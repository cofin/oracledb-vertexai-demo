# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ADK 2.0 chat runner with closure-bound tools and parallel intent classification."""

from __future__ import annotations

import time
import uuid
from hashlib import sha256
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, cast

import structlog
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import errors as genai_errors
from google.genai import types
from sqlspec.adapters.oracledb import OracleAsyncDriver  # noqa: TC002
from sqlspec.extensions.adk import SQLSpecSessionService  # noqa: TC002

from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services._adk_grounding import (
    _build_map_actions,
    _coerce_dict_rows,
    _default_route_fields,
    _extract_location_filters,
    _extract_product_query,
    _format_availability_answer,
    _format_store_location_answer,
    _get_field,
    _ground_product_rag_turn,
    _has_browser_coordinates,
    _record_product_search_result,
    _request_coordinates,
    _safe_location_context,
)
from app.domain.chat.services._adk_history import (
    _coerce_history_messages,
    _event_content_text,
    _event_history_messages,
)
from app.domain.chat.services._adk_telemetry import (
    _coerce_sql_phases,
    _effective_intent,
    _record_tool_sql_phases,
    _response_cache_phase,
    _sha256_text,
    _similarity_score,
    _sql_phase,
    _summarize_vector,
)
from app.domain.chat.services.classifier import (
    FlashLiteIntentClassifier,
    IntentLabel,
)
from app.domain.chat.services.workflow import make_workflow
from app.domain.products.services import ProductService, StoreService, VertexAIService  # noqa: TC001
from app.domain.system.schemas import SearchMetricsCreate
from app.domain.system.services import BASE_SYSTEM_INSTRUCTION, CacheService, MetricsService, PersonaManager
from app.lib.service import OracleAsyncService
from app.lib.settings import get_settings
from app.utils.serialization import sanitize_for_json

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from google.adk.agents.callback_context import CallbackContext
    from google.adk.agents.llm_agent import ToolUnion

    from app.domain.chat.schemas import ChatMessage

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


async def _collect_workflow_stream(
    events: AsyncIterator[Any],
    *,
    workflow_output: dict[str, Any],
    answer_parts: list[str],
    partial_answer_parts: list[str],
) -> AsyncIterator[dict[str, str]]:
    """Collect ADK workflow output while yielding streaming deltas."""
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


class AgentToolsService(OracleAsyncService):
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
            embedding_purpose="query",
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

        # 1. Try exact match first
        availability = await self.store_service.find_product_availability(product_query, coordinates=coordinates)
        sql_key = "find-product-availability-by-query"
        binds: dict[str, Any] = {"product_query": product_query}

        # 2. If no exact match, try vector search fallback
        if not availability:
            query_embedding = await self.vertex_ai_service.get_text_embedding(
                product_query,
                embedding_purpose="query",
            )
            matches = await self.product_service.search_by_vector(
                query_embedding,
                similarity_threshold=0.6,
                limit=1,
            )
            if matches:
                resolved_product = matches[0]
                availability = await self.store_service.find_stores_with_product(
                    resolved_product.id,
                    latitude=latitude,
                    longitude=longitude,
                )
                sql_key = "find-stores-with-product-inventory"
                binds = {"product_id": resolved_product.id}
                await logger.ainfo(
                    "Resolved product query via vector search",
                    query=product_query,
                    resolved_name=resolved_product.name,
                    similarity=resolved_product.similarity_score,
                )

        if coordinates:
            binds["origin"] = "<REQUEST_COORDINATES>"

        return {
            "availability": sanitize_for_json(availability),
            "results_count": len(availability),
            "sql_phases": [
                _sql_phase(
                    label="Product availability lookup",
                    sql_key=sql_key,
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

    @staticmethod
    def ensure_configured() -> None:
        """Raise AIServiceUnconfigured if Vertex AI credentials are missing."""
        _ensure_vertex_ai_backend_configured()

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

    async def get_history_or_empty(self, user_id: str, session_id: str) -> list[ChatMessage]:
        """Return displayable chat history, or an empty list if loading fails."""
        try:
            return await self.get_history(user_id=user_id, session_id=session_id)
        except Exception as exc:  # noqa: BLE001
            await logger.awarning("Chat history unavailable", error_type=type(exc).__name__)
            return []

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
        last_products: list[str] | None = None,
    ) -> None:
        session = await self._session_service.get_session(app_name=_APP_NAME, user_id=user_id, session_id=session_id)
        if not session:
            return

        state = dict(getattr(session, "state", None) or {})
        if intent_detected:
            state["intent"] = intent_detected
        if last_products is not None:
            state["last_products"] = last_products
        history = [
            *[
                {"source": message.source, "message": message.message}
                for message in _coerce_history_messages(state.get(_DISPLAY_HISTORY_STATE_KEY))
            ],
            {"source": "human", "message": query},
            {"source": "ai", "message": answer},
        ]
        state[_DISPLAY_HISTORY_STATE_KEY] = history[-40:]
        result = self._session_service.store.update_session_state(session_id, state)
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
        cached_metrics = dict(
            cached_response.get("searchMetrics")
            or cached_response.get("search_metrics")
            or {}
        )
        cached_metrics["total_ms"] = round(elapsed_ms)
        answer = str(cached_response.get("answer", ""))
        sql_phases = _coerce_sql_phases(
            cached_response.get("sqlPhases")
            or cached_response.get("sql_phases")
        )
        intent_detected = _effective_intent(
            str(
                cached_response.get("intentDetected")
                or cached_response.get("intent_detected")
                or "GENERAL_CONVERSATION"
            ),
            cached_metrics,
            sql_phases,
        )
        last_products = (
            cached_response.get("lastProducts")
            or cached_response.get("last_products")
        )
        if answer:
            await self._append_display_history(
                user_id=user_id,
                session_id=session.id,
                query=query,
                answer=answer,
                intent_detected=intent_detected,
                last_products=last_products,
            )
        return {
            "type": "final",
            "answer": answer,
            "session_id": session.id,
            "response_time_ms": elapsed_ms,
            "intent_detected": intent_detected,
            "search_metrics": cached_metrics,
            "from_cache": True,
            "embedding_cache_hit": bool(
                cached_response.get("embeddingCacheHit")
                or cached_response.get("embedding_cache_hit")
            ),
            "sql_phases": [response_cache_phase, *sql_phases],
            "store_results": _coerce_dict_rows(
                cached_response.get("storeResults")
                or cached_response.get("store_results")
            ),
            "inventory_results": _coerce_dict_rows(
                cached_response.get("inventoryResults")
                or cached_response.get("inventory_results")
            ),
            "map_actions": _coerce_dict_rows(
                cached_response.get("mapActions")
                or cached_response.get("map_actions")
            ),
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
        products = metric_state.get("rag_products", [])
        last_products = [p["name"] for p in products] if products else None
        response_data = {
            "answer": answer,
            "intent_detected": _PRODUCT_RAG_INTENT,
            "search_metrics": search_metrics,
            "embedding_cache_hit": bool(metric_state.get("embedding_cache_hit")),
            "sql_phases": product_sql_phases,
            "store_results": [],
            "inventory_results": [],
            "map_actions": [],
            "last_products": last_products,
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
                last_products=last_products,
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
        if not product_query:
            state = dict(getattr(session, "state", None) or {})
            last_products = state.get("last_products", [])
            product_query = last_products[0] if last_products else query

        location_hint = (location_context or {}).get("store_name") if location_context else None
        if not location_hint:
            filters = _extract_location_filters(query, location_context)
            location_hint = " ".join(str(filters[k]) for k in ("city", "state", "zip_code") if filters[k]) or query

        target_store = await tools_service.store_service.resolve_store(
            location_hint=location_hint,
            coordinates=coordinates,
        )

        if coordinates:
            result = await tools_service.find_stores_with_product(product_query, coordinates[0], coordinates[1])
        else:
            result = await tools_service.find_stores_with_product(product_query)

        inventory = _coerce_dict_rows(result.get("availability"))
        sql_phases = _coerce_sql_phases(result.get("sql_phases"))
        elapsed_ms = (time.time() - start) * 1000

        target_row = None
        alternatives = []

        if target_store:
            for row in inventory:
                if _get_field(row, "store_id") == target_store.id:
                    target_row = row
                else:
                    alternatives.append(row)
            if not target_row:
                alternatives = inventory
        else:
            alternatives = inventory

        answer = _format_availability_answer(
            target=target_row,
            alternatives=alternatives,
            target_store_name=target_store.name if target_store else None,
        )
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

    async def stream_request(  # noqa: PLR0914
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
            async for delta in _collect_workflow_stream(
                events,
                workflow_output=workflow_output,
                answer_parts=answer_parts,
                partial_answer_parts=partial_answer_parts,
            ):
                yield delta
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
