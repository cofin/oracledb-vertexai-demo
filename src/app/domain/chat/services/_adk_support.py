# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Private history coercion and telemetry helpers for ADK chat turns."""

from __future__ import annotations

from hashlib import sha256
from math import fsum, sqrt
from typing import Any

from app.config import db_manager
from app.domain.chat.schemas import ChatMessage
from app.utils.serialization import sanitize_for_json

_PRODUCT_RAG_INTENT = "PRODUCT_RAG"


def _coerce_history_messages(value: Any) -> list[ChatMessage]:
    if not isinstance(value, list):
        return []
    messages: list[ChatMessage] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "")
        message = str(item.get("message") or "")
        if source in {"human", "ai"} and message:
            messages.append(ChatMessage(source=source, message=message))
    return messages


def _event_content_text(event: Any) -> str:
    """Extract text from an ADK event."""
    if not event.content or not event.content.parts:
        return ""
    return "".join(str(part.text) for part in event.content.parts if getattr(part, "text", None))


def _event_history_messages(events: Any) -> list[ChatMessage]:
    if not isinstance(events, list):
        return []
    messages: list[ChatMessage] = []
    for event in events:
        if getattr(event, "partial", False):
            continue
        text = _event_content_text(event).strip()
        if not text:
            continue
        role = getattr(getattr(event, "content", None), "role", None)
        author = str(getattr(event, "author", "") or "")
        if role == "user":
            messages.append(ChatMessage(source="human", message=text))
        elif role == "model" and author in {"coffee_turn", "CoffeeAssistant", "model"}:
            messages.append(ChatMessage(source="ai", message=text))
    return messages


def _named_sql_text(sql_key: str) -> str:
    return str(db_manager.get_sql(sql_key).sql)


def _sha256_text(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _summarize_vector(values: Any) -> str:
    if not isinstance(values, list | tuple):
        return "<VECTOR[unknown FLOAT32]>"
    floats = [float(value) for value in values]
    digest = sha256(",".join(f"{value:.8g}" for value in floats).encode()).hexdigest()[:12]
    norm = sqrt(fsum(value * value for value in floats))
    return f"<VECTOR[{len(floats)} FLOAT32], sha256={digest}, norm={norm:.4f}>"


def _sql_phase(
    *, label: str, sql_key: str, binds: dict[str, Any], row_count: int, runtime_ms: float, cache_status: str
) -> dict[str, Any]:
    return {
        "label": label,
        "sql_key": sql_key,
        "sql": _named_sql_text(sql_key),
        "binds": sanitize_for_json(binds),
        "row_count": row_count,
        "runtime_ms": round(runtime_ms, 2),
        "cache_status": cache_status,
    }


def _response_cache_phase(cache_key: str, *, hit: bool, runtime_ms: float) -> dict[str, Any]:
    return _sql_phase(
        label="Response cache lookup",
        sql_key="get-cached-response",
        binds={"key_hash": _sha256_text(cache_key)[:16]},
        row_count=1 if hit else 0,
        runtime_ms=runtime_ms,
        cache_status="hit" if hit else "miss",
    )


def _coerce_sql_phases(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict) and item.get("sql_key")]


def _record_tool_sql_phases(metric_state: dict[str, Any], result: dict[str, Any]) -> None:
    sql_phases = _coerce_sql_phases(result.get("sql_phases"))
    if sql_phases:
        metric_state.setdefault("sql_phases", []).extend(sql_phases)


def _similarity_score(products: list[Any]) -> float | None:
    if not products:
        return None
    first = products[0]
    value = first.get("similarity_score") if isinstance(first, dict) else getattr(first, "similarity_score", None)
    return float(value) if isinstance(value, int | float) else None


def _product_lookup_ran(search_metrics: dict[str, Any], sql_phases: list[dict[str, Any]]) -> bool:
    return bool(
        search_metrics.get("vector_query")
        or search_metrics.get("products_found")
        or search_metrics.get("results_count")
        or any(phase.get("sql_key") == "vector-search-products" for phase in sql_phases)
    )


def _effective_intent(intent_detected: str, search_metrics: dict[str, Any], sql_phases: list[dict[str, Any]]) -> str:
    if _product_lookup_ran(search_metrics, sql_phases):
        return _PRODUCT_RAG_INTENT
    return intent_detected
