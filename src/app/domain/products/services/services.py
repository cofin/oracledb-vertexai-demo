# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

import structlog
from google.genai.types import EmbedContentConfig
from msgspec.structs import asdict
from sqlspec import sql

from app.config import db_manager
from app.domain.products.schemas import (
    ExplainPlan,
    ExplainPlanRow,
    Product,
    ProductAvailability,
    ProductMatch,
    Store,
    StoreDistance,
    StoreHours,
    StoreInventoryItem,
)
from app.domain.products.services._location import haversine_miles, store_matches_hint
from app.lib.service import FilterTypes, OffsetPagination, OracleAsyncService

if TYPE_CHECKING:
    from google.genai import Client

logger = structlog.get_logger()

GEMINI_EMBEDDING_2_MODEL = "gemini-embedding-2-preview"
EMBEDDING_PURPOSE_INSTRUCTIONS = {
    "query": (
        "Task: Generate an embedding for a search query to retrieve relevant "
        "Cymbal Coffee menu and store availability documents."
    ),
    "document": (
        "Task: Generate an embedding for a document that can be retrieved by "
        "Cymbal Coffee customer search queries."
    ),
}


class ProductService(OracleAsyncService):
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
        query = sql.select("id", "name", "description").from_("product")
        if not force:
            query = query.where("embedding IS NULL")
        query = query.order_by("id")
        rows = await self.driver.select(query)
        return [dict(row) for row in rows], len(rows)

    async def update_embedding(self, product_id: int, embedding: list[float]) -> bool:
        result = await self.driver.execute(
            sql.update("product").set(embedding=embedding).where_eq("id", product_id),
        )
        await self.driver.commit()
        return result.rows_affected > 0

    # docs:start-search-by-vector
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

    # docs:end-search-by-vector


# --- Store Service ---


class StoreService(OracleAsyncService):
    """Service for managing store locations."""

    async def list_with_count(self, *filters: FilterTypes) -> OffsetPagination[Store]:
        return await self.paginate(db_manager.get_sql("list-stores"), *filters, schema_type=Store)

    async def get_all_stores(self) -> list[Store]:
        return await self.driver.select(db_manager.get_sql("list-stores"), schema_type=Store)

    async def find_stores_by_city(self, city: str) -> list[Store]:
        return await self.driver.select(
            db_manager.get_sql("find-stores-by-city"),
            city=city,
            schema_type=Store,
        )

    async def find_stores_by_state(self, state: str) -> list[Store]:
        return await self.driver.select(
            db_manager.get_sql("find-stores-by-state"),
            state=state,
            schema_type=Store,
        )

    async def search_stores_by_zip(self, zip_code: str) -> list[Store]:
        return await self.driver.select(
            db_manager.get_sql("find-stores-by-zip"),
            zip_code=zip_code,
            schema_type=Store,
        )

    async def find_stores_by_location(
        self,
        *,
        city: str | None = None,
        state: str | None = None,
        zip_code: str | None = None,
    ) -> list[Store]:
        return await self.driver.select(
            db_manager.get_sql("find-stores-by-location"),
            city=city,
            state=state,
            zip_code=zip_code,
            schema_type=Store,
        )

    async def get_store_by_id(self, store_id: int) -> Store | None:
        return await self.driver.select_one_or_none(
            db_manager.get_sql("get-store-by-id"),
            id=store_id,
            schema_type=Store,
        )

    async def get_store_hours(self, store_id: int) -> StoreHours | None:
        store = await self.get_store_by_id(store_id)
        if store is None:
            return None
        return StoreHours(
            store_id=store.id,
            store_name=store.name,
            timezone=store.timezone,
            hours=store.hours or {},
        )

    async def find_nearest_stores(self, latitude: float, longitude: float, limit: int = 5) -> list[StoreDistance]:
        stores = await self.get_all_stores()
        ranked = [
            StoreDistance(
                **asdict(store),
                distance_miles=round(haversine_miles(latitude, longitude, store), 2),
            )
            for store in stores
            if store.latitude is not None and store.longitude is not None
        ]
        ranked.sort(key=lambda store: store.distance_miles)
        return ranked[:limit]

    async def resolve_store(
        self,
        *,
        location_hint: str | None = None,
        coordinates: tuple[float, float] | None = None,
    ) -> Store | None:
        """Resolve a single store by location hint (priority) or nearest to coordinates."""
        if location_hint:
            stores = await self.get_all_stores()
            for store in stores:
                if store_matches_hint(store, location_hint):
                    return store
        if coordinates:
            lat, lon = coordinates
            nearest = await self.find_nearest_stores(lat, lon, limit=1)
            if nearest:
                return nearest[0]
        return None

    async def get_store_inventory(self, store_id: int) -> list[StoreInventoryItem]:
        return await self.driver.select(
            db_manager.get_sql("list-store-inventory"),
            store_id=store_id,
            schema_type=StoreInventoryItem,
        )

    async def find_stores_with_product(
        self,
        product_id: int,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> list[ProductAvailability]:
        rows = await self.driver.select(
            db_manager.get_sql("find-stores-with-product-inventory"),
            product_id=product_id,
            schema_type=ProductAvailability,
        )
        return self._rank_availability(rows, latitude=latitude, longitude=longitude)

    async def find_product_availability(
        self,
        query: str,
        *,
        location_hint: str | None = None,
        coordinates: tuple[float, float] | None = None,
    ) -> list[ProductAvailability]:
        rows = await self.driver.select(
            db_manager.get_sql("find-product-availability-by-query"),
            product_query=query,
            schema_type=ProductAvailability,
        )
        latitude, longitude = coordinates or (None, None)
        return self._rank_availability(rows, latitude=latitude, longitude=longitude)

    @staticmethod
    def _rank_availability(
        rows: list[ProductAvailability],
        *,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> list[ProductAvailability]:
        if latitude is None or longitude is None:
            return rows
        ranked: list[ProductAvailability] = []
        for row in rows:
            data = asdict(row)
            data["distance_miles"] = round(haversine_miles(latitude, longitude, row), 2)
            ranked.append(ProductAvailability(**data))
        ranked.sort(key=lambda row: row.distance_miles if row.distance_miles is not None else float("inf"))
        return ranked


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

    # docs:start-vertex-embedding
    async def get_text_embedding(
        self,
        text: str,
        *,
        embedding_purpose: str = "document",
        return_cache_status: bool = False,
    ) -> Any:
        cached = await self.cache_service.get_embedding(text, self.embedding_model)
        if cached:
            return (cached, True) if return_cache_status else cached

        content = _embedding_content(self.embedding_model, text, embedding_purpose)
        config_kwargs: dict[str, Any] = {"output_dimensionality": self.embedding_dimensions}

        response = await self.client.aio.models.embed_content(
            model=self.embedding_model,
            contents=content,
            config=EmbedContentConfig(**config_kwargs),
        )
        embedding_list = response.embeddings
        if not embedding_list or not embedding_list[0].values:
            return None
        embedding = embedding_list[0].values
        await self.cache_service.save_embedding(text, embedding, self.embedding_model)
        return (embedding, False) if return_cache_status else embedding

    # docs:end-vertex-embedding


def _embedding_content(model: str, text: str, embedding_purpose: str) -> str:
    if GEMINI_EMBEDDING_2_MODEL not in model:
        return text
    instruction = EMBEDDING_PURPOSE_INSTRUCTIONS.get(embedding_purpose)
    if instruction is None:
        return text
    return f"{instruction}\n\n{text}"


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
            query, embedding_purpose="query", return_cache_status=True
        )
        embedding_ms = (time.time() - start_time) * 1000

        oracle_start = time.time()
        results = await self.product_service.search_by_vector(embedding, similarity_threshold=threshold, limit=k)
        oracle_ms = (time.time() - oracle_start) * 1000

        return results, cache_hit, {"embedding_ms": embedding_ms, "oracle_ms": oracle_ms}

    @staticmethod
    def parse_plan_rows(plan_lines: list[str]) -> list[ExplainPlanRow]:
        """Parse the operation table rows from ``DBMS_XPLAN.DISPLAY`` output."""

        def cell(cells: list[str], index: int) -> str:
            try:
                return cells[index]
            except IndexError:
                return ""

        rows: list[ExplainPlanRow] = []
        for line in plan_lines:
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells[0].lower() == "id":
                continue
            operation_cell = cell(cells, 1)
            if not operation_cell:
                continue
            plan_id = re.sub(r"[^0-9]", "", cells[0])
            if not plan_id:
                continue
            operation = re.sub(r"\s+", " ", operation_cell).strip()
            rows.append(
                ExplainPlanRow(
                    id=plan_id,
                    operation=operation,
                    name=cell(cells, 2),
                    rows=cell(cells, 3),
                    bytes=cell(cells, 4),
                    cost=cell(cells, 5),
                    time=cell(cells, 6),
                    raw_line=line,
                    is_vector="VECTOR" in line.upper(),
                )
            )
        return rows

    async def explain_search_plan(self, query: str) -> ExplainPlan:
        """Run EXPLAIN PLAN against the vector-search SQL and pull the plan.

        Two driver round-trips: ``EXPLAIN PLAN FOR <vector-search>`` then
        ``DBMS_XPLAN.DISPLAY()``. The returned summary is the first plan
        operation that mentions the VECTOR access path (Oracle 26ai's
        hallmark for HNSW/IVF lookups).
        """
        embedding, _ = await self.vertex_ai_service.get_text_embedding(
            query, embedding_purpose="query", return_cache_status=True
        )
        await self.product_service.driver.execute(
            db_manager.get_sql("explain-plan-vector-search"),
            query_vector=embedding,
            threshold=0.5,
            limit=5,
        )
        rows = await self.product_service.driver.select(db_manager.get_sql("explain-plan-display"))
        plan_lines = [str(row["plan_table_output"]) for row in rows]
        plan_rows = self.parse_plan_rows(plan_lines)
        plan_summary = next(
            (f"{row.operation} {row.name}".strip() for row in plan_rows if row.is_vector),
            plan_rows[0].operation if plan_rows else (plan_lines[0].strip() if plan_lines else ""),
        )
        return ExplainPlan(plan_lines=plan_lines, plan_summary=plan_summary, plan_rows=plan_rows)
