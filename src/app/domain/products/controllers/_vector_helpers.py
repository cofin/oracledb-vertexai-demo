# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Private helpers for vector controller request parsing and fallback responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import msgspec
from google.genai import errors as genai_errors

from app.domain.chat.services._telemetry import build_sql_phase
from app.domain.products.schemas import ExplainPlan, ProductMatch, VectorDemoMatch, VectorQuery
from app.domain.products.services import sanitize_oracle_text_query

if TYPE_CHECKING:
    from litestar_htmx import HTMXRequest

__all__ = (
    "RRF_DEFAULT_K",
    "SERVICE_UNAVAILABLE_MESSAGE",
    "build_explore_sql_phases",
    "build_explore_telemetry_context",
    "build_vector_demo_matches",
    "is_expected_service_unavailable",
    "payload_value",
    "unavailable_plan",
    "vector_query_from_request",
)

RRF_DEFAULT_K = 60
SERVICE_UNAVAILABLE_MESSAGE = "Vector search is unavailable. Check Vertex AI and Oracle configuration, then retry."


def is_expected_service_unavailable(exc: BaseException) -> bool:
    text = str(exc).lower()
    if isinstance(exc, genai_errors.ClientError):
        return any(
            marker in text
            for marker in (
                "api key",
                "credentials",
                "permission_denied",
                "service_disabled",
                "forbidden",
                "unauthorized",
            )
        )
    return any(
        marker in text
        for marker in (
            "api key",
            "credentials",
            "permission_denied",
            "service_disabled",
            "vertex ai api has not been used",
        )
    )


def payload_value(payload: Any, key: str, default: str = "") -> str:
    getter = getattr(payload, "get", None)
    value = getter(key, default) if callable(getter) else default
    if isinstance(value, list | tuple):
        value = value[0] if value else default
    return str(value or default)


def unavailable_plan(message: str = SERVICE_UNAVAILABLE_MESSAGE) -> ExplainPlan:
    return ExplainPlan(plan_lines=[message], plan_summary="Plan unavailable")


async def vector_query_from_request(request: HTMXRequest) -> VectorQuery:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        payload = await request.form()
    return VectorQuery(query=payload_value(payload, "query"))


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
    sanitized = sanitize_oracle_text_query(query)
    cache_status = "hit" if cache_hit else "miss"
    vector_digest = "<VECTOR[3072 FLOAT32], model=gemini-embedding-2>"
    return [
        build_sql_phase(
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
        ).to_dict(),
        build_sql_phase(
            label="Oracle 26ai HNSW Vector search (FETCH APPROX)",
            sql_key="vector-search-products",
            binds={"query_vector": vector_digest, "threshold": 0.5, "limit": 5},
            row_count=len(matches),
            runtime_ms=oracle_ms,
            cache_status=cache_status,
        ).to_dict(),
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
    sanitized = sanitize_oracle_text_query(query)
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
        "hybrid_detail_json": msgspec.json.encode(hybrid_detail).decode("utf-8"),
        "vector_detail_json": msgspec.json.encode(vector_detail).decode("utf-8"),
    }


def _format_rrf_formula(lexical_rank: int | None, vector_rank: int | None, rrf_score: float, rrf_k: int) -> str:
    lex_part = f"1/({rrf_k}+{lexical_rank})" if lexical_rank is not None else "0"
    vec_part = f"1/({rrf_k}+{vector_rank})" if vector_rank is not None else "0"
    return f"{lex_part} + {vec_part} = {rrf_score:.4f}"
