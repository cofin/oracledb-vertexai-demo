# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Product catalog database and hybrid/vector search service."""

from __future__ import annotations

from typing import Any, cast

from sqlspec import sql

from app.config import db_manager
from app.domain.products.schemas import ApexProduct, ApexVectorReadiness, Product, ProductMatch
from app.lib.service import FilterTypes, OffsetPagination, OracleAsyncService

__all__ = ("ProductService",)


class ProductService(OracleAsyncService):
    """Handles database operations for products using SQLSpec patterns."""

    async def list_with_count(self, *filters: FilterTypes) -> OffsetPagination[Product]:
        """Paginate products matching the supplied filter definitions."""
        return cast(
            "OffsetPagination[Product]",
            await self.paginate(db_manager.get_sql("list-products"), *filters, schema_type=Product),
        )

    async def list_apex_products(
        self, *, q: str | None = None, category: str | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[ApexProduct], int]:
        """List products and total count for the APEX administration console."""
        bounded_limit = max(1, min(limit, 100))
        bounded_offset = max(offset, 0)
        rows = await self.driver.select(
            db_manager.get_sql("list-apex-products"),
            q=q,
            category=category,
            limit=bounded_limit,
            offset=bounded_offset,
            schema_type=ApexProduct,
        )
        total = await self.driver.select_value(db_manager.get_sql("count-apex-products"), q=q, category=category)
        return rows, int(total or 0)

    async def get_vector_readiness(self) -> ApexVectorReadiness:
        """Return vector index and embedding population readiness statistics."""
        return await self.driver.select_one(db_manager.get_sql("get-vector-readiness"), schema_type=ApexVectorReadiness)

    async def get_by_id(self, product_id: int) -> Product | None:
        """Return a single product by primary key."""
        return await self.driver.select_one_or_none(
            db_manager.get_sql("get-product").where("id = :id"), id=product_id, schema_type=Product
        )

    async def get_by_name(self, name: str) -> Product | None:
        """Return a single product by exact name."""
        return await self.driver.select_one_or_none(
            db_manager.get_sql("get-product").where("name = :name"), name=name, schema_type=Product
        )

    async def get_products_for_embedding(self, force: bool = False) -> tuple[list[dict[str, Any]], int]:
        """Return ``(products_to_embed, total_count)``. ``force=True`` returns every product."""
        query = sql.select("id", "name", "description").from_("product")
        if not force:
            query = query.where("embedding IS NULL")
        query = query.order_by("id")
        rows = await self.driver.select(query)
        return [dict(row) for row in rows], len(rows)

    async def update_embedding(self, product_id: int, embedding: list[float]) -> bool:
        """Persist a 3072-dimension document embedding for a product row."""
        result = await self.driver.execute(sql.update("product").set(embedding=embedding).where_eq("id", product_id))
        await self.driver.commit()
        return result.rows_affected > 0

    async def get_chat_routes_for_embedding(self, force: bool = False) -> tuple[list[dict[str, Any]], int]:
        """Return ``(chat_routes_to_embed, total_count)``. ``force=True`` returns every route exemplar."""
        query = sql.select("id", "route_label", "title", "exemplar_text", "keywords").from_("chat_route")
        if not force:
            query = query.where("embedding IS NULL")
        query = query.order_by("id")
        rows = await self.driver.select(query)
        return [dict(row) for row in rows], len(rows)

    async def update_chat_route_embedding(self, route_id: int, embedding: list[float]) -> bool:
        """Persist a 3072-dimension document embedding for a ``chat_route`` exemplar row."""
        result = await self.driver.execute(sql.update("chat_route").set(embedding=embedding).where_eq("id", route_id))
        await self.driver.commit()
        return result.rows_affected > 0

    async def search_by_vector(
        self,
        query_embedding: list[float],
        similarity_threshold: float = 0.7,
        limit: int = 5,
        *,
        store_id: int | None = None,
    ) -> list[ProductMatch]:
        """Search products by HNSW cosine similarity."""
        if store_id is not None:
            return await self.driver.select(
                db_manager.get_sql("vector-search-products-by-store"),
                query_vector=query_embedding,
                threshold=similarity_threshold,
                limit=limit,
                store_id=store_id,
                schema_type=ProductMatch,
            )
        return await self.driver.select(
            db_manager.get_sql("vector-search-products"),
            query_vector=query_embedding,
            threshold=similarity_threshold,
            limit=limit,
            schema_type=ProductMatch,
        )

    async def search_hybrid(
        self,
        *,
        text_query: str | None,
        query_embedding: list[float],
        similarity_threshold: float = 0.45,
        rrf_k: int = 60,
        limit: int = 5,
    ) -> list[ProductMatch]:
        """Run single-query Oracle 26ai Hybrid RRF product search combining CONTAINS/SCORE and VECTOR_DISTANCE."""
        has_text_query = 1 if text_query is not None else 0
        bind_text_query = text_query if text_query is not None else "{coffee}"
        return await self.driver.select(
            db_manager.get_sql("hybrid-search-products"),
            has_text_query=has_text_query,
            text_query=bind_text_query,
            query_vector=query_embedding,
            threshold=similarity_threshold,
            rrf_k=rrf_k,
            limit=limit,
            schema_type=ProductMatch,
        )
