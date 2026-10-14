# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Product catalog database and hybrid/vector search service."""

from __future__ import annotations

import re
from typing import Any, cast

from sqlspec import sql

from app.config import db_manager
from app.domain.products.schemas import ApexProduct, ApexVectorReadiness, Product, ProductMatch
from app.lib.service import FilterTypes, OffsetPagination, OracleAsyncService

__all__ = ("ProductService", "sanitize_oracle_text_query")

_ORACLE_TEXT_RESERVED_AND_STOPWORDS = frozenset({
    "a",
    "about",
    "accum",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "bt",
    "btg",
    "bti",
    "btp",
    "by",
    "can",
    "carry",
    "definescore",
    "definomerge",
    "do",
    "does",
    "equiv",
    "for",
    "from",
    "fuzzy",
    "give",
    "has",
    "have",
    "here",
    "hi",
    "hello",
    "how",
    "i",
    "in",
    "into",
    "is",
    "it",
    "list",
    "mddata",
    "me",
    "minus",
    "my",
    "near",
    "not",
    "nt",
    "ntg",
    "nti",
    "ntp",
    "of",
    "on",
    "or",
    "please",
    "pt",
    "rt",
    "sdata",
    "sell",
    "show",
    "soundex",
    "sqe",
    "stem",
    "syn",
    "tell",
    "that",
    "the",
    "their",
    "there",
    "they",
    "this",
    "threshold",
    "to",
    "tr",
    "transform",
    "trsyn",
    "us",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "wild",
    "will",
    "with",
    "within",
    "you",
    "your",
})
_MIN_ORACLE_TEXT_TOKEN_LEN = 2
_MAX_ORACLE_TEXT_TOKENS = 8


def sanitize_oracle_text_query(text_query: str | None) -> str | None:
    """Brace-escape raw tokens and join with ``ACCUM`` for Oracle Text ``CONTAINS``."""
    if text_query is None:
        return None
    stripped = text_query.strip()
    if not stripped:
        return None
    if stripped.startswith("{"):
        return stripped
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9\-']*", stripped.lower()):
        cleaned = re.sub(r"[^a-z0-9\-]", "", raw.strip("-'")).strip("-")
        if (
            len(cleaned) < _MIN_ORACLE_TEXT_TOKEN_LEN
            or cleaned in _ORACLE_TEXT_RESERVED_AND_STOPWORDS
            or cleaned in seen
        ):
            continue
        seen.add(cleaned)
        tokens.append(f"{{{cleaned}}}")
        if len(tokens) >= _MAX_ORACLE_TEXT_TOKENS:
            break
    if not tokens:
        return None
    return " ACCUM ".join(tokens)


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
        sanitized_query = sanitize_oracle_text_query(text_query)
        has_text_query = 1 if sanitized_query is not None else 0
        bind_text_query = sanitized_query if sanitized_query is not None else "{coffee}"
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
