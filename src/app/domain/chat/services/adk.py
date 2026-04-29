# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

import structlog
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.genai import types
from sqlspec.adapters.oracledb import OracleAsyncDriver
from sqlspec.extensions.adk import SQLSpecSessionService

from app.domain.products.services import ProductService, StoreService, VertexAIService
from app.domain.system.services import (
    BASE_SYSTEM_INSTRUCTION,
    CacheService,
    MetricsService,
    PersonaManager,
)
from app.lib.service import SQLSpecAsyncService
from app.lib.settings import get_settings
from app.utils.serialization import sanitize_for_json

logger = structlog.get_logger()


class AgentToolsService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Business logic for ADK tools."""

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
        embedding, cache_hit = await self.vertex_ai_service.get_text_embedding(query, return_cache_status=True)
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


async def search_products_by_vector(
    query: str, limit: int = 5, similarity_threshold: float = 0.7
) -> dict[str, Any]:
    from app.lib.di import request_container_var

    async with _resolve_request_container(request_container_var.get()) as container:
        service = await container.get(AgentToolsService)
        return cast("dict[str, Any]", await service.search_products_by_vector(query, limit, similarity_threshold))


async def get_product_details(product_id: str) -> dict[str, Any]:
    from app.lib.di import request_container_var

    async with _resolve_request_container(request_container_var.get()) as container:
        service = await container.get(AgentToolsService)
        return cast("dict[str, Any]", await service.get_product_details(product_id))


@asynccontextmanager
async def _resolve_request_container(current: Any) -> AsyncGenerator[Any, None]:
    if current:
        yield current
    else:
        from dishka import Scope

        from app.ioc import make_litestar_container

        container = make_litestar_container()
        async with container(scope=Scope.REQUEST) as scoped:
            yield scoped


ALL_TOOLS: list[Any] = [search_products_by_vector, get_product_details]


class ADKRunner:
    """Runner for the ADK agent."""

    def __init__(self, session_service: SQLSpecSessionService) -> None:
        self.session_service = session_service
        agent = LlmAgent(
            name="CoffeeAssistant",
            instruction=BASE_SYSTEM_INSTRUCTION,
            model=get_settings().vertex_ai.CHAT_MODEL,
            tools=ALL_TOOLS,
        )
        self._runner = Runner(agent=agent, app_name="coffee_assistant", session_service=session_service)

    async def process_request(
        self,
        query: str,
        user_id: str = "default",
        session_id: str | None = None,
        persona: str = "enthusiast",
        cache_service: CacheService | None = None,
    ) -> dict[str, Any]:
        start_time = time.time()
        session = (
            await self.session_service.get_session(
                app_name="coffee_assistant", user_id=user_id, session_id=session_id
            )
            if session_id
            else None
        )
        if not session:
            session = await self.session_service.create_session(
                app_name="coffee_assistant", user_id=user_id, session_id=session_id
            )

        persona_instruction = PersonaManager.get_system_prompt(persona, BASE_SYSTEM_INSTRUCTION)
        content = types.Content(
            role="user",
            parts=[types.Part(text=f"[System Context: {persona_instruction}]\n\nUser Query: {query}")],
        )

        events = self._runner.run_async(user_id=user_id, session_id=session.id, new_message=content)

        all_text = []
        async for event in events:
            if event.content and event.content.parts:
                all_text.extend(
                    [str(p.text) for p in event.content.parts if hasattr(p, "text") and p.text is not None]
                )

        return {
            "answer": "".join(all_text),
            "session_id": session.id,
            "response_time_ms": (time.time() - start_time) * 1000,
        }
