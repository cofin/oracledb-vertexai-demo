# ruff: noqa: ERA001
"""Coffee domain dependency providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
from app.services.intent_exemplar import IntentExemplarService
from app.services.oracle_metrics import OracleMetricsService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar import Request
    from oracledb import AsyncConnection


# Service providers for dependency injection


async def provide_company_service(db_connection: AsyncConnection | None = None) -> AsyncGenerator[CompanyService, None]:
    """Provide Company service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield CompanyService(db_connection)
        return
    async with config.oracle_async.get_connection() as conn:
        yield CompanyService(conn)


async def provide_product_service(db_connection: AsyncConnection | None = None) -> AsyncGenerator[ProductService, None]:
    """Provide Product service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield ProductService(db_connection)
        return
    async with config.oracle_async.get_connection() as conn:
        yield ProductService(conn)


async def provide_shop_service(db_connection: AsyncConnection | None = None) -> AsyncGenerator[ShopService, None]:
    """Provide Shop service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield ShopService(db_connection)
        return
    async with config.oracle_async.get_connection() as conn:
        yield ShopService(conn)


async def provide_inventory_service(
    db_connection: AsyncConnection | None = None,
) -> AsyncGenerator[InventoryService, None]:
    """Provide Inventory service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield InventoryService(db_connection)
        return
    async with config.oracle_async.get_connection() as conn:
        yield InventoryService(conn)


async def provide_user_session_service(
    db_connection: AsyncConnection | None = None,
) -> AsyncGenerator[UserSessionService, None]:
    """Provide User Session service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield UserSessionService(db_connection)
        return
    async with config.oracle_async.get_connection() as conn:
        yield UserSessionService(conn)


async def provide_chat_conversation_service(
    db_connection: AsyncConnection | None = None,
) -> AsyncGenerator[ChatConversationService, None]:
    """Provide Chat Conversation service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield ChatConversationService(db_connection)
        return
    async with config.oracle_async.get_connection() as conn:
        yield ChatConversationService(conn)


async def provide_response_cache_service(
    db_connection: AsyncConnection | None = None,
) -> AsyncGenerator[ResponseCacheService, None]:
    """Provide Response Cache service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield ResponseCacheService(db_connection)
        return
    async with config.oracle_async.get_connection() as conn:
        yield ResponseCacheService(conn)


async def provide_search_metrics_service(
    db_connection: AsyncConnection | None = None,
) -> AsyncGenerator[SearchMetricsService, None]:
    """Provide Search Metrics service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield SearchMetricsService(db_connection)
        return
    async with config.oracle_async.get_connection() as conn:
        yield SearchMetricsService(conn)


async def provide_intent_exemplar_service(
    db_connection: AsyncConnection | None = None,
) -> AsyncGenerator[IntentExemplarService, None]:
    """Provide Intent Exemplar service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield IntentExemplarService(db_connection)
        return
    async with config.oracle_async.get_connection() as conn:
        yield IntentExemplarService(conn)


async def provide_vertex_ai_service() -> AsyncGenerator[VertexAIService, None]:
    """Provide Vertex AI service."""
    yield VertexAIService()


async def provide_oracle_vector_search_service(
    products_service: ProductService,
    vertex_ai_service: VertexAIService,
) -> AsyncGenerator[OracleVectorSearchService, None]:
    """Provide Oracle vector search service."""
    yield OracleVectorSearchService(products_service, vertex_ai_service)


async def provide_oracle_metrics_service(
    db_connection: AsyncConnection | None = None,
) -> AsyncGenerator[OracleMetricsService, None]:
    """Provide Oracle Metrics service with Oracle connection."""
    if db_connection:
        # If a specific connection is provided, use it
        yield OracleMetricsService(db_connection)
        return
    async with config.oracle_async.get_connection() as conn:
        yield OracleMetricsService(conn)


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
) -> AsyncGenerator[RecommendationService, None]:
    """Provide recommendation service with Oracle integration."""
    # if hasattr(request, "user") and request.user.is_authenticated:
    #     # Use the authenticated user's ID if available
    #     user_id = request.user.id
    user_id = "1"  # You can get this from request.user if you have auth

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
        user_id=user_id,
    )
