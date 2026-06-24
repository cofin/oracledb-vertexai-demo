# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka container configuration for Litestar.

Three providers, accelerator-style:
- LitestarPersistenceProvider: APP-scoped Oracle config + REQUEST-scoped driver.
- IntegrationsProvider: APP-scoped external integrations (genai client, ADK store/session/runner).
- DomainServiceProvider: REQUEST-scoped domain services that depend on the per-request driver.

NOTE: Dishka introspects @provide method annotations at runtime; this module must NOT use
`from __future__ import annotations`.
"""

import sys
from collections.abc import AsyncIterator

from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from google.genai import Client
from sqlspec.adapters.oracledb import OracleAsyncConfig, OracleAsyncDriver
from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore
from sqlspec.extensions.adk import SQLSpecSessionService

from app.domain.chat.services.adk import ADKRunner, AgentToolsService
from app.domain.chat.services.classifier import FlashLiteIntentClassifier
from app.domain.products.services.services import (
    OracleVectorSearchService,
    ProductService,
    StoreService,
    VertexAIService,
)
from app.domain.system.services.services import CacheService, MetricsService, PersonaManager
from app.lib.di import QueryContext, query_id_var
from app.lib.settings import get_settings


class LitestarPersistenceProvider(Provider):
    """Oracle config (APP) + per-request driver (REQUEST)."""

    @provide(scope=Scope.APP)
    def provide_config(self) -> OracleAsyncConfig:
        from app import config

        return config.db

    @provide(scope=Scope.REQUEST)
    async def provide_driver(self) -> AsyncIterator[OracleAsyncDriver]:
        from app import config

        session_context = config.db_manager.provide_session(config.db)
        # Dishka owns async-generator provider cleanup; SQLSpec exposes only an
        # async context manager, so entering it manually avoids yielding inside
        # an async-with block while preserving exception-aware cleanup.
        driver = await session_context.__aenter__()  # noqa: PLC2801
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
    def provide_adk_store(self, config: OracleAsyncConfig) -> OracleAsyncADKStore:
        return OracleAsyncADKStore(config=config)

    @provide(scope=Scope.APP)
    def provide_session_service(self, store: OracleAsyncADKStore) -> SQLSpecSessionService:
        return SQLSpecSessionService(store)

    @provide(scope=Scope.APP)
    def provide_intent_classifier(self, client: Client) -> FlashLiteIntentClassifier:
        return FlashLiteIntentClassifier(client, model=get_settings().ai.intent_model)

    @provide(scope=Scope.APP)
    def provide_persona_manager(self) -> PersonaManager:
        return PersonaManager()

    @provide(scope=Scope.APP)
    def provide_adk_runner(
        self,
        session_service: SQLSpecSessionService,
        classifier: FlashLiteIntentClassifier,
        persona_manager: PersonaManager,
    ) -> ADKRunner:
        return ADKRunner(session_service=session_service, classifier=classifier, persona_manager=persona_manager)


class DomainServiceProvider(Provider):
    """REQUEST-scoped domain services."""

    scope = Scope.REQUEST

    product_service = provide(ProductService)
    store_service = provide(StoreService)
    cache_service = provide(CacheService)
    metrics_service = provide(MetricsService)

    agent_tools_service = provide(AgentToolsService)

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

    @provide
    def provide_query_context(self) -> "QueryContext | None":
        qid = query_id_var.get()
        if not qid:
            return None
        return QueryContext(query_id=qid)


PROVIDERS: tuple[type[Provider], ...] = (LitestarPersistenceProvider, IntegrationsProvider, DomainServiceProvider)


def make_container(*extra_providers: Provider) -> AsyncContainer:
    """Build the Dishka container with the three user providers plus any extras.

    Pass ``LitestarProvider()`` to wire the request scope to Litestar; pass
    nothing for the ``coffee`` CLI.
    """
    return make_async_container(*extra_providers, *(P() for P in PROVIDERS))


__all__ = (
    "PROVIDERS",
    "DomainServiceProvider",
    "IntegrationsProvider",
    "LitestarPersistenceProvider",
    "make_container",
)
