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
from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services import GroundedRouteService, HybridRouteResolver
from app.domain.products.services.services import (
    OracleVectorSearchService,
    ProductService,
    StoreService,
    VertexAIService,
)
from app.domain.system.services.services import CacheService, MetricsService, PersonaManager
from app.lib.settings import get_settings

_PLACEHOLDER_VALUES = frozenset({"", "demo-project", "your-project-id", "placeholder", "your-api-key"})


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
        """Provide a configured Google GenAI client or raise 503 AIServiceUnconfigured."""
        settings = get_settings()
        project_id = (settings.ai.project_id or "").strip()
        api_key = (settings.ai.api_key or "").strip()
        if project_id and project_id.lower() not in _PLACEHOLDER_VALUES:
            return Client(vertexai=True, project=project_id, location=settings.ai.location)
        if api_key and api_key.lower() not in _PLACEHOLDER_VALUES:
            return Client(api_key=api_key)
        msg = "Vertex AI or Google GenAI credentials are not configured."
        raise AIServiceUnconfigured(msg)

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
    def provide_persona_manager(self) -> PersonaManager:
        return PersonaManager()

    @provide(scope=Scope.APP)
    def provide_session_store(self) -> OracleSessionStore:
        return OracleSessionStore()

    @provide(scope=Scope.APP)
    def provide_event_store(self) -> OracleEventStore:
        return OracleEventStore()


class DomainServiceProvider(Provider):
    """REQUEST-scoped domain services."""

    scope = Scope.REQUEST

    product_service = provide(ProductService)
    store_service = provide(StoreService)
    cache_service = provide(CacheService)
    metrics_service = provide(MetricsService)
    route_resolver = provide(HybridRouteResolver)

    @provide
    def provide_agent_stream_service(self) -> AgentStreamService:
        return AgentStreamService()

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
    def provide_grounded_route_service(
        self,
        product_service: ProductService,
        store_service: StoreService,
        vertex_ai_service: VertexAIService,
    ) -> GroundedRouteService:
        return GroundedRouteService(
            product_service=product_service,
            store_service=store_service,
            vertex_ai_service=vertex_ai_service,
        )

    @provide
    def provide_agent_orchestration_service(
        self,
        runtime: AgentRuntime,
        stream_service: AgentStreamService,
        spec_tree: SpecTree,
        session_store: OracleSessionStore,
        event_store: OracleEventStore,
        route_resolver: HybridRouteResolver,
        grounded_service: GroundedRouteService,
        product_service: ProductService,
        store_service: StoreService,
        vertex_ai_service: VertexAIService,
        cache_service: CacheService,
        metrics_service: MetricsService,
        persona_manager: PersonaManager,
    ) -> AgentOrchestrationService:
        return AgentOrchestrationService(
            runtime=runtime,
            stream_service=stream_service,
            spec_tree=spec_tree,
            session_store=session_store,
            event_store=event_store,
            route_resolver=route_resolver,
            grounded_service=grounded_service,
            product_service=product_service,
            store_service=store_service,
            vertex_ai_service=vertex_ai_service,
            cache_service=cache_service,
            metrics_service=metrics_service,
            persona_manager=persona_manager,
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
