"""Coffee domain dependency providers."""

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

provide_vertex_ai_service = create_service_provider(
    VertexAIService,
    error_messages={
        "duplicate_key": "AI service conflict.",
        "integrity": "AI service operation failed.",
    },
)

provide_oracle_vector_search_service = create_service_provider(
    OracleVectorSearchService,
    error_messages={
        "duplicate_key": "Vector search conflict.",
        "integrity": "Vector search operation failed.",
    },
)

provide_recommendation_service = create_service_provider(
    RecommendationService,
    error_messages={
        "duplicate_key": "Recommendation service conflict.",
        "integrity": "Recommendation operation failed.",
    },
)
