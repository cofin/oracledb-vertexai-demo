# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka provider for request-scoped domain services."""

from dishka import Provider, Scope, provide
from google.genai import Client

import app.ioc as _ioc_pkg
from app.domain.ai.runtime import AgentRuntime, AgentStreamService, OracleEventStore, OracleSessionStore, SpecTree
from app.domain.ai.services import AgentOrchestrationService
from app.domain.chat.services import GroundedRouteService, HybridRouteResolver
from app.domain.products.services import (
    InventoryService,
    MapsService,
    OracleVectorSearchService,
    ProductService,
    StoreService,
    VertexAIService,
)
from app.domain.system.services import CacheService, MetricsService, PersonaManager

__all__ = ("DomainServiceProvider",)


class DomainServiceProvider(Provider):
    """REQUEST-scoped domain services."""

    scope = Scope.REQUEST

    product_service = provide(ProductService)
    store_service = provide(StoreService)
    inventory_service = provide(InventoryService)
    cache_service = provide(CacheService)
    metrics_service = provide(MetricsService)
    route_resolver = provide(HybridRouteResolver)

    @provide
    def provide_maps_service(self) -> MapsService:
        """Provide the Google Maps URL builder service."""
        return MapsService()

    @provide
    def provide_agent_stream_service(self) -> AgentStreamService:
        """Provide the SSE AgentStreamService adapter."""
        return AgentStreamService()

    @provide
    def provide_vertex_ai_service(self, client: Client, cache_service: CacheService) -> VertexAIService:
        """Provide VertexAIService configured with embedding and chat model settings."""
        settings = _ioc_pkg.get_settings()
        return VertexAIService(
            client=client,
            model=settings.ai.chat_model,
            embedding_model=settings.ai.embedding_model,
            embedding_dimensions=settings.ai.embedding_dimensions,
            cache_service=cache_service,
        )

    @provide
    def provide_grounded_route_service(
        self, product_service: ProductService, store_service: StoreService, vertex_ai_service: VertexAIService
    ) -> GroundedRouteService:
        """Provide GroundedRouteService for deterministic chat routes."""
        return GroundedRouteService(
            product_service=product_service, store_service=store_service, vertex_ai_service=vertex_ai_service
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
        """Provide AgentOrchestrationService for hybrid chat turns."""
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
        """Provide OracleVectorSearchService combining Vertex AI embeddings with product search."""
        return OracleVectorSearchService(vertex_ai_service=vertex_ai_service, product_service=product_service)
