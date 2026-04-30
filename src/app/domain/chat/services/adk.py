# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ADK 2.0 chat runner with closure-bound tools and parallel intent classification."""

from __future__ import annotations

import time
import uuid
from hashlib import sha256
from typing import TYPE_CHECKING, Any, cast

import structlog
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import errors as genai_errors
from google.genai import types
from sqlspec.adapters.oracledb import OracleAsyncDriver
from sqlspec.extensions.adk import SQLSpecSessionService  # noqa: TC002

from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services.classifier import FlashLiteIntentClassifier  # noqa: TC001
from app.domain.chat.services.workflow import make_workflow
from app.domain.products.services import ProductService, StoreService, VertexAIService  # noqa: TC001
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
_CHAT_RESULT_KEYS: tuple[str, ...] = (
    "answer",
    "session_id",
    "response_time_ms",
    "intent_detected",
    "search_metrics",
    "from_cache",
    "embedding_cache_hit",
)


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
        embedding, cache_hit = await self.vertex_ai_service.get_text_embedding(query, return_cache_status=True)
        products = await self.product_service.search_by_vector(embedding, similarity_threshold, limit)
        return {
            "products": sanitize_for_json(products),
            "embedding_cache_hit": cache_hit,
            "results_count": len(products),
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

    def make_response_cache_key(self, query: str, persona: str) -> str:
        normalized = " ".join(query.casefold().split())
        model = self.vertex_ai_service.model
        digest = sha256(f"{model}:{persona}:{normalized}".encode()).hexdigest()
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
                Matching products and cache/search metadata.
            """
            result = await tools_service.search_products_by_vector(query, limit, similarity_threshold)
            metric_state["embedding_cache_hit"] = bool(result.get("embedding_cache_hit", False))
            products_found = int(result.get("results_count") or len(result.get("products") or []))
            search_metrics = metric_state.setdefault("search_metrics", {})
            search_metrics["results_count"] = products_found
            search_metrics["products_found"] = products_found
            return result

        async def get_product_details(product_id: str) -> dict[str, Any]:
            """Get exact details for a Cymbal Coffee product by id or name.

            Returns:
                Product details, or an error object when no product matches.
            """
            return await tools_service.get_product_details(product_id)

        async def get_all_store_locations() -> list[dict[str, Any]]:
            """List Cymbal Coffee store locations for address, hours, pickup, or nearest-cafe questions.

            Returns:
                Store location records.
            """
            return await tools_service.get_all_store_locations()

        return [search_products_by_vector, get_product_details, get_all_store_locations]

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

    async def stream_request(  # noqa: PLR0914, PLR0915
        self,
        query: str,
        user_id: str,
        session_id: str | None,
        persona: str,
        tools_service: AgentToolsService,
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
        if not _has_vertex_ai_backend_config():
            raise AIServiceUnconfigured(_UNCONFIGURED_MESSAGE)

        session = await self._get_or_create_session(user_id, session_id)

        cache_key = tools_service.make_response_cache_key(query, persona)
        cached_response = await tools_service.get_cached_chat_response(cache_key)
        if cached_response:
            elapsed_ms = (time.time() - start) * 1000
            cached_metrics = dict(cached_response.get("search_metrics") or {})
            cached_metrics["total_ms"] = round(elapsed_ms)
            yield {
                "type": "final",
                "answer": str(cached_response.get("answer", "")),
                "session_id": session.id,
                "response_time_ms": elapsed_ms,
                "intent_detected": str(cached_response.get("intent_detected", "GENERAL_CONVERSATION")),
                "search_metrics": cached_metrics,
                "from_cache": True,
                "embedding_cache_hit": bool(cached_response.get("embedding_cache_hit", False)),
            }
            return

        instruction = self._persona_manager.get_system_prompt(persona, BASE_SYSTEM_INSTRUCTION)
        temperature = self._persona_manager.get_temperature(persona)

        metric_state: dict[str, Any] = {"search_metrics": {}, "embedding_cache_hit": False}
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

        intent_detected = str(workflow_output.get("intent") or "GENERAL_CONVERSATION")
        state = getattr(session, "state", None) or {}
        if isinstance(state, dict):
            intent_detected = str(state.get("intent") or intent_detected)

        answer = str(workflow_output.get("answer") or "".join(answer_parts) or "".join(partial_answer_parts))
        elapsed_ms = (time.time() - start) * 1000
        search_metrics = dict(metric_state.get("search_metrics", {}))
        search_metrics["total_ms"] = round(elapsed_ms)

        response_data = {
            "answer": answer,
            "intent_detected": intent_detected,
            "search_metrics": search_metrics,
            "embedding_cache_hit": bool(metric_state.get("embedding_cache_hit")),
        }
        if answer:
            await tools_service.set_cached_chat_response(cache_key, response_data)

        yield {
            "type": "final",
            "answer": answer,
            "session_id": session.id,
            "response_time_ms": elapsed_ms,
            "intent_detected": intent_detected,
            "search_metrics": search_metrics,
            "from_cache": False,
            "embedding_cache_hit": bool(metric_state.get("embedding_cache_hit")),
        }

    async def process_request(
        self,
        query: str,
        user_id: str,
        session_id: str | None,
        persona: str,
        tools_service: AgentToolsService,
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
        }


__all__ = (
    "ADKRunner",
    "AgentToolsService",
    "credential_guard_callback",
)
