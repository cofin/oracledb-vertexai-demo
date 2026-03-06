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
from sqlspec.adapters.oracledb import OracleAsyncDriver

from app.domain.products.schemas import Product, Store
from app.lib.service import SQLSpecService

if TYPE_CHECKING:
    from google.genai import Client

logger = structlog.get_logger()

# --- Product Service ---

class ProductService(SQLSpecService[OracleAsyncDriver]):
    """Handles database operations for products using SQLSpec patterns."""

    async def get_by_id(self, product_id: int) -> Product | None:
        sql = "SELECT * FROM product WHERE id = :id"
        row = await self.driver.select_one_or_none(sql, {"id": product_id})
        return Product(**row) if row else None

    async def get_by_name(self, name: str) -> Product | None:
        sql = "SELECT * FROM product WHERE name = :name"
        row = await self.driver.select_one_or_none(sql, {"name": name})
        return Product(**row) if row else None

    async def search_by_vector(self, query_embedding: list[float], similarity_threshold: float = 0.7, limit: int = 5) -> list[dict[str, Any]]:
        sql = """SELECT id, name, description, current_price, 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) as similarity_score
                 FROM product WHERE 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) > :threshold
                 ORDER BY similarity_score DESC FETCH FIRST :limit ROWS ONLY"""
        return await self.driver.select(sql, {"query_vector": query_embedding, "threshold": similarity_threshold, "limit": limit})

# --- Store Service ---

class StoreService(SQLSpecService[OracleAsyncDriver]):
    """Service for managing store locations."""

    async def get_all_stores(self) -> list[Store]:
        sql = "SELECT * FROM store"
        rows = await self.driver.select(sql)
        return [Store(**row) for row in rows]

    async def find_stores_by_city(self, city: str) -> list[Store]:
        sql = "SELECT * FROM store WHERE city = :city"
        rows = await self.driver.select(sql, {"city": city})
        return [Store(**row) for row in rows]

    async def find_stores_by_state(self, state: str) -> list[Store]:
        sql = "SELECT * FROM store WHERE state = :state"
        rows = await self.driver.select(sql, {"state": state})
        return [Store(**row) for row in rows]

    async def get_store_by_id(self, store_id: int) -> Store | None:
        sql = "SELECT * FROM store WHERE id = :id"
        row = await self.driver.select_one_or_none(sql, {"id": store_id})
        return Store(**row) if row else None

# --- Vertex AI Service ---

class VertexAIService:
    """Service for interacting with Google Vertex AI."""

    def __init__(self, client: Client, model: str, embedding_model: str, cache_service: Any) -> None:
        self.client = client
        self.model = model
        self.embedding_model = embedding_model
        self.cache_service = cache_service

    async def get_text_embedding(self, text: str, return_cache_status: bool = False) -> Any:
        # Check cache first
        cached = await self.cache_service.get_embedding(text, self.embedding_model)
        if cached:
            return (cached, True) if return_cache_status else cached

        # Call Vertex AI
        response = await self.client.aio.models.embed_content(model=self.embedding_model, contents=text)
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

    async def similarity_search(self, query: str, k: int = 5, threshold: float = 0.5) -> tuple[list[dict[str, Any]], bool, dict[str, float]]:
        start_time = time.time()
        embedding, cache_hit = await self.vertex_ai_service.get_text_embedding(query, return_cache_status=True)
        embedding_ms = (time.time() - start_time) * 1000

        oracle_start = time.time()
        results = await self.product_service.search_by_vector(embedding, similarity_threshold=threshold, limit=k)
        oracle_ms = (time.time() - oracle_start) * 1000

        # Map current_price to distance (1 - similarity) for compatibility with legacy controller
        for r in results:
            r["distance"] = 1 - r["similarity_score"]

        return results, cache_hit, {"embedding_ms": embedding_ms, "oracle_ms": oracle_ms}
