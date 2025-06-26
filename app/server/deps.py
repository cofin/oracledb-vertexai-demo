"""Coffee domain dependency providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from app import config
from app.services import (
    ChatConversationService,
    CompanyService,
    InventoryService,
    OracleVectorSearchService,
    ProductService,
    RecommendationService,
    ResponseCacheService,
    SearchMetricsService,
    ShopService,
    UserSessionService,
    VertexAIService,
)
from app.services.browser_session import BrowserFingerprint
from app.services.embedding_cache import EmbeddingCache
from app.services.intent_exemplar import IntentExemplarService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from litestar import Request
    from oracledb import AsyncConnection


# Generic service provider factory
T = TypeVar("T")


def create_service_provider(service_cls: type[T]) -> Callable[..., AsyncGenerator[T, None]]:
    """Create a generic service provider for services that require a db connection."""

    async def provider(db_connection: AsyncConnection | None = None) -> AsyncGenerator[T, None]:
        """Generic provider function."""
        if db_connection:
            yield service_cls(db_connection)  # type: ignore[call-arg]
            return
        async with config.oracle_async.get_connection() as conn:
            yield service_cls(conn)  # type: ignore[call-arg]

    return provider


# Create service providers from the factory
provide_company_service = create_service_provider(CompanyService)
provide_product_service = create_service_provider(ProductService)
provide_shop_service = create_service_provider(ShopService)
provide_inventory_service = create_service_provider(InventoryService)
provide_user_session_service = create_service_provider(UserSessionService)
provide_chat_conversation_service = create_service_provider(ChatConversationService)
provide_response_cache_service = create_service_provider(ResponseCacheService)
provide_search_metrics_service = create_service_provider(SearchMetricsService)
provide_intent_exemplar_service = create_service_provider(IntentExemplarService)


# Provider for EmbeddingCache, which has an extra argument
async def provide_embedding_cache(
    db_connection: AsyncConnection | None = None,
) -> AsyncGenerator[EmbeddingCache, None]:
    """Provide Embedding Cache service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield EmbeddingCache(db_connection, ttl_hours=24)
        return
    async with config.oracle_async.get_connection() as conn:
        yield EmbeddingCache(conn, ttl_hours=24)


# Providers that don't require a database connection directly
async def provide_vertex_ai_service() -> AsyncGenerator[VertexAIService, None]:
    """Provide Vertex AI service."""
    yield VertexAIService()


async def provide_oracle_vector_search_service(
    products_service: ProductService,
    vertex_ai_service: VertexAIService,
    embedding_cache: EmbeddingCache,
) -> AsyncGenerator[OracleVectorSearchService, None]:
    """Provide Oracle vector search service."""
    yield OracleVectorSearchService(products_service, vertex_ai_service, embedding_cache)


# Main recommendation service provider
async def provide_recommendation_service(
    request: Request,
    vertex_ai_service: VertexAIService,
    vector_search_service: OracleVectorSearchService,
    products_service: ProductService,
    shops_service: ShopService,
    session_service: UserSessionService,
    conversation_service: ChatConversationService,
    cache_service: ResponseCacheService,
    metrics_service: SearchMetricsService,
    exemplar_service: IntentExemplarService,
    embedding_cache: EmbeddingCache,
) -> AsyncGenerator[RecommendationService, None]:
    """Provide recommendation service with Oracle integration."""
    # Use browser fingerprinting for stable session identification without login
    user_id = BrowserFingerprint.get_stable_user_id(request)

    yield RecommendationService(
        vertex_ai_service=vertex_ai_service,
        vector_search_service=vector_search_service,
        products_service=products_service,
        shops_service=shops_service,
        session_service=session_service,
        conversation_service=conversation_service,
        cache_service=cache_service,
        metrics_service=metrics_service,
        exemplar_service=exemplar_service,
        embedding_cache=embedding_cache,
        user_id=user_id,
    )
