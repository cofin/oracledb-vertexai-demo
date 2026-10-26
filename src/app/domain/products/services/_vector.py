# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle 26ai vector/hybrid search, DBMS_XPLAN inspection, and APEX recommendation orchestration."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any, cast

import structlog

from app.domain.products.schemas import (
    ApexRecommendation,
    ApexRecommendationResponse,
    ApexVectorStatus,
    ExplainPlan,
    ExplainPlanRow,
    ProductMatch,
    RecommendationMode,
    VectorDemoMatch,
)
from app.domain.products.services._products import ProductService
from app.lib.exceptions import AIServiceUnconfigured, is_expected_service_unavailable
from app.lib.service import OracleLoaderService, default_sql_loader
from app.lib.settings import Settings
from app.lib.text_search import build_oracle_text_query
from app.utils.serialization import encode_json, sanitize_for_json

if TYPE_CHECKING:
    from sqlspec.adapters.oracledb import OracleAsyncDriver
    from sqlspec.loader import SQLFileLoader

    from app.domain.products.services._embedding import VertexAIService
    from app.domain.products.services._stores import StoreService

__all__ = (
    "RRF_DEFAULT_K",
    "SERVICE_UNAVAILABLE_MESSAGE",
    "OracleVectorSearchService",
    "build_explore_sql_phases",
    "build_explore_telemetry_context",
    "build_vector_demo_matches",
    "unavailable_plan",
)

RRF_DEFAULT_K = 60
SERVICE_UNAVAILABLE_MESSAGE = "Vector search is unavailable. Check Vertex AI and Oracle configuration, then retry."
_REQUIRED_HYBRID_INDEX_COUNT = 2

logger = structlog.get_logger()


class OracleVectorSearchService(OracleLoaderService):
    """Orchestrator for Oracle 26ai Hybrid RRF, HNSW vector search, EXPLAIN PLAN, and APEX recommendations."""

    __slots__ = ("product_service", "store_service", "vertex_ai_service")

    def __init__(
        self,
        driver: OracleAsyncDriver | None = None,
        *,
        vertex_ai_service: VertexAIService,
        product_service: ProductService,
        store_service: StoreService | None = None,
        loader: SQLFileLoader | None = None,
    ) -> None:
        resolved_driver = driver if driver is not None else getattr(product_service, "driver", product_service)
        super().__init__(cast("OracleAsyncDriver", resolved_driver), loader or default_sql_loader())
        self.vertex_ai_service = vertex_ai_service
        self.product_service = product_service
        self.store_service = store_service

    async def similarity_search(
        self, query: str, k: int = 5, threshold: float = 0.5, *, store_id: int | None = None
    ) -> tuple[list[ProductMatch], bool, dict[str, float]]:
        """Embed a query and execute Oracle Hybrid RRF or store-scoped HNSW vector search."""
        start_time = time.perf_counter()
        embedding, cache_hit = await self.vertex_ai_service.get_text_embedding(
            query, embedding_purpose="query", return_cache_status=True
        )
        embedding_ms = (time.perf_counter() - start_time) * 1000
        if not embedding:
            raise AIServiceUnconfigured(SERVICE_UNAVAILABLE_MESSAGE)

        oracle_start = time.perf_counter()
        results: list[ProductMatch] = []
        if store_id is None and isinstance(self.product_service, ProductService):
            results = await self.product_service.search_hybrid(
                text_query=query,
                query_embedding=embedding,
                similarity_threshold=min(threshold, 0.45),
                rrf_k=RRF_DEFAULT_K,
                limit=k,
            )
        if not results:
            results = await self.product_service.search_by_vector(
                embedding, similarity_threshold=threshold, limit=k, store_id=store_id
            )
        oracle_ms = (time.perf_counter() - oracle_start) * 1000

        return results, cache_hit, {"embedding_ms": embedding_ms, "oracle_ms": oracle_ms}

    async def explain_search_plan(self, query: str, *, mode: str = "hybrid") -> ExplainPlan:
        """Run EXPLAIN PLAN against the Hybrid RRF or HNSW vector-search SQL and parse DBMS_XPLAN rows."""
        embedding, _ = await self.vertex_ai_service.get_text_embedding(
            query, embedding_purpose="query", return_cache_status=True
        )
        if not embedding:
            raise AIServiceUnconfigured(SERVICE_UNAVAILABLE_MESSAGE)
        if mode == "vector":
            await self.driver.execute(
                self.get_sql("explain-plan-vector-search"), query_vector=embedding, threshold=0.5, limit=5
            )
        else:
            sanitized = build_oracle_text_query(query, max_terms=8)
            await self.driver.execute(
                self.get_sql("explain-plan-hybrid-search"),
                has_text_query=1 if sanitized is not None else 0,
                text_query=sanitized if sanitized is not None else "{coffee}",
                query_vector=embedding,
                threshold=0.45,
                rrf_k=RRF_DEFAULT_K,
                limit=5,
            )
        rows = await self.driver.select(self.get_sql("explain-plan-display"))
        plan_lines = [str(row["plan_table_output"]) for row in rows]
        plan_rows = self.parse_plan_rows(plan_lines)
        highlighted = [f"{row.operation} {row.name}".strip() for row in plan_rows if row.is_vector]
        plan_summary = (
            " + ".join(dict.fromkeys(highlighted))
            if highlighted
            else (plan_rows[0].operation if plan_rows else (plan_lines[0].strip() if plan_lines else ""))
        )
        return ExplainPlan(plan_lines=plan_lines, plan_summary=plan_summary, plan_rows=plan_rows)

    async def get_apex_vector_status(self) -> ApexVectorStatus:
        """Inspect embedding provider configuration and Oracle vector/hybrid index readiness."""
        readiness = await self.product_service.get_vector_readiness()
        settings = Settings.from_env()
        embedding_model = str(getattr(self.vertex_ai_service, "embedding_model", settings.ai.embedding_model))
        embedding_dimensions = int(
            getattr(self.vertex_ai_service, "embedding_dimensions", settings.ai.embedding_dimensions)
        )
        provider_configured = settings.ai.has_valid_project_id() or settings.ai.has_valid_api_key()
        oracle_vector_ready = readiness.product_count > 0 and readiness.embedded_product_count > 0
        hybrid_rrf_ready = oracle_vector_ready and (
            readiness.hybrid_index_count is None or readiness.hybrid_index_count >= _REQUIRED_HYBRID_INDEX_COUNT
        )
        return ApexVectorStatus(
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimensions,
            provider_configured=provider_configured,
            oracle_vector_ready=oracle_vector_ready,
            hybrid_rrf_ready=hybrid_rrf_ready,
            product_count=readiness.product_count,
            embedded_product_count=readiness.embedded_product_count,
        )

    async def recommend_for_apex(
        self, *, query: str, limit: int = 5, store_id: int | None = None
    ) -> ApexRecommendationResponse:
        """Return grounded APEX recommendations, executing fallback SQL outside ``except:`` for mypyc safety."""
        fallback_reason: str | None = None
        try:
            matches, cache_hit, timings = await self.similarity_search(query, k=limit, threshold=0.5, store_id=store_id)
            mode: RecommendationMode = (
                "hybrid" if store_id is None and any(row.rrf_score > 0 for row in matches) else "vector"
            )
            return ApexRecommendationResponse(
                query=query,
                mode=mode,
                items=[
                    ApexRecommendation(
                        product_id=row.id,
                        name=row.name,
                        description=row.description,
                        price=row.price,
                        similarity_score=row.similarity_score,
                        store_id=row.store_id,
                        store_name=row.store_name,
                        quantity_available=row.quantity_available,
                        stock_status=row.stock_status,
                        pickup_available=row.pickup_available,
                    )
                    for row in matches
                ],
                total=len(matches),
                cache_hit=cache_hit,
                embedding_time_ms=round(timings.get("embedding_ms", 0.0), 2),
                oracle_time_ms=round(timings.get("oracle_ms", 0.0), 2),
            )
        except Exception as exc:
            if not is_expected_service_unavailable(exc):
                raise
            fallback_reason = type(exc).__name__

        await logger.awarning("APEX vector recommendations fell back", error_type=fallback_reason)
        fallback_items = await self._select_fallback_recommendations(query=query, limit=limit, store_id=store_id)
        return ApexRecommendationResponse(
            query=query,
            mode="fallback",
            items=fallback_items,
            total=len(fallback_items),
            fallback_reason=fallback_reason,
        )

    @staticmethod
    def parse_plan_rows(plan_lines: list[str]) -> list[ExplainPlanRow]:
        """Parse operation table rows from ``DBMS_XPLAN.DISPLAY`` output."""
        rows: list[ExplainPlanRow] = []
        for line in plan_lines:
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells[0].lower() == "id":
                continue
            operation_cell = _plan_cell(cells, 1)
            if not operation_cell:
                continue
            plan_id = re.sub(r"[^0-9]", "", cells[0])
            if not plan_id:
                continue
            operation = re.sub(r"\s+", " ", operation_cell).strip()
            upper_line = line.upper()
            rows.append(
                ExplainPlanRow(
                    id=plan_id,
                    operation=operation,
                    name=_plan_cell(cells, 2),
                    rows=_plan_cell(cells, 3),
                    bytes=_plan_cell(cells, 4),
                    cost=_plan_cell(cells, 5),
                    time=_plan_cell(cells, 6),
                    raw_line=line,
                    is_vector=any(token in upper_line for token in ("VECTOR", "DOMAIN INDEX", "CTX_IDX")),
                )
            )
        return rows

    async def _select_fallback_recommendations(
        self, *, query: str, limit: int, store_id: int | None
    ) -> list[ApexRecommendation]:
        if store_id is not None and self.store_service is not None:
            inventory = await self.store_service.search_store_inventory(store_id=store_id, q=query, limit=limit)
            return [
                ApexRecommendation(
                    product_id=row.product_id,
                    name=row.product_name,
                    description=row.product_description,
                    price=row.product_price if row.product_price is not None else 0.0,
                    category=row.product_category,
                    sku=row.product_sku,
                    store_id=row.store_id,
                    store_name=row.store_name,
                    quantity_available=row.quantity_available,
                    stock_status=row.stock_status,
                    pickup_available=row.pickup_available,
                )
                for row in inventory
            ]

        products, _ = await self.product_service.list_apex_products(q=query, category=None, limit=limit, offset=0)
        return [
            ApexRecommendation(
                product_id=row.id,
                name=row.name,
                description=row.description,
                price=row.price,
                category=row.category,
                sku=row.sku,
            )
            for row in products
        ]


def unavailable_plan(message: str = SERVICE_UNAVAILABLE_MESSAGE) -> ExplainPlan:
    """Return a fallback ExplainPlan payload when Oracle or Vertex AI is unavailable."""
    return ExplainPlan(plan_lines=[message], plan_summary="Plan unavailable")


def build_vector_demo_matches(results: list[ProductMatch], *, rrf_k: int = RRF_DEFAULT_K) -> list[VectorDemoMatch]:
    """Convert ``ProductMatch`` rows into ``VectorDemoMatch`` records with RRF rank and score metadata."""
    sim_ranked_ids = [
        row.id for row in sorted(results, key=lambda r: r.similarity_score, reverse=True) if row.similarity_score > 0
    ]
    fallback_vec_ranks = {product_id: idx + 1 for idx, product_id in enumerate(sim_ranked_ids)}

    matches: list[VectorDemoMatch] = []
    for idx, row in enumerate(results):
        vector_rank = (
            int(row.vector_rank)
            if row.vector_rank is not None
            else fallback_vec_ranks.get(row.id, idx + 1 if row.similarity_score > 0 else None)
        )
        lexical_rank = int(row.lexical_rank) if row.lexical_rank is not None else None
        lexical_score = round(float(row.lexical_score or 0.0), 1)
        computed_rrf = (1.0 / (rrf_k + lexical_rank) if lexical_rank is not None else 0.0) + (
            1.0 / (rrf_k + vector_rank) if vector_rank is not None else 0.0
        )
        rrf_score = round(float(row.rrf_score) if row.rrf_score and row.rrf_score > 0 else computed_rrf, 4)
        matches.append(
            VectorDemoMatch(
                name=row.name,
                description=row.description,
                price=row.price,
                similarity=round(row.similarity_score * 100, 1),
                lexical_score=lexical_score,
                lexical_rank=lexical_rank,
                vector_rank=vector_rank,
                rrf_score=rrf_score,
                rrf_k=rrf_k,
            )
        )
    return matches


def build_explore_sql_phases(
    query: str,
    *,
    matches: list[VectorDemoMatch],
    oracle_ms: float = 0.0,
    cache_hit: bool = False,
    rrf_k: int = RRF_DEFAULT_K,
) -> list[dict[str, Any]]:
    """Build structured SQL telemetry phases for both Hybrid RRF and pure HNSW vector queries."""
    sanitized = build_oracle_text_query(query, max_terms=8)
    cache_status = "hit" if cache_hit else "miss"
    vector_digest = "<VECTOR[3072 FLOAT32], model=gemini-embedding-2>"
    return [
        _build_explore_phase(
            label="Oracle 26ai Hybrid RRF search (CONTAINS + VECTOR_DISTANCE)",
            sql_key="hybrid-search-products",
            binds={
                "has_text_query": 1 if sanitized is not None else 0,
                "text_query": sanitized if sanitized is not None else "{coffee}",
                "query_vector": vector_digest,
                "threshold": 0.45,
                "rrf_k": rrf_k,
                "limit": 5,
            },
            row_count=len(matches),
            runtime_ms=oracle_ms,
            cache_status=cache_status,
        ),
        _build_explore_phase(
            label="Oracle 26ai HNSW Vector search (FETCH APPROX)",
            sql_key="vector-search-products",
            binds={"query_vector": vector_digest, "threshold": 0.5, "limit": 5},
            row_count=len(matches),
            runtime_ms=oracle_ms,
            cache_status=cache_status,
        ),
    ]


def build_explore_telemetry_context(
    query: str,
    *,
    matches: list[VectorDemoMatch],
    embedding_ms: float = 0.0,
    oracle_ms: float = 0.0,
    cache_hit: bool = False,
    rrf_k: int = RRF_DEFAULT_K,
) -> dict[str, Any]:
    """Assemble template context and serialized popover payloads for the Explore search panel."""
    sanitized = build_oracle_text_query(query, max_terms=8)
    sql_phases = build_explore_sql_phases(query, matches=matches, oracle_ms=oracle_ms, cache_hit=cache_hit, rrf_k=rrf_k)
    rrf_rows = [
        {
            "name": m.name,
            "lexicalScore": m.lexical_score,
            "lexicalRank": m.lexical_rank,
            "similarity": m.similarity,
            "vectorRank": m.vector_rank,
            "rrfScore": m.rrf_score,
            "formula": _format_rrf_formula(m.lexical_rank, m.vector_rank, m.rrf_score, rrf_k),
        }
        for m in matches
    ]
    clean_query = query.strip()
    hybrid_detail: dict[str, Any] = {
        "title": "Oracle 26ai Hybrid RRF & HNSW Vector SQL",
        "summary": (
            f"Reciprocal Rank Fusion (k={rrf_k}) fuses Oracle Text CONTAINS/SCORE(1) "
            f"({sanitized or '{coffee}'}) on PRODUCT_HYBRID_CTX_IDX with HNSW cosine distance "
            f"on PRODUCT_EMBEDDING_IDX."
        ),
        "rrfFormula": f"RRF(d) = 1 / ({rrf_k} + lexical_rank) + 1 / ({rrf_k} + vector_rank)",
        "oracleTextQuery": sanitized or "{coffee}",
        "rrfRows": rrf_rows,
        "sqlPhases": sql_phases,
    }
    if clean_query:
        hybrid_detail["planQuery"] = clean_query

    vector_detail: dict[str, Any] = {
        "title": "Oracle 26ai HNSW Vector Search SQL",
        "summary": (
            "Approximate Nearest Neighbor (HNSW) cosine distance query using "
            "ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE) FETCH APPROX FIRST :limit ROWS ONLY."
        ),
        "sqlPhases": [phase for phase in sql_phases if phase["sql_key"] == "vector-search-products"],
    }
    if clean_query:
        vector_detail["planQuery"] = clean_query

    return {
        "search_mode": "hybrid",
        "oracle_text_query": sanitized,
        "rrf_k": rrf_k,
        "embedding_ms": round(embedding_ms, 1),
        "oracle_ms": round(oracle_ms, 1),
        "cache_hit": cache_hit,
        "sql_phases": sql_phases,
        "hybrid_detail_json": encode_json(hybrid_detail),
        "vector_detail_json": encode_json(vector_detail),
    }


def _build_explore_phase(
    *, label: str, sql_key: str, binds: dict[str, Any], row_count: int, runtime_ms: float, cache_status: str
) -> dict[str, Any]:
    try:
        sql_text = str(default_sql_loader().get_sql(sql_key).sql)
    except Exception:
        sql_text = sql_key
    return {
        "label": label,
        "sql_key": sql_key,
        "sql": sql_text,
        "binds": sanitize_for_json(binds),
        "row_count": row_count,
        "runtime_ms": round(runtime_ms, 2),
        "cache_status": cache_status,
    }


def _plan_cell(cells: list[str], index: int) -> str:
    try:
        return cells[index]
    except IndexError:
        return ""


def _format_rrf_formula(lexical_rank: int | None, vector_rank: int | None, rrf_score: float, rrf_k: int) -> str:
    lex_part = f"1/({rrf_k}+{lexical_rank})" if lexical_rank is not None else "0"
    vec_part = f"1/({rrf_k}+{vector_rank})" if vector_rank is not None else "0"
    return f"{lex_part} + {vec_part} = {rrf_score:.4f}"
