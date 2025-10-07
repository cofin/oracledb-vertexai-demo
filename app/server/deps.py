"""Service dependency providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from app.config import db, db_manager
from app.services import CacheService, ExemplarService, MetricsService, ProductService, VertexAIService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable


# Generic service provider factory
T = TypeVar("T")


def create_service_provider(service_cls: type[T]) -> Callable[..., AsyncGenerator[T, None]]:
    """Create a generic service provider for SQLSpec-based services."""

    async def provider() -> AsyncGenerator[T, None]:
        """Generic provider function using SQLSpec's session management."""
        # SQLSpec automatically handles connection pooling and lifecycle
        async with db_manager.provide_session(db) as session:
            yield service_cls(session)  # type: ignore[call-arg]

    return provider


# Core service providers (5 total)
provide_product_service = create_service_provider(ProductService)
provide_cache_service = create_service_provider(CacheService)
provide_metrics_service = create_service_provider(MetricsService)
provide_exemplar_service = create_service_provider(ExemplarService)


# VertexAI service doesn't need database connection
async def provide_vertex_ai_service() -> AsyncGenerator[VertexAIService, None]:
    """Provide Vertex AI service."""
    yield VertexAIService()


# Oracle Vector Search Service (legacy wrapper)
async def provide_oracle_vector_search_service(
    products_service: ProductService,
    vertex_ai_service: VertexAIService,
    cache_service: CacheService,
) -> AsyncGenerator:
    """Provide Oracle vector search service with required dependencies."""
    from app.services.vertex_ai import OracleVectorSearchService

    # Create service with cache for embeddings
    service = OracleVectorSearchService(
        products_service=products_service,
        vertex_ai_service=vertex_ai_service,
        embedding_cache=cache_service,  # Pass CacheService as embedding cache
    )
    yield service


# ADK Orchestrator (when needed)
async def provide_adk_orchestrator() -> AsyncGenerator:
    """Provide ADK orchestrator for agent-based workflows."""
    from app.services.adk.orchestrator import ADKOrchestrator

    orchestrator = ADKOrchestrator()
    yield orchestrator
