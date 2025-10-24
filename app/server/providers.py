"""Dishka DI providers for the application.

This module provides clean dependency injection using Dishka, replacing the
previous service locator pattern. It defines three main providers:

1. SQLSpecProvider - Database infrastructure (APP + REQUEST scopes)
2. CoreServiceProvider - Business services (REQUEST scope, VertexAI in APP scope)
3. ADKProvider - ADK-specific setup (REQUEST scope)

The providers handle automatic dependency resolution and proper lifecycle
management for all services.
"""

from collections.abc import AsyncIterable
from contextvars import ContextVar

from dishka import AsyncContainer, Provider, Scope, provide
from sqlspec.adapters.oracledb import OracleAsyncConfig
from sqlspec.base import SQLSpec
from sqlspec.driver import AsyncDriverAdapterBase

from app.config import db, db_manager
from app.lib.di import QueryContext, query_id_var

# Import service types for proper type registration (aliased to avoid conflicts)
from app.services import (
    CacheService,
    ExemplarService,
    MetricsService,
    OracleVectorSearchService,
    ProductService,
    VertexAIService,
)
from app.services._adk import ADKRunner, AgentToolsService
from app.services._intent import IntentService
from app.services._store import StoreService

# Context variable for request container access in ADK tools
_request_container: ContextVar[AsyncContainer | None] = ContextVar("_request_container", default=None)


def get_request_container() -> AsyncContainer:
    """Get the current request-scoped Dishka container.

    This function is used by ADK tool functions to access the DI container
    and resolve services, since ADK doesn't support dependency injection
    in tool function signatures.

    Returns:
        The active request container

    Raises:
        RuntimeError: If no active request container exists
    """
    container = _request_container.get()
    if container is None:
        msg = "No active Dishka request container. Ensure container middleware is running."
        raise RuntimeError(msg)
    return container


def set_request_container(container: AsyncContainer) -> None:
    """Set the current request-scoped container.

    This is called by middleware to make the container available to
    ADK tool functions via context variables.

    Args:
        container: The request-scoped container to set
    """
    _request_container.set(container)


class SQLSpecProvider(Provider):
    """Provides SQLSpec database sessions with proper lifecycle.

    This provider handles the SQLSpec infrastructure:
    - SQLSpec manager (singleton, APP scope)
    - Database configuration (singleton, APP scope)
    - Database sessions (per-request, REQUEST scope)

    The session provider wraps SQLSpec's `provide_session()` context manager
    for automatic connection pooling and cleanup.
    """

    @provide(scope=Scope.APP)
    def get_sqlspec_manager(self) -> SQLSpec:
        """Provide SQLSpec manager singleton.

        The manager handles connection pooling and SQL file loading.
        Created once at application startup.
        """

        return db_manager

    @provide(scope=Scope.APP)
    def get_database_config(self) -> OracleAsyncConfig:
        """Provide database configuration singleton.

        Returns the database configuration from app.config.
        Created once at application startup.
        """

        return db

    @provide(scope=Scope.REQUEST)
    async def get_db_session(
        self,
        manager: SQLSpec,
        config: OracleAsyncConfig,
    ) -> AsyncIterable[AsyncDriverAdapterBase]:
        """Provide SQLSpec async database session.

        This wraps SQLSpec's provide_session() context manager for
        automatic connection pooling and cleanup. Each HTTP request
        gets its own session which is automatically returned to the
        pool when the request completes.

        Args:
            manager: The SQLSpec manager (injected)
            config: The database config (injected)

        Yields:
            An async database driver session
        """
        async with manager.provide_session(config) as session:
            yield session


class CoreServiceProvider(Provider):
    """Provides core application services with automatic dependency resolution.

    This provider handles all business services. Most services are auto-wired
    by Dishka based on their constructor signatures:

    Simple services (auto-wired):
    - ProductService(driver)
    - CacheService(driver)
    - MetricsService(driver)
    - ExemplarService(driver)
    - StoreService(driver)

    Complex services (auto-wired):
    - IntentService(driver, exemplar_service, vertex_ai_service)
    - AgentToolsService(driver, product_service, metrics_service, ...)

    Services with special scopes:
    - VertexAIService - APP scope singleton (no DB needed)
    - OracleVectorSearchService - REQUEST scope with explicit provider
    """

    scope = Scope.REQUEST  # Default scope for all provides

    # Simple services - auto-wired by constructor
    @provide
    def get_product_service(self, driver: AsyncDriverAdapterBase) -> ProductService:
        """Provide ProductService."""
        return ProductService(driver)

    @provide
    def get_cache_service(self, driver: AsyncDriverAdapterBase) -> CacheService:
        """Provide CacheService."""
        return CacheService(driver)

    @provide
    def get_metrics_service(self, driver: AsyncDriverAdapterBase) -> MetricsService:
        """Provide MetricsService."""
        return MetricsService(driver)

    @provide
    def get_exemplar_service(self, driver: AsyncDriverAdapterBase) -> ExemplarService:
        """Provide ExemplarService."""
        return ExemplarService(driver)

    @provide
    def get_store_service(self, driver: AsyncDriverAdapterBase) -> StoreService:
        """Provide StoreService."""
        return StoreService(driver)

    # VertexAI service - REQUEST scope to enable embedding cache
    @provide
    def get_vertex_ai_service(self, cache_service: CacheService) -> VertexAIService:
        """Provide VertexAI service with cache support.

        Changed from APP to REQUEST scope to enable Oracle-based embedding cache.
        Each request gets a VertexAI instance with access to CacheService for
        embedding caching in the Oracle database.
        """
        return VertexAIService(cache_service=cache_service)

    # Complex services - auto-wired with multiple dependencies
    @provide
    def get_intent_service(
        self,
        driver: AsyncDriverAdapterBase,
        exemplar_service: ExemplarService,
        vertex_ai_service: VertexAIService,
    ) -> IntentService:
        """Provide IntentService with auto-wired dependencies.

        Dishka automatically resolves all three dependencies:
        - driver: from SQLSpecProvider
        - exemplar_service: from this provider
        - vertex_ai_service: from this provider (APP scope)
        """
        return IntentService(
            driver=driver,
            exemplar_service=exemplar_service,
            vertex_ai_service=vertex_ai_service,
        )

    @provide
    def get_agent_tools_service(
        self,
        driver: AsyncDriverAdapterBase,
        product_service: ProductService,
        metrics_service: MetricsService,
        intent_service: IntentService,
        vertex_ai_service: VertexAIService,
        store_service: StoreService,
    ) -> AgentToolsService:
        """Provide AgentToolsService with auto-wired dependencies.

        Dishka automatically resolves all six dependencies from
        the appropriate providers and scopes.
        """
        return AgentToolsService(
            driver=driver,
            product_service=product_service,
            metrics_service=metrics_service,
            intent_service=intent_service,
            vertex_ai_service=vertex_ai_service,
            store_service=store_service,
        )

    @provide
    def get_vector_search_service(
        self,
        product_service: ProductService,
        vertex_ai_service: VertexAIService,
        cache_service: CacheService,
    ) -> OracleVectorSearchService:
        """Provide OracleVectorSearchService with mixed-scope dependencies.

        This service depends on:
        - product_service: REQUEST scope
        - vertex_ai_service: APP scope (singleton)
        - cache_service: REQUEST scope

        Dishka handles the mixed scopes correctly.
        """
        return OracleVectorSearchService(
            products_service=product_service,
            vertex_ai_service=vertex_ai_service,
            embedding_cache=cache_service,
        )


class ADKProvider(Provider):
    """Provides ADK-specific services.

    The ADKRunner manages its own session service internally via
    SQLSpecSessionService, so it doesn't need a database session
    injected from the DI container.
    """

    @provide(scope=Scope.APP)
    def get_adk_runner(self) -> ADKRunner:
        """Provide ADK agent runner as a singleton.

        The ADKRunner is stateless and reusable across requests.
        It creates request-scoped sessions internally via SQLSpecSessionService.

        Using APP scope (singleton) is more efficient and matches the
        pattern used in the postgres demo's ADKOrchestrator.
        """
        return ADKRunner()

    @provide(scope=Scope.REQUEST)
    def get_query_context(self) -> QueryContext | None:
        """Provide query context from the current request ContextVar.

        Returns None if query_id is not set (e.g., background tasks).
        """

        qid = query_id_var.get()
        if not qid:
            return None
        return QueryContext(query_id=qid)


__all__ = [
    "ADKProvider",
    "CoreServiceProvider",
    "SQLSpecProvider",
    "get_request_container",
    "set_request_container",
]
