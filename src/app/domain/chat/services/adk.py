# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ADK 2.0 chat runner with closure-bound tools and parallel intent classification."""

from __future__ import annotations

import re
import time
import uuid
from hashlib import sha256
from inspect import isawaitable
from math import fsum, sqrt
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlencode, urlunsplit

import structlog
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import errors as genai_errors
from google.genai import types
from sqlspec.adapters.oracledb import OracleAsyncDriver
from sqlspec.extensions.adk import SQLSpecSessionService  # noqa: TC002

from app.config import db_manager
from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.schemas import ChatMessage
from app.domain.chat.services.classifier import (
    FlashLiteIntentClassifier,
    IntentLabel,
)
from app.domain.chat.services.workflow import make_workflow
from app.domain.products.services import ProductService, StoreService, VertexAIService  # noqa: TC001
from app.domain.system.schemas import SearchMetricsCreate
from app.domain.system.services import BASE_SYSTEM_INSTRUCTION, CacheService, MetricsService, PersonaManager
from app.lib.service import SQLSpecAsyncService
from app.lib.settings import get_settings
from app.utils.serialization import sanitize_for_json

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from google.adk.agents.callback_context import CallbackContext
    from google.adk.agents.llm_agent import ToolUnion

logger = structlog.get_logger()

_APP_NAME = "coffee_assistant"
_UNCONFIGURED_MESSAGE = "AI service is not configured. Set GOOGLE_API_KEY or VERTEX_AI_API_KEY in your .env file."
_PLACEHOLDER_PROJECT_IDS = frozenset({"demo-project", "your-project-id", "your-gcp-project-id"})
_CHAT_CACHE_VERSION = "menu-grounded-v1"
_PRODUCT_RAG_INTENT = "PRODUCT_RAG"
_PRODUCT_AVAILABILITY_INTENT = "PRODUCT_AVAILABILITY"
_STORE_LOCATION_INTENT = "STORE_LOCATION"
_ORDER_STATUS_INTENT = "ORDER_STATUS"
_DISPLAY_HISTORY_STATE_KEY = "display_history"
_CHAT_RESULT_KEYS: tuple[str, ...] = (
    "answer",
    "session_id",
    "response_time_ms",
    "intent_detected",
    "search_metrics",
    "from_cache",
    "embedding_cache_hit",
    "sql_phases",
    "store_results",
    "inventory_results",
    "map_actions",
    "location_context",
)
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
_MIN_LATITUDE = -90.0
_MAX_LATITUDE = 90.0
_MIN_LONGITUDE = -180.0
_MAX_LONGITUDE = 180.0


def _coerce_products(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict) and item.get("name")]


def _format_price(value: Any) -> str:
    if not isinstance(value, int | float):
        return ""
    return f" (${value:.2f})"


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
    *,
    label: str,
    sql_key: str,
    binds: dict[str, Any],
    row_count: int,
    runtime_ms: float,
    cache_status: str,
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


def _grounded_product_answer(query: str, products: list[dict[str, Any]]) -> str:
    menu_products = _coerce_products(products)
    if not menu_products:
        return "I couldn't find a matching Cymbal Coffee menu item for that. Try another flavor, roast, or drink style and I'll check the menu again."

    first = menu_products[0]
    lead = "For breakfast" if "breakfast" in query.casefold() else "For that"
    name = str(first["name"])
    description = str(first.get("description") or "").strip()
    answer = f"{lead}, I'd start with {name}{_format_price(first.get('price'))}"
    if description:
        answer += f": {description}"
    else:
        answer += "."

    if len(menu_products) > 1:
        second = menu_products[1]
        answer += f" Another good menu option is {second['name']}{_format_price(second.get('price'))}."
    return answer


def _coerce_dict_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _default_route_fields(location_context: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "store_results": [],
        "inventory_results": [],
        "map_actions": [],
        "location_context": _safe_location_context(location_context),
    }


def _safe_location_context(location_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(location_context, dict):
        return {}

    safe: dict[str, Any] = {}
    for key in ("city", "state", "zip_code", "store_name"):
        value = location_context.get(key)
        if value:
            safe[key] = str(value)

    coordinates = location_context.get("coordinates")
    if isinstance(coordinates, dict) and _request_coordinates(location_context):
        safe["has_browser_coordinates"] = True
        accuracy = coordinates.get("accuracy_meters")
        if isinstance(accuracy, int | float):
            safe["accuracy_meters"] = float(accuracy)
    return safe


def _request_coordinates(location_context: dict[str, Any] | None) -> tuple[float, float] | None:
    if not isinstance(location_context, dict):
        return None
    coordinates = location_context.get("coordinates")
    if not isinstance(coordinates, dict):
        return None
    latitude = coordinates.get("latitude")
    longitude = coordinates.get("longitude")
    if not isinstance(latitude, int | float) or not isinstance(longitude, int | float):
        return None
    if not _MIN_LATITUDE <= float(latitude) <= _MAX_LATITUDE or not (
        _MIN_LONGITUDE <= float(longitude) <= _MAX_LONGITUDE
    ):
        return None
    return float(latitude), float(longitude)


def _has_browser_coordinates(location_context: dict[str, Any] | None) -> bool:
    return _request_coordinates(location_context) is not None


def _extract_location_filters(query: str, location_context: dict[str, Any] | None) -> dict[str, str | None]:
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
        for city, _state in _KNOWN_CITY_FILTERS:
            if city.casefold() in query_text:
                filters["city"] = city
                break
    return filters


def _extract_product_query(query: str) -> str:
    query_text = query.casefold()
    for needle, product_name in _PRODUCT_QUERY_ALIASES:
        if needle in query_text:
            return product_name

    cleaned = re.sub(
        r"\b(where|can|i|pick|up|near|me|is|are|available|availability|which|cafe|store|has|have|in|at|do|you|the|a|an)\b",
        " ",
        query_text,
    )
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned.title() if cleaned else query


def _store_query_parts(row: dict[str, Any]) -> tuple[str, str]:
    name = str(row.get("name") or row.get("store_name") or "Cymbal Coffee").strip()
    address = str(row.get("address") or row.get("store_address") or "").strip()
    city = str(row.get("city") or row.get("store_city") or "").strip()
    state = str(row.get("state") or row.get("store_state") or "").strip()
    zip_code = str(row.get("zip") or row.get("store_zip") or "").strip()
    locality = " ".join(part for part in (state, zip_code) if part)
    city_region = ", ".join(part for part in (city, locality) if part)
    query = ", ".join(part for part in (name, address, city_region) if part)
    return name, query or name


def _maps_search_url(query: str, place_id: str | None = None) -> str:
    params = {"api": "1", "query": query}
    if place_id:
        params["query_place_id"] = place_id
    return urlunsplit(("https", "www.google.com", "/maps/search/", urlencode(params), ""))


def _build_map_actions(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for row in rows:
        label, query = _store_query_parts(row)
        actions.append(
            {
                "type": "search",
                "label": label,
                "url": _maps_search_url(query, str(row.get("google_place_id") or "") or None),
            }
        )
    return actions


def _format_hours(hours: Any) -> str:
    if not isinstance(hours, dict) or not hours:
        return ""
    monday = hours.get("monday")
    if monday:
        return f" Hours: Monday {monday}."
    first_key, first_value = next(iter(hours.items()))
    return f" Hours: {str(first_key).title()} {first_value}."


def _format_store_location_answer(stores: list[dict[str, Any]]) -> str:
    if not stores:
        return "I couldn't find a matching Cymbal Coffee store for that location. Try a city, ZIP code, or nearby landmark."

    first = stores[0]
    name, _query = _store_query_parts(first)
    address = str(first.get("address") or "").strip()
    city = str(first.get("city") or "").strip()
    state = str(first.get("state") or "").strip()
    zip_code = str(first.get("zip") or "").strip()
    phone = str(first.get("phone") or "").strip()
    location = ", ".join(part for part in (address, city, " ".join(part for part in (state, zip_code) if part)) if part)
    answer = f"{name}"
    if location:
        answer += f" is at {location}."
    else:
        answer += " is the closest matching Cymbal Coffee location."
    if phone:
        answer += f" Phone: {phone}."
    answer += _format_hours(first.get("hours"))
    if len(stores) > 1:
        answer += f" I found {len(stores)} matching stores."
    return answer


def _format_availability_answer(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "I couldn't find current store-level availability for that product. Try another menu item or nearby location."

    first = rows[0]
    product = str(first.get("product_name") or "that item")
    store = str(first.get("store_name") or "a Cymbal Coffee store")
    status = str(first.get("stock_status") or "").replace("_", " ").title()
    quantity = first.get("quantity_available")
    answer = f"{product} is available at {store}"
    if status:
        answer += f" ({status})"
    if isinstance(quantity, int | float):
        answer += f" with {int(quantity)} on hand"
    distance = first.get("distance_miles")
    if isinstance(distance, int | float):
        answer += f", about {float(distance):.1f} miles away"
    answer += "."
    if len(rows) > 1:
        answer += f" I found {len(rows)} stores with matching availability."
    return answer


def _record_product_search_result(metric_state: dict[str, Any], result: dict[str, Any], query: str) -> None:
    metric_state["embedding_cache_hit"] = bool(result.get("embedding_cache_hit"))
    products = _coerce_products(result.get("products"))
    if products:
        metric_state["rag_products"] = products
    products_found = int(result.get("results_count") or len(products))
    search_metrics = metric_state.setdefault("search_metrics", {})
    tool_metrics = result.get("search_metrics")
    if isinstance(tool_metrics, dict):
        search_metrics.update(tool_metrics)
    search_metrics["vector_query"] = str(result.get("vector_query") or query)
    search_metrics["results_count"] = products_found
    search_metrics["products_found"] = products_found
    sql_phases = _coerce_sql_phases(result.get("sql_phases"))
    if sql_phases:
        metric_state.setdefault("sql_phases", []).extend(sql_phases)


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


async def _ground_product_rag_turn(
    query: str,
    metric_state: dict[str, Any],
    tools_service: AgentToolsService,
) -> str:
    products = _coerce_products(metric_state.get("rag_products"))
    if not products:
        fallback_result = await tools_service.search_products_by_vector(query, 3, 0.5)
        _record_product_search_result(metric_state, fallback_result, query)
        products = _coerce_products(metric_state.get("rag_products"))
    return _grounded_product_answer(query, products)


class AgentToolsService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Business logic invoked by closure-bound ADK tools."""

    def __init__(
        self,
        driver: OracleAsyncDriver,
        product_service: ProductService,
        metrics_service: MetricsService,
        vertex_ai_service: VertexAIService,
        store_service: StoreService,
        cache_service: CacheService,
    ) -> None:
        super().__init__(driver)
        self.product_service = product_service
        self.metrics_service = metrics_service
        self.vertex_ai_service = vertex_ai_service
        self.store_service = store_service
        self.cache_service = cache_service

    async def search_products_by_vector(
        self, query: str, limit: int = 5, similarity_threshold: float = 0.7
    ) -> dict[str, Any]:
        embedding_start = time.time()
        embedding, cache_hit = await self.vertex_ai_service.get_text_embedding(
            query,
            task_type="RETRIEVAL_QUERY",
            return_cache_status=True,
        )
        embedding_ms = (time.time() - embedding_start) * 1000

        oracle_start = time.time()
        products = await self.product_service.search_by_vector(embedding, similarity_threshold, limit)
        oracle_ms = (time.time() - oracle_start) * 1000
        tool_total_ms = embedding_ms + oracle_ms
        model = str(getattr(self.vertex_ai_service, "embedding_model", "unknown"))
        await self.metrics_service.record_search(
            SearchMetricsCreate(
                query_id=str(uuid.uuid4()),
                user_id="chat",
                search_time_ms=tool_total_ms,
                embedding_time_ms=embedding_ms,
                oracle_time_ms=oracle_ms,
                similarity_score=_similarity_score(products),
                result_count=len(products),
            )
        )
        return {
            "products": sanitize_for_json(products),
            "embedding_cache_hit": cache_hit,
            "results_count": len(products),
            "vector_query": query,
            "search_metrics": {
                "vector_query": query,
                "embedding_ms": round(embedding_ms, 2),
                "oracle_ms": round(oracle_ms, 2),
                "tool_ms": round(tool_total_ms, 2),
            },
            "sql_phases": [
                _sql_phase(
                    label="Embedding cache lookup",
                    sql_key="get-cached-embedding",
                    binds={"hash": _sha256_text(query), "model": model},
                    row_count=1 if cache_hit else 0,
                    runtime_ms=embedding_ms,
                    cache_status="hit" if cache_hit else "miss",
                ),
                _sql_phase(
                    label="Oracle vector search",
                    sql_key="vector-search-products",
                    binds={
                        "query_vector": _summarize_vector(embedding),
                        "threshold": similarity_threshold,
                        "limit": limit,
                    },
                    row_count=len(products),
                    runtime_ms=oracle_ms,
                    cache_status="miss",
                ),
            ],
        }

    async def get_product_details(self, product_id: str) -> dict[str, Any]:
        try:
            product = await self.product_service.get_by_id(int(product_id))
        except ValueError:
            product = await self.product_service.get_by_name(product_id)
        return cast("dict[str, Any]", sanitize_for_json(product)) if product else {"error": "Product not found"}

    async def record_search_metric(
        self,
        session_id: str,
        query_text: str,
        intent: str,
        vector_results: list[dict[str, Any]],
        total_response_time_ms: int,
        vector_search_time_ms: int = 0,
        embedding_time_ms: int = 0,
        query_id: str | None = None,
    ) -> dict[str, Any]:
        from app.domain.system.schemas import SearchMetricsCreate

        metrics = SearchMetricsCreate(
            query_id=query_id or str(uuid.uuid4()),
            user_id=session_id,
            search_time_ms=float(total_response_time_ms),
            embedding_time_ms=float(embedding_time_ms),
            oracle_time_ms=float(vector_search_time_ms),
            result_count=len(vector_results),
        )
        await self.metrics_service.record_search(metrics)
        return {"status": "recorded"}

    async def get_all_store_locations(self) -> list[dict[str, Any]]:
        stores = await self.store_service.get_all_stores()
        return cast("list[dict[str, Any]]", sanitize_for_json(stores))

    async def find_stores_by_location(
        self,
        *,
        city: str | None = None,
        state: str | None = None,
        zip_code: str | None = None,
    ) -> dict[str, Any]:
        started = time.time()
        stores = await self.store_service.find_stores_by_location(city=city, state=state, zip_code=zip_code)
        return {
            "stores": sanitize_for_json(stores),
            "results_count": len(stores),
            "sql_phases": [
                _sql_phase(
                    label="Store location lookup",
                    sql_key="find-stores-by-location",
                    binds={"city": city, "state": state, "zip_code": zip_code},
                    row_count=len(stores),
                    runtime_ms=(time.time() - started) * 1000,
                    cache_status="miss",
                )
            ],
        }

    async def get_store_hours(self, store_id: int) -> dict[str, Any]:
        started = time.time()
        hours = await self.store_service.get_store_hours(store_id)
        payload: dict[str, Any] = cast("dict[str, Any]", sanitize_for_json(hours)) if hours else {"error": "Store not found"}
        payload["sql_phases"] = [
            _sql_phase(
                label="Store hours lookup",
                sql_key="get-store-by-id",
                binds={"id": store_id},
                row_count=0 if hours is None else 1,
                runtime_ms=(time.time() - started) * 1000,
                cache_status="miss",
            )
        ]
        return payload

    async def find_nearest_stores(self, latitude: float, longitude: float, limit: int = 5) -> dict[str, Any]:
        started = time.time()
        stores = await self.store_service.find_nearest_stores(latitude, longitude, limit)
        return {
            "stores": sanitize_for_json(stores),
            "results_count": len(stores),
            "sql_phases": [
                _sql_phase(
                    label="Nearest store lookup",
                    sql_key="list-stores",
                    binds={"origin": "<REQUEST_COORDINATES>", "limit": limit},
                    row_count=len(stores),
                    runtime_ms=(time.time() - started) * 1000,
                    cache_status="miss",
                )
            ],
        }

    async def find_stores_with_product(
        self,
        product_query: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict[str, Any]:
        started = time.time()
        coordinates = (latitude, longitude) if latitude is not None and longitude is not None else None
        availability = await self.store_service.find_product_availability(product_query, coordinates=coordinates)
        binds: dict[str, Any] = {"product_query": product_query}
        if coordinates:
            binds["origin"] = "<REQUEST_COORDINATES>"
        return {
            "availability": sanitize_for_json(availability),
            "results_count": len(availability),
            "sql_phases": [
                _sql_phase(
                    label="Product availability lookup",
                    sql_key="find-product-availability-by-query",
                    binds=binds,
                    row_count=len(availability),
                    runtime_ms=(time.time() - started) * 1000,
                    cache_status="miss",
                )
            ],
        }

    def make_response_cache_key(self, query: str, persona: str) -> str:
        normalized = " ".join(query.casefold().split())
        model = self.vertex_ai_service.model
        digest = sha256(f"{_CHAT_CACHE_VERSION}:{model}:{persona}:{normalized}".encode()).hexdigest()
        return f"chat:{digest}"

    async def get_cached_chat_response(self, cache_key: str) -> dict[str, Any] | None:
        cached = await self.cache_service.get_cached_response(cache_key)
        return cached.response_data if cached else None

    async def set_cached_chat_response(self, cache_key: str, response_data: dict[str, Any]) -> None:
        await self.cache_service.set_cached_response(cache_key, response_data, ttl_minutes=60)


def credential_guard_callback(callback_context: CallbackContext) -> types.Content | None:
    """Short-circuit the agent with a 503 message when credentials are missing.

    Returns:
        A model response when credentials are missing, otherwise ``None``.
    """
    del callback_context
    if _has_vertex_ai_backend_config():
        return None
    return types.Content(
        role="model",
        parts=[types.Part(text=_UNCONFIGURED_MESSAGE)],
    )


def _has_vertex_ai_backend_config() -> bool:
    settings = get_settings()
    project_id = settings.vertex_ai.PROJECT_ID.strip()
    return bool(settings.vertex_ai.API_KEY or (project_id and project_id not in _PLACEHOLDER_PROJECT_IDS))


def _ensure_vertex_ai_backend_configured() -> None:
    if not _has_vertex_ai_backend_config():
        raise AIServiceUnconfigured(_UNCONFIGURED_MESSAGE)


def _is_credential_error(exc: BaseException) -> bool:
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
    return "api key" in text or "credentials" in text


def _event_content_text(event: Any) -> str:
    """Extract text from an ADK event.

    Returns:
        Concatenated text parts, or an empty string when the event has no text.
    """
    if not event.content or not event.content.parts:
        return ""
    return "".join(str(part.text) for part in event.content.parts if getattr(part, "text", None))


class ADKRunner:
    """Per-request ADK 2.0 workflow with closure-bound tools."""

    def __init__(
        self,
        session_service: SQLSpecSessionService,
        classifier: FlashLiteIntentClassifier,
        persona_manager: PersonaManager,
    ) -> None:
        self._session_service = session_service
        self._classifier = classifier
        self._persona_manager = persona_manager

    def _make_tool_factories(self, tools_service: AgentToolsService, metric_state: dict[str, Any]) -> list[ToolUnion]:
        async def search_products_by_vector(
            query: str, limit: int = 5, similarity_threshold: float = 0.7
        ) -> dict[str, Any]:
            """Search the Cymbal Coffee menu with vector RAG.

            Use for menu, catalog, recommendation, flavor, roast, price, caffeine,
            availability, dietary substitution, and idiomatic preference requests.

            Returns:
                Matching menu products and cache/search metadata. Only these
                returned products may be recommended to the user.
            """
            result = await tools_service.search_products_by_vector(query, limit, similarity_threshold)
            _record_product_search_result(metric_state, result, query)
            return result

        async def get_product_details(product_id: str) -> dict[str, Any]:
            """Get exact details for a Cymbal Coffee product by id or name.

            Returns:
                Product details, or an error object when no product matches.
            """
            result = await tools_service.get_product_details(product_id)
            if "error" not in result and result.get("name"):
                metric_state["rag_products"] = [result]
            return result

        async def get_all_store_locations() -> list[dict[str, Any]]:
            """List Cymbal Coffee store locations for address, hours, pickup, or nearest-cafe questions.

            Returns:
                Store location records.
            """
            return await tools_service.get_all_store_locations()

        async def find_stores_by_location(
            city: str | None = None,
            state: str | None = None,
            zip_code: str | None = None,
        ) -> dict[str, Any]:
            """Find Cymbal Coffee stores by city, state, or ZIP code.

            Returns:
                Matching store records and named-SQL telemetry.
            """
            result = await tools_service.find_stores_by_location(city=city, state=state, zip_code=zip_code)
            _record_tool_sql_phases(metric_state, result)
            return result

        async def get_store_hours(store_id: int) -> dict[str, Any]:
            """Get business hours for a Cymbal Coffee store.

            Returns:
                Store hours, timezone, and named-SQL telemetry.
            """
            result = await tools_service.get_store_hours(store_id)
            _record_tool_sql_phases(metric_state, result)
            return result

        async def find_nearest_stores(latitude: float, longitude: float, limit: int = 5) -> dict[str, Any]:
            """Find nearest Cymbal Coffee stores from request-scoped browser coordinates.

            Returns:
                Nearest local stores and named-SQL telemetry with coordinates masked.
            """
            result = await tools_service.find_nearest_stores(latitude, longitude, limit)
            _record_tool_sql_phases(metric_state, result)
            return result

        async def find_stores_with_product(
            product_query: str,
            latitude: float | None = None,
            longitude: float | None = None,
        ) -> dict[str, Any]:
            """Find stores with availability for a Cymbal Coffee product.

            Returns:
                Store-level availability and named-SQL telemetry.
            """
            result = await tools_service.find_stores_with_product(product_query, latitude, longitude)
            _record_tool_sql_phases(metric_state, result)
            return result

        return [
            search_products_by_vector,
            get_product_details,
            get_all_store_locations,
            find_stores_by_location,
            get_store_hours,
            find_nearest_stores,
            find_stores_with_product,
        ]

    def _build_workflow(self, instruction: str, temperature: float, tools: list[ToolUnion]) -> Any:
        agent = LlmAgent(
            name="CoffeeAssistant",
            model=get_settings().vertex_ai.CHAT_MODEL,
            instruction=instruction,
            tools=tools,
            generate_content_config=types.GenerateContentConfig(temperature=temperature),
            before_agent_callback=credential_guard_callback,
        )
        return make_workflow(self._classifier, agent)

    async def _get_or_create_session(self, user_id: str, session_id: str | None) -> Any:
        """Fetch an existing ADK session or create one for the request.

        Returns:
            ADK session bound to the user/session identifiers.
        """
        session = (
            await self._session_service.get_session(app_name=_APP_NAME, user_id=user_id, session_id=session_id)
            if session_id
            else None
        )
        if not session:
            session = await self._session_service.create_session(
                app_name=_APP_NAME, user_id=user_id, session_id=session_id
            )
        return session

    async def get_history(self, user_id: str, session_id: str) -> list[ChatMessage]:
        """Return displayable chat history for the current ADK session."""
        session = await self._session_service.get_session(app_name=_APP_NAME, user_id=user_id, session_id=session_id)
        if not session:
            return []

        state = getattr(session, "state", None) or {}
        if isinstance(state, dict):
            persisted = _coerce_history_messages(state.get(_DISPLAY_HISTORY_STATE_KEY))
            if persisted:
                return persisted
        return _event_history_messages(getattr(session, "events", []))

    async def clear_session(self, user_id: str, session_id: str) -> None:
        """Delete the current ADK session and its event history."""
        await self._session_service.delete_session(app_name=_APP_NAME, user_id=user_id, session_id=session_id)

    async def _append_display_history(
        self,
        *,
        user_id: str,
        session_id: str,
        query: str,
        answer: str,
        intent_detected: str | None = None,
    ) -> None:
        session = await self._session_service.get_session(app_name=_APP_NAME, user_id=user_id, session_id=session_id)
        if not session:
            return

        state = dict(getattr(session, "state", None) or {})
        if intent_detected:
            state["intent"] = intent_detected
        history = [
            *[
                {"source": message.source, "message": message.message}
                for message in _coerce_history_messages(state.get(_DISPLAY_HISTORY_STATE_KEY))
            ],
            {"source": "human", "message": query},
            {"source": "ai", "message": answer},
        ]
        state[_DISPLAY_HISTORY_STATE_KEY] = history[-40:]
        update_state = getattr(getattr(self._session_service, "store", None), "update_session_state", None)
        if callable(update_state):
            result = update_state(session_id, state)
            if isawaitable(result):
                await result

    async def _classify_intent(self, query: str) -> str:
        intent_result = self._classifier.classify(query)
        intent_label = await intent_result if isawaitable(intent_result) else intent_result
        return intent_label.value if isinstance(intent_label, IntentLabel) else str(intent_label)

    async def _cached_response_event(
        self,
        *,
        start: float,
        query: str,
        user_id: str,
        session: Any,
        cached_response: dict[str, Any],
        response_cache_phase: dict[str, Any],
        location_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        elapsed_ms = (time.time() - start) * 1000
        cached_metrics = dict(cached_response.get("search_metrics") or {})
        cached_metrics["total_ms"] = round(elapsed_ms)
        answer = str(cached_response.get("answer", ""))
        sql_phases = _coerce_sql_phases(cached_response.get("sql_phases"))
        intent_detected = _effective_intent(
            str(cached_response.get("intent_detected", "GENERAL_CONVERSATION")),
            cached_metrics,
            sql_phases,
        )
        if answer:
            await self._append_display_history(
                user_id=user_id,
                session_id=session.id,
                query=query,
                answer=answer,
                intent_detected=intent_detected,
            )
        return {
            "type": "final",
            "answer": answer,
            "session_id": session.id,
            "response_time_ms": elapsed_ms,
            "intent_detected": intent_detected,
            "search_metrics": cached_metrics,
            "from_cache": True,
            "embedding_cache_hit": bool(cached_response.get("embedding_cache_hit")),
            "sql_phases": [response_cache_phase, *sql_phases],
            "store_results": _coerce_dict_rows(cached_response.get("store_results")),
            "inventory_results": _coerce_dict_rows(cached_response.get("inventory_results")),
            "map_actions": _coerce_dict_rows(cached_response.get("map_actions")),
            "location_context": _safe_location_context(location_context),
        }

    async def _product_rag_event(
        self,
        *,
        start: float,
        query: str,
        user_id: str,
        session: Any,
        cache_key: str | None,
        response_cache_phase: dict[str, Any] | None,
        tools_service: AgentToolsService,
        location_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metric_state: dict[str, Any] = {"search_metrics": {}, "embedding_cache_hit": False, "sql_phases": []}
        answer = await _ground_product_rag_turn(query, metric_state, tools_service)
        elapsed_ms = (time.time() - start) * 1000
        search_metrics = dict(metric_state.get("search_metrics", {}))
        search_metrics["total_ms"] = round(elapsed_ms)
        product_sql_phases = _coerce_sql_phases(metric_state.get("sql_phases"))
        response_data = {
            "answer": answer,
            "intent_detected": _PRODUCT_RAG_INTENT,
            "search_metrics": search_metrics,
            "embedding_cache_hit": bool(metric_state.get("embedding_cache_hit")),
            "sql_phases": product_sql_phases,
            "store_results": [],
            "inventory_results": [],
            "map_actions": [],
        }
        if answer:
            if cache_key:
                await tools_service.set_cached_chat_response(cache_key, response_data)
            await self._append_display_history(
                user_id=user_id,
                session_id=session.id,
                query=query,
                answer=answer,
                intent_detected=_PRODUCT_RAG_INTENT,
            )
        return {
            "type": "final",
            "answer": answer,
            "session_id": session.id,
            "response_time_ms": elapsed_ms,
            "intent_detected": _PRODUCT_RAG_INTENT,
            "search_metrics": search_metrics,
            "from_cache": False,
            "embedding_cache_hit": bool(metric_state.get("embedding_cache_hit")),
            "sql_phases": ([response_cache_phase] if response_cache_phase else []) + product_sql_phases,
            **_default_route_fields(location_context),
        }

    async def _store_location_event(
        self,
        *,
        start: float,
        query: str,
        user_id: str,
        session: Any,
        tools_service: AgentToolsService,
        location_context: dict[str, Any] | None,
        response_cache_phase: dict[str, Any] | None,
    ) -> dict[str, Any]:
        coordinates = _request_coordinates(location_context)
        if coordinates:
            result = await tools_service.find_nearest_stores(coordinates[0], coordinates[1], 5)
        else:
            filters = _extract_location_filters(query, location_context)
            result = await tools_service.find_stores_by_location(
                city=filters["city"],
                state=filters["state"],
                zip_code=filters["zip_code"],
            )

        stores = _coerce_dict_rows(result.get("stores"))
        sql_phases = _coerce_sql_phases(result.get("sql_phases"))
        elapsed_ms = (time.time() - start) * 1000
        answer = _format_store_location_answer(stores)
        await self._append_display_history(
            user_id=user_id,
            session_id=session.id,
            query=query,
            answer=answer,
            intent_detected=_STORE_LOCATION_INTENT,
        )
        return {
            "type": "final",
            "answer": answer,
            "session_id": session.id,
            "response_time_ms": elapsed_ms,
            "intent_detected": _STORE_LOCATION_INTENT,
            "search_metrics": {"total_ms": round(elapsed_ms), "results_count": len(stores)},
            "from_cache": False,
            "embedding_cache_hit": False,
            "sql_phases": ([response_cache_phase] if response_cache_phase else []) + sql_phases,
            "store_results": stores,
            "inventory_results": [],
            "map_actions": _build_map_actions(stores),
            "location_context": _safe_location_context(location_context),
        }

    async def _product_availability_event(
        self,
        *,
        start: float,
        query: str,
        user_id: str,
        session: Any,
        tools_service: AgentToolsService,
        location_context: dict[str, Any] | None,
        response_cache_phase: dict[str, Any] | None,
    ) -> dict[str, Any]:
        coordinates = _request_coordinates(location_context)
        product_query = _extract_product_query(query)
        if coordinates:
            result = await tools_service.find_stores_with_product(product_query, coordinates[0], coordinates[1])
        else:
            result = await tools_service.find_stores_with_product(product_query)

        inventory = _coerce_dict_rows(result.get("availability"))
        sql_phases = _coerce_sql_phases(result.get("sql_phases"))
        elapsed_ms = (time.time() - start) * 1000
        answer = _format_availability_answer(inventory)
        await self._append_display_history(
            user_id=user_id,
            session_id=session.id,
            query=query,
            answer=answer,
            intent_detected=_PRODUCT_AVAILABILITY_INTENT,
        )
        return {
            "type": "final",
            "answer": answer,
            "session_id": session.id,
            "response_time_ms": elapsed_ms,
            "intent_detected": _PRODUCT_AVAILABILITY_INTENT,
            "search_metrics": {
                "total_ms": round(elapsed_ms),
                "results_count": len(inventory),
                "product_query": product_query,
            },
            "from_cache": False,
            "embedding_cache_hit": False,
            "sql_phases": ([response_cache_phase] if response_cache_phase else []) + sql_phases,
            "store_results": [],
            "inventory_results": inventory,
            "map_actions": _build_map_actions(inventory),
            "location_context": _safe_location_context(location_context),
        }

    async def _unsupported_order_status_event(
        self,
        *,
        start: float,
        query: str,
        user_id: str,
        session: Any,
        location_context: dict[str, Any] | None,
        response_cache_phase: dict[str, Any] | None,
    ) -> dict[str, Any]:
        elapsed_ms = (time.time() - start) * 1000
        answer = (
            "This demo does not include order tracking yet. I can help with menu recommendations, "
            "store locations, and product availability."
        )
        await self._append_display_history(
            user_id=user_id,
            session_id=session.id,
            query=query,
            answer=answer,
            intent_detected=_ORDER_STATUS_INTENT,
        )
        return {
            "type": "final",
            "answer": answer,
            "session_id": session.id,
            "response_time_ms": elapsed_ms,
            "intent_detected": _ORDER_STATUS_INTENT,
            "search_metrics": {"total_ms": round(elapsed_ms)},
            "from_cache": False,
            "embedding_cache_hit": False,
            "sql_phases": [response_cache_phase] if response_cache_phase else [],
            **_default_route_fields(location_context),
        }

    async def _response_cache_lookup(
        self,
        *,
        query: str,
        persona: str,
        tools_service: AgentToolsService,
        location_context: dict[str, Any] | None,
    ) -> tuple[str | None, dict[str, Any] | None, dict[str, Any] | None]:
        if _has_browser_coordinates(location_context):
            return None, None, None

        cache_key = tools_service.make_response_cache_key(query, persona)
        cache_start = time.time()
        cached_response = await tools_service.get_cached_chat_response(cache_key)
        response_cache_phase = _response_cache_phase(
            cache_key,
            hit=bool(cached_response),
            runtime_ms=(time.time() - cache_start) * 1000,
        )
        return cache_key, response_cache_phase, cached_response

    async def _deterministic_route_event(
        self,
        *,
        intent_detected: str,
        start: float,
        query: str,
        user_id: str,
        session: Any,
        tools_service: AgentToolsService,
        location_context: dict[str, Any] | None,
        cache_key: str | None,
        response_cache_phase: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if intent_detected == _PRODUCT_RAG_INTENT:
            return await self._product_rag_event(
                start=start,
                query=query,
                user_id=user_id,
                session=session,
                cache_key=cache_key,
                response_cache_phase=response_cache_phase,
                tools_service=tools_service,
                location_context=location_context,
            )
        if intent_detected == _STORE_LOCATION_INTENT:
            return await self._store_location_event(
                start=start,
                query=query,
                user_id=user_id,
                session=session,
                tools_service=tools_service,
                location_context=location_context,
                response_cache_phase=response_cache_phase,
            )
        if intent_detected == _PRODUCT_AVAILABILITY_INTENT:
            return await self._product_availability_event(
                start=start,
                query=query,
                user_id=user_id,
                session=session,
                tools_service=tools_service,
                location_context=location_context,
                response_cache_phase=response_cache_phase,
            )
        if intent_detected == _ORDER_STATUS_INTENT:
            return await self._unsupported_order_status_event(
                start=start,
                query=query,
                user_id=user_id,
                session=session,
                location_context=location_context,
                response_cache_phase=response_cache_phase,
            )
        return None

    async def stream_request(  # noqa: PLR0914, PLR0915
        self,
        query: str,
        user_id: str,
        session_id: str | None,
        persona: str,
        tools_service: AgentToolsService,
        location_context: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat turn as ADK produces partial events.

        Yields:
            Delta events followed by one final event with the complete reply payload.

        Raises:
            AIServiceUnconfigured: If configured credentials are missing or invalid.
            ClientError: If the Gemini client fails for a non-credential reason.
            ValueError: If ADK raises a non-credential validation error.
        """
        start = time.time()
        _ensure_vertex_ai_backend_configured()

        session = await self._get_or_create_session(user_id, session_id)

        cache_key, response_cache_phase, cached_response = await self._response_cache_lookup(
            query=query,
            persona=persona,
            tools_service=tools_service,
            location_context=location_context,
        )
        if cached_response and response_cache_phase:
            yield await self._cached_response_event(
                start=start,
                query=query,
                user_id=user_id,
                session=session,
                cached_response=cached_response,
                response_cache_phase=response_cache_phase,
                location_context=location_context,
            )
            return

        intent_detected = await self._classify_intent(query)
        route_event = await self._deterministic_route_event(
            intent_detected=intent_detected,
            start=start,
            query=query,
            user_id=user_id,
            session=session,
            tools_service=tools_service,
            location_context=location_context,
            cache_key=cache_key,
            response_cache_phase=response_cache_phase,
        )
        if route_event:
            yield route_event
            return

        instruction = self._persona_manager.get_system_prompt(persona, BASE_SYSTEM_INSTRUCTION)
        temperature = self._persona_manager.get_temperature(persona)

        metric_state: dict[str, Any] = {"search_metrics": {}, "embedding_cache_hit": False, "sql_phases": []}
        tools = self._make_tool_factories(tools_service, metric_state)
        workflow = self._build_workflow(instruction, temperature, tools)

        runner = Runner(node=workflow, app_name=_APP_NAME, session_service=self._session_service)
        content = types.Content(role="user", parts=[types.Part(text=query)])
        run_config = RunConfig(streaming_mode=StreamingMode.SSE)
        events = runner.run_async(user_id=user_id, session_id=session.id, new_message=content, run_config=run_config)

        answer_parts: list[str] = []
        partial_answer_parts: list[str] = []
        workflow_output: dict[str, Any] = {}
        try:
            async for event in events:
                if isinstance(event.output, dict) and "intent" in event.output:
                    workflow_output.update(event.output)
                text = _event_content_text(event)
                if not text:
                    continue
                if event.partial:
                    partial_answer_parts.append(text)
                    yield {"type": "delta", "text": text}
                else:
                    answer_parts.append(text)
        except (genai_errors.ClientError, ValueError) as exc:
            if _is_credential_error(exc):
                raise AIServiceUnconfigured(_UNCONFIGURED_MESSAGE) from exc
            raise

        answer = str(workflow_output.get("answer") or "".join(answer_parts) or "".join(partial_answer_parts))
        elapsed_ms = (time.time() - start) * 1000
        search_metrics = dict(metric_state.get("search_metrics", {}))
        search_metrics["total_ms"] = round(elapsed_ms)
        product_sql_phases = _coerce_sql_phases(metric_state.get("sql_phases"))
        intent_detected = _effective_intent(
            str(workflow_output.get("intent") or intent_detected or "GENERAL_CONVERSATION"),
            search_metrics,
            product_sql_phases,
        )
        if intent_detected == _PRODUCT_RAG_INTENT:
            answer = await _ground_product_rag_turn(query, metric_state, tools_service)
            elapsed_ms = (time.time() - start) * 1000
            search_metrics = dict(metric_state.get("search_metrics", {}))
            search_metrics["total_ms"] = round(elapsed_ms)
            product_sql_phases = _coerce_sql_phases(metric_state.get("sql_phases"))
        sql_phases = ([response_cache_phase] if response_cache_phase else []) + product_sql_phases

        response_data = {
            "answer": answer,
            "intent_detected": intent_detected,
            "search_metrics": search_metrics,
            "embedding_cache_hit": bool(metric_state.get("embedding_cache_hit")),
            "sql_phases": product_sql_phases,
            "store_results": [],
            "inventory_results": [],
            "map_actions": [],
        }
        if answer:
            if cache_key:
                await tools_service.set_cached_chat_response(cache_key, response_data)
            await self._append_display_history(
                user_id=user_id,
                session_id=session.id,
                query=query,
                answer=answer,
                intent_detected=intent_detected,
            )

        yield {
            "type": "final",
            "answer": answer,
            "session_id": session.id,
            "response_time_ms": elapsed_ms,
            "intent_detected": intent_detected,
            "search_metrics": search_metrics,
            "from_cache": False,
            "embedding_cache_hit": bool(metric_state.get("embedding_cache_hit")),
            "sql_phases": sql_phases,
            **_default_route_fields(location_context),
        }

    async def process_request(
        self,
        query: str,
        user_id: str,
        session_id: str | None,
        persona: str,
        tools_service: AgentToolsService,
        location_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a chat turn to completion.

        Returns:
            Final chat payload used by JSON and non-streaming HTMX callers.
        """
        async for event in self.stream_request(
            query=query,
            user_id=user_id,
            session_id=session_id,
            persona=persona,
            tools_service=tools_service,
            location_context=location_context,
        ):
            if event.get("type") == "final":
                return {key: event[key] for key in _CHAT_RESULT_KEYS}

        return {
            "answer": "",
            "session_id": session_id or "",
            "response_time_ms": 0.0,
            "intent_detected": "GENERAL_CONVERSATION",
            "search_metrics": {},
            "from_cache": False,
            "embedding_cache_hit": False,
            "sql_phases": [],
            **_default_route_fields(location_context),
        }


__all__ = (
    "ADKRunner",
    "AgentToolsService",
    "credential_guard_callback",
)
