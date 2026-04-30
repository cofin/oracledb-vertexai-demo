# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ADK 2.0 chat runner with closure-bound tools and parallel intent classification."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any, cast

import structlog
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.genai import errors as genai_errors
from google.genai import types
from sqlspec.adapters.oracledb import OracleAsyncDriver

from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services.workflow import make_workflow
from app.domain.products.services import ProductService, StoreService, VertexAIService
from app.domain.system.services import BASE_SYSTEM_INSTRUCTION, MetricsService, PersonaManager
from app.lib.service import SQLSpecAsyncService
from app.lib.settings import get_settings
from app.utils.serialization import sanitize_for_json

if TYPE_CHECKING:
    from collections.abc import Callable

    from google.adk.agents.callback_context import CallbackContext
    from sqlspec.extensions.adk import SQLSpecSessionService

    from app.domain.chat.services.classifier import FlashLiteIntentClassifier

logger = structlog.get_logger()

_APP_NAME = "coffee_assistant"
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
    ) -> None:
        super().__init__(driver)
        self.product_service = product_service
        self.metrics_service = metrics_service
        self.vertex_ai_service = vertex_ai_service
        self.store_service = store_service

    async def search_products_by_vector(
        self, query: str, limit: int = 5, similarity_threshold: float = 0.7
    ) -> dict[str, Any]:
        embedding, cache_hit = await self.vertex_ai_service.get_text_embedding(
            query, return_cache_status=True
        )
        products = await self.product_service.search_by_vector(embedding, similarity_threshold, limit)
        return {"products": products, "embedding_cache_hit": cache_hit, "results_count": len(products)}

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


def credential_guard_callback(callback_context: CallbackContext) -> types.Content | None:
    """Short-circuit the agent with a 503 message when credentials are missing."""
    del callback_context
    settings = get_settings()
    if settings.vertex_ai.PROJECT_ID or settings.vertex_ai.API_KEY:
        return None
    return types.Content(
        role="model",
        parts=[
            types.Part(
                text="AI service is not configured. Set GOOGLE_API_KEY or VERTEX_AI_API_KEY in your .env file."
            )
        ],
    )


def _is_credential_error(exc: BaseException) -> bool:
    if isinstance(exc, genai_errors.ClientError):
        return True
    text = str(exc).lower()
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

    def _make_tool_factories(
        self, tools_service: AgentToolsService, metric_state: dict[str, Any]
    ) -> list[Callable[..., Any]]:
        async def search_products_by_vector(
            query: str, limit: int = 5, similarity_threshold: float = 0.7
        ) -> dict[str, Any]:
            result = await tools_service.search_products_by_vector(query, limit, similarity_threshold)
            metric_state["embedding_cache_hit"] = bool(result.get("embedding_cache_hit", False))
            metric_state.setdefault("search_metrics", {})["results_count"] = result.get("results_count", 0)
            return result

        async def get_product_details(product_id: str) -> dict[str, Any]:
            return await tools_service.get_product_details(product_id)

        return [search_products_by_vector, get_product_details]

    def _build_workflow(
        self, instruction: str, temperature: float, tools: list[Callable[..., Any]]
    ) -> Any:
        agent = LlmAgent(
            name="CoffeeAssistant",
            model=get_settings().vertex_ai.CHAT_MODEL,
            instruction=instruction,
            tools=tools,
            generate_content_config=types.GenerateContentConfig(temperature=temperature),
            before_agent_callback=credential_guard_callback,
        )
        return make_workflow(self._classifier, agent)

    async def process_request(
        self,
        query: str,
        user_id: str,
        session_id: str | None,
        persona: str,
        tools_service: AgentToolsService,
    ) -> dict[str, Any]:
        start = time.time()

        session = (
            await self._session_service.get_session(
                app_name=_APP_NAME, user_id=user_id, session_id=session_id
            )
            if session_id
            else None
        )
        if not session:
            session = await self._session_service.create_session(
                app_name=_APP_NAME, user_id=user_id, session_id=session_id
            )

        instruction = self._persona_manager.get_system_prompt(persona, BASE_SYSTEM_INSTRUCTION)
        temperature = self._persona_manager.get_temperature(persona)

        metric_state: dict[str, Any] = {"search_metrics": {}, "embedding_cache_hit": False}
        tools = self._make_tool_factories(tools_service, metric_state)
        workflow = self._build_workflow(instruction, temperature, tools)

        runner = Runner(node=workflow, app_name=_APP_NAME, session_service=self._session_service)
        content = types.Content(role="user", parts=[types.Part(text=query)])
        events = runner.run_async(user_id=user_id, session_id=session.id, new_message=content)

        answer_parts: list[str] = []
        try:
            async for event in events:
                if event.content and event.content.parts:
                    answer_parts.extend(
                        str(p.text) for p in event.content.parts if getattr(p, "text", None)
                    )
        except (genai_errors.ClientError, ValueError) as exc:
            if _is_credential_error(exc):
                raise AIServiceUnconfigured(
                    "AI service is not configured. Set GOOGLE_API_KEY or VERTEX_AI_API_KEY in your .env file."
                ) from exc
            raise

        intent_detected = "GENERAL_CONVERSATION"
        state = getattr(session, "state", None) or {}
        if isinstance(state, dict):
            intent_detected = str(state.get("intent", intent_detected))

        return {
            "answer": "".join(answer_parts),
            "session_id": session.id,
            "response_time_ms": (time.time() - start) * 1000,
            "intent_detected": intent_detected,
            "search_metrics": metric_state.get("search_metrics", {}),
            "from_cache": False,
            "embedding_cache_hit": bool(metric_state.get("embedding_cache_hit")),
        }


__all__ = (
    "ADKRunner",
    "AgentToolsService",
    "credential_guard_callback",
)
