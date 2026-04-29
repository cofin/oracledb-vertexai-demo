# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog
from google.genai.types import EmbedContentConfig
from sqlspec import sql
from sqlspec.adapters.oracledb import OracleAsyncDriver

from app.config import db_manager
from app.domain.products.schemas import Product, ProductMatch, Store
from app.lib.service import FilterTypes, OffsetPagination, SQLSpecAsyncService

if TYPE_CHECKING:
    from google.genai import Client

logger = structlog.get_logger()

# --- Product Service ---


class ProductService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Handles database operations for products using SQLSpec patterns."""

    async def list_with_count(self, *filters: FilterTypes) -> OffsetPagination[Product]:
        return await self.paginate(db_manager.get_sql("list-products"), *filters, schema_type=Product)

    async def get_by_id(self, product_id: int) -> Product | None:
        return await self.driver.select_one_or_none(
            db_manager.get_sql("get-product").where("id = :id"),
            id=product_id,
            schema_type=Product,
        )

    async def get_by_name(self, name: str) -> Product | None:
        return await self.driver.select_one_or_none(
            db_manager.get_sql("get-product").where("name = :name"),
            name=name,
            schema_type=Product,
        )

    async def get_products_for_embedding(self, force: bool = False) -> tuple[list[dict[str, Any]], int]:
        """Return (products_to_embed, total_count). force=True returns every product."""
        query = db_manager.get_sql("list-products-for-embedding")
        if not force:
            query = query.where("embedding IS NULL")
        page = await self.paginate(query)
        return list(page.items), page.total

    async def update_embedding(self, product_id: int, embedding: list[float]) -> bool:
        result = await self.driver.execute(
            sql.update("product").set(embedding=embedding).where_eq("id", product_id),
        )
        await self.driver.commit()
        rowcount = getattr(result, "rowcount", None)
        return bool(rowcount) if rowcount is not None else True

    async def search_by_vector(
        self, query_embedding: list[float], similarity_threshold: float = 0.7, limit: int = 5
    ) -> list[ProductMatch]:
        return await self.driver.select(
            db_manager.get_sql("vector-search-products"),
            query_vector=query_embedding,
            threshold=similarity_threshold,
            limit=limit,
            schema_type=ProductMatch,
        )

# --- Store Service ---


class StoreService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Service for managing store locations."""

    async def list_with_count(self, *filters: FilterTypes) -> OffsetPagination[Store]:
        return await self.paginate(db_manager.get_sql("list-stores"), *filters, schema_type=Store)

    async def get_all_stores(self) -> list[Store]:
        return await self.driver.select(db_manager.get_sql("list-stores"), schema_type=Store)

    async def find_stores_by_city(self, city: str) -> list[Store]:
        return await self.driver.select(
            db_manager.get_sql("list-stores").where("city = :city"),
            city=city,
            schema_type=Store,
        )

    async def find_stores_by_state(self, state: str) -> list[Store]:
        return await self.driver.select(
            db_manager.get_sql("list-stores").where("state = :state"),
            state=state,
            schema_type=Store,
        )

    async def get_store_by_id(self, store_id: int) -> Store | None:
        return await self.driver.select_one_or_none(
            db_manager.get_sql("list-stores").where("id = :id"),
            id=store_id,
            schema_type=Store,
        )

# --- Vertex AI Service ---


class VertexAIService:
    """Service for interacting with Google Vertex AI."""

    def __init__(
        self,
        client: Client,
        model: str,
        embedding_model: str,
        embedding_dimensions: int,
        cache_service: Any,
    ) -> None:
        self.client = client
        self.model = model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.cache_service = cache_service

    async def get_text_embedding(
        self,
        text: str,
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
        return_cache_status: bool = False,
    ) -> Any:
        cached = await self.cache_service.get_embedding(text, self.embedding_model)
        if cached:
            return (cached, True) if return_cache_status else cached

        response = await self.client.aio.models.embed_content(
            model=self.embedding_model,
            contents=text,
            config=EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.embedding_dimensions,
            ),
        )
        embedding_list = response.embeddings
        if not embedding_list or not embedding_list[0].values:
            return None
        embedding = embedding_list[0].values
        await self.cache_service.save_embedding(text, embedding, self.embedding_model)
        return (embedding, False) if return_cache_status else embedding


class OracleVectorSearchService:
    """Orchestrator for Oracle + Vertex AI vector search operations."""

    def __init__(self, vertex_ai_service: VertexAIService, product_service: ProductService) -> None:
        self.vertex_ai_service = vertex_ai_service
        self.product_service = product_service

    async def similarity_search(
        self, query: str, k: int = 5, threshold: float = 0.5
    ) -> tuple[list[ProductMatch], bool, dict[str, float]]:
        start_time = time.time()
        embedding, cache_hit = await self.vertex_ai_service.get_text_embedding(
            query, task_type="RETRIEVAL_QUERY", return_cache_status=True
        )
        embedding_ms = (time.time() - start_time) * 1000

        oracle_start = time.time()
        results = await self.product_service.search_by_vector(embedding, similarity_threshold=threshold, limit=k)
        oracle_ms = (time.time() - oracle_start) * 1000

        return results, cache_hit, {"embedding_ms": embedding_ms, "oracle_ms": oracle_ms}
