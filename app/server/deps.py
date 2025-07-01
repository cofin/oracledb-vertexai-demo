from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from app import config
from app.db.repositories.chat_conversation import ChatConversationRepository
from app.db.repositories.company import CompanyRepository
from app.db.repositories.intent_exemplar import IntentExemplarRepository
from app.db.repositories.inventory import InventoryRepository
from app.db.repositories.product import ProductRepository
from app.db.repositories.response_cache import ResponseCacheRepository
from app.db.repositories.search_metrics import SearchMetricsRepository
from app.db.repositories.shop import ShopRepository
from app.db.repositories.user_session import UserSessionRepository
from app.services import (
    ChatConversationService,
    CompanyService,
    InventoryService,
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
    from collections.abc import AsyncGenerator

    from litestar import Request
    from oracledb import AsyncConnection


T = TypeVar("T")


async def provide_db_connection() -> AsyncGenerator[AsyncConnection, None]:
    """Provide a database connection."""
    async with config.oracle_async.get_connection() as conn:
        yield conn


async def provide_company_repository(db_connection: AsyncConnection) -> CompanyRepository:
    """Provide Company repository."""
    return CompanyRepository(db_connection)


async def provide_product_repository(db_connection: AsyncConnection) -> ProductRepository:
    """Provide Product repository."""
    return ProductRepository(db_connection)


async def provide_shop_repository(db_connection: AsyncConnection) -> ShopRepository:
    """Provide Shop repository."""
    return ShopRepository(db_connection)


async def provide_inventory_repository(db_connection: AsyncConnection) -> InventoryRepository:
    """Provide Inventory repository."""
    return InventoryRepository(db_connection)


async def provide_user_session_repository(db_connection: AsyncConnection) -> UserSessionRepository:
    """Provide UserSession repository."""
    return UserSessionRepository(db_connection)


async def provide_chat_conversation_repository(db_connection: AsyncConnection) -> ChatConversationRepository:
    """Provide ChatConversation repository."""
    return ChatConversationRepository(db_connection)


async def provide_response_cache_repository(db_connection: AsyncConnection) -> ResponseCacheRepository:
    """Provide ResponseCache repository."""
    return ResponseCacheRepository(db_connection)


async def provide_search_metrics_repository(db_connection: AsyncConnection) -> SearchMetricsRepository:
    """Provide SearchMetrics repository."""
    return SearchMetricsRepository(db_connection)


async def provide_intent_exemplar_repository(db_connection: AsyncConnection) -> IntentExemplarRepository:
    """Provide IntentExemplar repository."""
    return IntentExemplarRepository(db_connection)


async def provide_company_service(company_repository: CompanyRepository) -> CompanyService:
    """Provide Company service."""
    return CompanyService(company_repository)


async def provide_product_service(product_repository: ProductRepository) -> ProductService:
    """Provide Product service."""
    return ProductService(product_repository)


async def provide_shop_service(shop_repository: ShopRepository) -> ShopService:
    """Provide Shop service."""
    return ShopService(shop_repository)


async def provide_inventory_service(inventory_repository: InventoryRepository) -> InventoryService:
    """Provide Inventory service."""
    return InventoryService(inventory_repository)


async def provide_user_session_service(user_session_repository: UserSessionRepository) -> UserSessionService:
    """Provide UserSession service."""
    return UserSessionService(user_session_repository)


async def provide_chat_conversation_service(
    chat_conversation_repository: ChatConversationRepository,
) -> ChatConversationService:
    """Provide ChatConversation service."""
    return ChatConversationService(chat_conversation_repository)


async def provide_response_cache_service(response_cache_repository: ResponseCacheRepository) -> ResponseCacheService:
    """Provide ResponseCache service."""
    return ResponseCacheService(response_cache_repository)


async def provide_search_metrics_service(search_metrics_repository: SearchMetricsRepository) -> SearchMetricsService:
    """Provide SearchMetrics service."""
    return SearchMetricsService(search_metrics_repository)


async def provide_intent_exemplar_service(
    intent_exemplar_repository: IntentExemplarRepository,
) -> IntentExemplarService:
    """Provide IntentExemplar service."""
    return IntentExemplarService(intent_exemplar_repository)


async def provide_embedding_cache(embedding_cache_repository: EmbeddingCacheRepository) -> EmbeddingCache:
    """Provide Embedding Cache service."""
    return EmbeddingCache(embedding_cache_repository, ttl_hours=24)


async def provide_vertex_ai_service() -> VertexAIService:
    """Provide Vertex AI service."""
    return VertexAIService()


async def provide_recommendation_service(
    request: Request,
    vertex_ai_service: VertexAIService,
    product_repository: ProductRepository,
    shop_service: ShopService,
    session_service: UserSessionService,
    conversation_service: ChatConversationService,
    cache_service: ResponseCacheService,
    metrics_service: SearchMetricsService,
    exemplar_service: IntentExemplarService,
    embedding_cache: EmbeddingCache,
) -> RecommendationService:
    """Provide recommendation service with Oracle integration."""
    user_id = BrowserFingerprint.get_stable_user_id(request)
    return RecommendationService(
        vertex_ai_service=vertex_ai_service,
        vector_search_service=None,  # This is removed
        products_service=ProductService(product_repository),
        shops_service=shop_service,
        session_service=session_service,
        conversation_service=conversation_service,
        cache_service=cache_service,
        metrics_service=metrics_service,
        exemplar_service=exemplar_service,
        embedding_cache=embedding_cache,
        user_id=user_id,
    )
