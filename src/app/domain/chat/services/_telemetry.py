# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Telemetry phase, search metrics, and location privacy helpers for chat turns."""

from __future__ import annotations

import re
from hashlib import sha256
from math import fsum, sqrt
from typing import TYPE_CHECKING, Any

import msgspec

from app.config import db_manager
from app.domain.products.services import build_store_directions_url, build_store_search_url
from app.utils.serialization import sanitize_for_json

if TYPE_CHECKING:
    from app.domain.chat.schemas import HybridTurnContext

_MIN_LATITUDE = -90.0
_MAX_LATITUDE = 90.0
_MIN_LONGITUDE = -180.0
_MAX_LONGITUDE = 180.0
_KNOWN_CITY_FILTERS: tuple[tuple[str, str | None], ...] = (
    ("Austin", "TX"),
    ("Berkeley", "CA"),
    ("Dallas", "TX"),
    ("Denver", "CO"),
    ("Fresno", "CA"),
    ("Los Angeles", "CA"),
    ("Oakland", "CA"),
    ("Palo Alto", "CA"),
    ("Portland", "OR"),
    ("Sacramento", "CA"),
    ("San Diego", "CA"),
    ("San Francisco", "CA"),
    ("San Jose", "CA"),
    ("Santa Monica", "CA"),
    ("Seattle", "WA"),
)
_PRODUCT_QUERY_ALIASES: tuple[tuple[str, str], ...] = (
    ("cold brew", "Cold Brew Nitro"),
    ("nitro", "Cold Brew Nitro"),
    ("espresso", "Espresso Romano"),
)
_PRODUCT_QUERY_STOP_WORDS = frozenset({
    "where",
    "can",
    "i",
    "pick",
    "up",
    "near",
    "me",
    "is",
    "are",
    "available",
    "availability",
    "which",
    "cafe",
    "store",
    "has",
    "have",
    "in",
    "at",
    "do",
    "you",
    "the",
    "a",
    "an",
    "that",
    "this",
    "it",
    "them",
    "those",
    "stock",
    "nearby",
    "here",
    "there",
})


class SQLPhase(msgspec.Struct, kw_only=True):
    """Structured SQL execution phase emitted in the chat SSE final payload."""

    label: str
    sql_key: str
    sql: str
    binds: dict[str, Any]
    row_count: int
    runtime_ms: float
    cache_status: str = "miss"

    def to_dict(self) -> dict[str, Any]:
        """Serialize SQLPhase to a plain dictionary for JSON streaming."""
        return {
            "label": self.label,
            "sql_key": self.sql_key,
            "sql": self.sql,
            "binds": self.binds,
            "row_count": self.row_count,
            "runtime_ms": round(self.runtime_ms, 2),
            "cache_status": self.cache_status,
        }


class SearchMetrics(msgspec.Struct, kw_only=True):
    """Structured retrieval and grounding metrics emitted in the chat SSE final payload."""

    vector_query: str
    total_ms: float
    embedding_ms: float
    oracle_ms: float
    results_count: int
    products_found: int
    similarity_scores: list[float] = []
    avg_similarity: float | None = None
    rrf_scores: list[float] = []
    lexical_hits: int = 0
    grounded_answer_mode: str | None = None
    grounded_answer_ms: float | None = None
    product_query: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize SearchMetrics to a plain dictionary for JSON streaming."""
        payload: dict[str, Any] = {
            "vector_query": self.vector_query,
            "total_ms": round(self.total_ms),
            "embedding_ms": round(self.embedding_ms, 2),
            "oracle_ms": round(self.oracle_ms, 2),
            "results_count": self.results_count,
            "products_found": self.products_found,
            "similarity_scores": [round(score, 4) for score in self.similarity_scores],
            "avg_similarity": round(self.avg_similarity, 4) if self.avg_similarity is not None else None,
            "rrf_scores": [round(score, 6) for score in self.rrf_scores],
            "lexical_hits": self.lexical_hits,
        }
        if self.grounded_answer_mode is not None:
            payload["grounded_answer_mode"] = self.grounded_answer_mode
        if self.grounded_answer_ms is not None:
            payload["grounded_answer_ms"] = round(self.grounded_answer_ms, 2)
        if self.product_query is not None:
            payload["product_query"] = self.product_query
        return payload


def summarize_vector(values: Any) -> str:
    """Return a compact, deterministic digest and norm summary for an embedding vector."""
    if not isinstance(values, list | tuple) or not values:
        return "<VECTOR[unknown FLOAT32]>"
    floats = [float(value) for value in values]
    digest = sha256(",".join(f"{value:.8g}" for value in floats).encode()).hexdigest()[:12]
    norm = sqrt(fsum(value * value for value in floats))
    return f"<VECTOR[{len(floats)} FLOAT32], sha256={digest}, norm={norm:.4f}>"


def build_sql_phase(
    *, label: str, sql_key: str, binds: dict[str, Any], row_count: int, runtime_ms: float, cache_status: str = "miss"
) -> SQLPhase:
    """Construct a single SQLPhase struct with sanitized bind parameters."""
    return SQLPhase(
        label=label,
        sql_key=sql_key,
        sql=_named_sql_text(sql_key),
        binds=sanitize_for_json(binds),
        row_count=row_count,
        runtime_ms=round(runtime_ms, 2),
        cache_status=cache_status,
    )


def build_response_cache_phase(cache_key: str, *, hit: bool, runtime_ms: float) -> SQLPhase:
    """Construct the SQLPhase entry for a response-cache lookup."""
    return build_sql_phase(
        label="Response cache lookup",
        sql_key="get-cached-response",
        binds={"key_hash": _sha256_text(cache_key)[:16]},
        row_count=1 if hit else 0,
        runtime_ms=runtime_ms,
        cache_status="hit" if hit else "miss",
    )


def build_hybrid_sql_phases(
    *,
    query: str,
    turn_context: HybridTurnContext,
    query_embedding: list[float] | None,
    embedding_ms: float,
    oracle_ms: float,
    embedding_cache_hit: bool,
    embedding_model: str = "gemini-embedding-2",
    similarity_threshold: float = 0.45,
    rrf_k: int = 60,
    limit: int = 5,
) -> list[SQLPhase]:
    """Build SQLPhase records for the embedding lookup, hybrid-search-turn RRF query, and term hits."""
    phases: list[SQLPhase] = [
        build_sql_phase(
            label="Embedding cache lookup",
            sql_key="get-cached-embedding",
            binds={"hash": _sha256_text(query), "model": embedding_model},
            row_count=1 if embedding_cache_hit else 0,
            runtime_ms=embedding_ms,
            cache_status="hit" if embedding_cache_hit else "miss",
        ),
        build_sql_phase(
            label="Oracle Hybrid RRF search",
            sql_key="hybrid-search-turn",
            binds={
                "has_text_query": 1 if turn_context.oracle_text_query is not None else 0,
                "text_query": turn_context.oracle_text_query or "{coffee}",
                "query_vector": summarize_vector(query_embedding),
                "threshold": similarity_threshold,
                "rrf_k": rrf_k,
                "limit": limit,
            },
            row_count=len(turn_context.products) + len(turn_context.stores) + 1,
            runtime_ms=oracle_ms,
            cache_status="miss",
        ),
    ]
    if turn_context.term_hits:
        phases.append(
            build_sql_phase(
                label="Oracle Text term hit verification",
                sql_key="hybrid-term-hits",
                binds={"terms_json": list(turn_context.term_hits.keys())},
                row_count=len(turn_context.term_hits),
                runtime_ms=round(oracle_ms * 0.15, 2),
                cache_status="miss",
            )
        )
    return phases


def build_search_metrics(
    *,
    query: str,
    turn_context: HybridTurnContext,
    total_ms: float,
    embedding_ms: float,
    oracle_ms: float,
    results_count: int | None = None,
    grounded_answer_mode: str | None = None,
    grounded_answer_ms: float | None = None,
    product_query: str | None = None,
) -> SearchMetrics:
    """Build SearchMetrics from a resolved HybridTurnContext and phase timings."""
    similarities = [
        float(product.vector_similarity) for product in turn_context.products if product.vector_similarity is not None
    ]
    rrf_scores = [float(product.rrf_score) for product in turn_context.products]
    lexical_hits = sum(1 for product in turn_context.products if product.lexical_rank is not None)
    avg_similarity = (fsum(similarities) / len(similarities)) if similarities else None
    products_found = len(turn_context.products)
    effective_results_count = products_found if results_count is None else results_count
    return SearchMetrics(
        vector_query=query,
        total_ms=round(total_ms, 2),
        embedding_ms=round(embedding_ms, 2),
        oracle_ms=round(oracle_ms, 2),
        results_count=effective_results_count,
        products_found=products_found,
        similarity_scores=similarities,
        avg_similarity=avg_similarity,
        rrf_scores=rrf_scores,
        lexical_hits=lexical_hits,
        grounded_answer_mode=grounded_answer_mode,
        grounded_answer_ms=grounded_answer_ms,
        product_query=product_query,
    )


def request_coordinates(location_context: dict[str, Any] | None) -> tuple[float, float] | None:
    """Extract validated (latitude, longitude) coordinates from request-scoped location_context."""
    if not isinstance(location_context, dict):
        return None
    coordinates = location_context.get("coordinates")
    if not isinstance(coordinates, dict):
        return None
    latitude = coordinates.get("latitude")
    longitude = coordinates.get("longitude")
    if not isinstance(latitude, int | float) or not isinstance(longitude, int | float):
        return None
    lat_val = float(latitude)
    lon_val = float(longitude)
    if not _MIN_LATITUDE <= lat_val <= _MAX_LATITUDE or not _MIN_LONGITUDE <= lon_val <= _MAX_LONGITUDE:
        return None
    return lat_val, lon_val


def safe_location_context(location_context: dict[str, Any] | None) -> dict[str, Any]:
    """Return a masked location context with raw browser coordinates stripped out."""
    if not isinstance(location_context, dict):
        return {}
    safe: dict[str, Any] = {}
    for key in ("city", "state", "zip_code", "store_name"):
        value = location_context.get(key)
        if value:
            safe[key] = str(value)
    coordinates = location_context.get("coordinates")
    if isinstance(coordinates, dict) and request_coordinates(location_context) is not None:
        safe["has_browser_coordinates"] = True
        accuracy = coordinates.get("accuracy_meters")
        if isinstance(accuracy, int | float):
            safe["accuracy_meters"] = float(accuracy)
    return safe


def extract_location_filters(query: str, location_context: dict[str, Any] | None) -> dict[str, str | None]:
    """Extract city, state, and zip_code filters from location_context or query text."""
    context = location_context if isinstance(location_context, dict) else {}
    filters: dict[str, str | None] = {
        "city": str(context.get("city") or "").strip() or None,
        "state": str(context.get("state") or "").strip() or None,
        "zip_code": str(context.get("zip_code") or "").strip() or None,
    }
    query_text = query.casefold()
    if not filters["zip_code"]:
        zip_match = re.search(r"\b\d{5}(?:-\d{4})?\b", query)
        if zip_match:
            filters["zip_code"] = zip_match.group(0)
    if not filters["city"]:
        for city, state in _KNOWN_CITY_FILTERS:
            if city.casefold() in query_text:
                filters["city"] = city
                if not filters["state"] and state:
                    filters["state"] = state
                break
    return filters


def extract_product_query(query: str) -> str | None:
    """Extract a normalized product search phrase from a customer availability query."""
    query_text = query.casefold()
    for needle, product_name in _PRODUCT_QUERY_ALIASES:
        if needle in query_text:
            return product_name
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", query_text)
    words = [word for word in cleaned.split() if word not in _PRODUCT_QUERY_STOP_WORDS]
    joined = " ".join(words)
    return joined.title() if joined else None


def build_map_actions(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build no-key Google Maps search and directions action links for store or inventory rows."""
    actions: list[dict[str, str]] = []
    for row in rows:
        name = str(row.get("name") or row.get("store_name") or "Cymbal Coffee").strip() or "Cymbal Coffee"
        address = str(row.get("address") or row.get("store_address") or "").strip()
        city = str(row.get("city") or row.get("store_city") or "").strip()
        state = str(row.get("state") or row.get("store_state") or "").strip()
        zip_code = str(row.get("zip") or row.get("store_zip") or "").strip()
        place_id = str(row.get("google_place_id") or "") or None
        actions.extend((
            {
                "type": "search",
                "label": "Open in Google Maps",
                "url": build_store_search_url(
                    name=name, address=address, city=city, state=state, zip_code=zip_code, place_id=place_id
                ),
            },
            {
                "type": "directions",
                "label": "Get directions",
                "url": build_store_directions_url(
                    name=name, address=address, city=city, state=state, zip_code=zip_code, place_id=place_id
                ),
            },
        ))
    return actions


def _named_sql_text(sql_key: str) -> str:
    try:
        return str(db_manager.get_sql(sql_key).sql)
    except Exception:
        return sql_key


def _sha256_text(value: str) -> str:
    return sha256(value.encode()).hexdigest()


__all__ = (
    "SQLPhase",
    "SearchMetrics",
    "build_hybrid_sql_phases",
    "build_map_actions",
    "build_response_cache_phase",
    "build_search_metrics",
    "build_sql_phase",
    "extract_location_filters",
    "extract_product_query",
    "request_coordinates",
    "safe_location_context",
    "summarize_vector",
)
