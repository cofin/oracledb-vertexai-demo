"""Service dependency providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from app.config import db, sqlspec
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
        async with sqlspec.provide_session(db) as session:
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


# ADK Orchestrator (when needed)
async def provide_adk_orchestrator() -> AsyncGenerator:
    """Provide ADK orchestrator for agent-based workflows."""
    from app.services.adk.orchestrator import ADKOrchestrator

    orchestrator = ADKOrchestrator()
    yield orchestrator
