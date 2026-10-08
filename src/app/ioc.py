# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka container configuration for Litestar.

Three providers:
- LitestarPersistenceProvider: APP-scoped Oracle config + REQUEST-scoped driver.
- IntegrationsProvider: APP-scoped external integrations (genai client, AI runtime, stores).
- DomainServiceProvider: REQUEST-scoped domain services that depend on the per-request driver.

NOTE: Dishka introspects @provide method annotations at runtime; this module must NOT use
`from __future__ import annotations`.
"""

import sys
from collections.abc import AsyncIterator

from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from google.genai import Client
from sqlspec.adapters.oracledb import OracleAsyncConfig, OracleAsyncDriver

from app.domain.ai.runtime import (
    AgentRuntime,
    AgentStreamService,
    GeminiModelClient,
    OracleEventStore,
    OracleSessionStore,
    SpecTree,
)
from app.domain.ai.services import AgentOrchestrationService, get_coffee_spec_tree
from app.domain.chat.services.classifier import FlashLiteIntentClassifier
from app.domain.products.services.services import (
    OracleVectorSearchService,
    ProductService,
    StoreService,
    VertexAIService,
)
from app.domain.system.services.services import CacheService, MetricsService, PersonaManager
from app.lib.settings import get_settings


class LitestarPersistenceProvider(Provider):
    """Oracle config (APP) + per-request driver (REQUEST)."""

    @provide(scope=Scope.APP)
    def provide_config(self) -> OracleAsyncConfig:
        from app import config

        return config.db

    @provide(scope=Scope.REQUEST)
    async def provide_driver(self) -> AsyncIterator[OracleAsyncDriver]:
        """Provide per-request OracleAsyncDriver."""
        from app import config

        session_context = config.db_manager.provide_session(config.db)
        driver = await session_context.__aenter__()
        try:
            yield driver
        except BaseException:
            await session_context.__aexit__(*sys.exc_info())
            raise
        else:
            await session_context.__aexit__(None, None, None)


class IntegrationsProvider(Provider):
    """APP-scoped singletons for external integrations."""

    @provide(scope=Scope.APP)
    def provide_genai_client(self) -> Client:
        settings = get_settings()
        if settings.ai.project_id:
            return Client(vertexai=True, project=settings.ai.project_id, location=settings.ai.location)
        return Client(api_key=settings.ai.api_key)

    @provide(scope=Scope.APP)
    def provide_model_client(self, client: Client) -> GeminiModelClient:
        settings = get_settings()
        return GeminiModelClient(client=client, default_model=settings.ai.chat_model)

    @provide(scope=Scope.APP)
    def provide_agent_runtime(self, model_client: GeminiModelClient) -> AgentRuntime:
        return AgentRuntime(model_client=model_client)

    @provide(scope=Scope.APP)
    def provide_spec_tree(self) -> SpecTree:
        return get_coffee_spec_tree()

    @provide(scope=Scope.APP)
    def provide_intent_classifier(self, client: Client) -> FlashLiteIntentClassifier:
        return FlashLiteIntentClassifier(client, model=get_settings().ai.intent_model)

    @provide(scope=Scope.APP)
    def provide_persona_manager(self) -> PersonaManager:
        return PersonaManager()


class DomainServiceProvider(Provider):
    """REQUEST-scoped domain services."""

    scope = Scope.REQUEST

    product_service = provide(ProductService)
    store_service = provide(StoreService)
    cache_service = provide(CacheService)
    metrics_service = provide(MetricsService)

    session_store = provide(OracleSessionStore)
    event_store = provide(OracleEventStore)

    @provide
    def provide_agent_stream_service(self) -> AgentStreamService:
        return AgentStreamService()

    agent_orchestration_service = provide(AgentOrchestrationService)

    @provide
    def provide_vertex_ai_service(self, client: Client, cache_service: CacheService) -> VertexAIService:
        settings = get_settings()
        return VertexAIService(
            client=client,
            model=settings.ai.chat_model,
            embedding_model=settings.ai.embedding_model,
            embedding_dimensions=settings.ai.embedding_dimensions,
            cache_service=cache_service,
        )

    @provide
    def provide_vector_search_service(
        self, vertex_ai_service: VertexAIService, product_service: ProductService
    ) -> OracleVectorSearchService:
        return OracleVectorSearchService(vertex_ai_service=vertex_ai_service, product_service=product_service)


PROVIDERS: tuple[type[Provider], ...] = (LitestarPersistenceProvider, IntegrationsProvider, DomainServiceProvider)


def make_container(*extra_providers: Provider) -> AsyncContainer:
    """Build the Dishka container with the three user providers plus any extras."""
    return make_async_container(*extra_providers, *(P() for P in PROVIDERS))


__all__ = (
    "PROVIDERS",
    "DomainServiceProvider",
    "IntegrationsProvider",
    "LitestarPersistenceProvider",
    "make_container",
)
