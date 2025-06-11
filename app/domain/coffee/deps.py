# ruff: noqa: ERA001
"""Coffee domain dependency providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import selectinload

from app.db import models as m
from app.domain.coffee.services.account import (
    ChatConversationService,
    ResponseCacheService,
    SearchMetricsService,
    UserSessionService,
)
from app.domain.coffee.services.company import CompanyService
from app.domain.coffee.services.inventory import InventoryService
from app.domain.coffee.services.product import ProductService
from app.domain.coffee.services.recommendation import RecommendationService
from app.domain.coffee.services.shop import ShopService
from app.domain.coffee.services.vertex_ai import OracleVectorSearchService, VertexAIService
from app.lib.deps import create_service_provider

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar import Request

# Service providers for dependency injection
provide_company_service = create_service_provider(
    CompanyService,
    load=[selectinload(m.Company.products)],
    error_messages={
        "duplicate_key": "Company already exists.",
        "integrity": "Company operation failed.",
    },
)

provide_product_service = create_service_provider(
    ProductService,
    load=[selectinload(m.Product.company)],
    error_messages={
        "duplicate_key": "Product already exists.",
        "integrity": "Product operation failed.",
    },
)

provide_shop_service = create_service_provider(
    ShopService,
    load=[selectinload(m.Shop.inventory).selectinload(m.Inventory.product)],
    error_messages={
        "duplicate_key": "Shop already exists.",
        "integrity": "Shop operation failed.",
    },
)

provide_inventory_service = create_service_provider(
    InventoryService,
    load=[
        selectinload(m.Inventory.shop),
        selectinload(m.Inventory.product).selectinload(m.Product.company),
    ],
    error_messages={
        "duplicate_key": "Inventory item already exists.",
        "integrity": "Inventory operation failed.",
    },
)

provide_user_session_service = create_service_provider(
    UserSessionService,
    load=[selectinload(m.UserSession.conversations)],
    error_messages={
        "duplicate_key": "Session already exists.",
        "integrity": "Session operation failed.",
    },
)

provide_chat_conversation_service = create_service_provider(
    ChatConversationService,
    load=[selectinload(m.ChatConversation.session)],
    error_messages={
        "duplicate_key": "Conversation already exists.",
        "integrity": "Conversation operation failed.",
    },
)

provide_response_cache_service = create_service_provider(
    ResponseCacheService,
    error_messages={
        "duplicate_key": "Cache entry already exists.",
        "integrity": "Cache operation failed.",
    },
)

provide_search_metrics_service = create_service_provider(
    SearchMetricsService,
    error_messages={
        "duplicate_key": "Metrics entry already exists.",
        "integrity": "Metrics operation failed.",
    },
)

# Non-repository service providers


async def provide_vertex_ai_service() -> AsyncGenerator[VertexAIService, None]:
    """Provide Vertex AI service."""
    yield VertexAIService()


async def provide_oracle_vector_search_service(
    products_service: ProductService,
    vertex_ai_service: VertexAIService,
) -> AsyncGenerator[OracleVectorSearchService, None]:
    """Provide Oracle vector search service."""
    yield OracleVectorSearchService(products_service, vertex_ai_service)


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
        user_id=user_id,
    )
