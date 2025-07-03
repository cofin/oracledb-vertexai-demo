from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from app import config
from app.db.repositories.chat_conversation import ChatConversationRepository
from app.db.repositories.company import CompanyRepository
from app.db.repositories.embedding_cache import EmbeddingCacheRepository
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


async def provide_company_service(db_connection: AsyncConnection) -> CompanyService:
    """Provide Company service."""
    repository = CompanyRepository(db_connection)
    return CompanyService(repository)


async def provide_product_service(db_connection: AsyncConnection) -> ProductService:
    """Provide Product service."""
    repository = ProductRepository(db_connection)
    return ProductService(repository)


async def provide_shop_service(db_connection: AsyncConnection) -> ShopService:
    """Provide Shop service."""
    repository = ShopRepository(db_connection)
    return ShopService(repository)


async def provide_inventory_service(db_connection: AsyncConnection) -> InventoryService:
    """Provide Inventory service."""
    repository = InventoryRepository(db_connection)
    return InventoryService(repository)


async def provide_user_session_service(db_connection: AsyncConnection) -> UserSessionService:
    """Provide UserSession service."""
    repository = UserSessionRepository(db_connection)
    return UserSessionService(repository)


async def provide_chat_conversation_service(db_connection: AsyncConnection) -> ChatConversationService:
    """Provide ChatConversation service."""
    repository = ChatConversationRepository(db_connection)
    return ChatConversationService(repository)


async def provide_response_cache_service(db_connection: AsyncConnection) -> ResponseCacheService:
    """Provide ResponseCache service."""
    repository = ResponseCacheRepository(db_connection)
    return ResponseCacheService(repository)


async def provide_search_metrics_service(db_connection: AsyncConnection) -> SearchMetricsService:
    """Provide SearchMetrics service."""
    repository = SearchMetricsRepository(db_connection)
    return SearchMetricsService(repository)


async def provide_intent_exemplar_service(db_connection: AsyncConnection) -> IntentExemplarService:
    """Provide IntentExemplar service."""
    repository = IntentExemplarRepository(db_connection)
    return IntentExemplarService(repository)


async def provide_embedding_cache(db_connection: AsyncConnection) -> EmbeddingCache:
    """Provide Embedding Cache service."""
    repository = EmbeddingCacheRepository(db_connection)
    return EmbeddingCache(repository, ttl_hours=24)


async def provide_vertex_ai_service() -> VertexAIService:
    """Provide Vertex AI service."""
    return VertexAIService()


async def provide_recommendation_service(
    request: Request,
    db_connection: AsyncConnection,
    vertex_ai_service: VertexAIService,
    products_service: ProductService,
    shops_service: ShopService,
    session_service: UserSessionService,
    conversation_service: ChatConversationService,
    cache_service: ResponseCacheService,
    metrics_service: SearchMetricsService,
    exemplar_service: IntentExemplarService,
    embedding_cache: EmbeddingCache,
) -> RecommendationService:
    """Provide recommendation service with Oracle integration."""
    user_id = BrowserFingerprint.get_stable_user_id(request)
    exemplar_repository = IntentExemplarRepository(db_connection)
    return RecommendationService(
        vertex_ai_service=vertex_ai_service,
        products_service=products_service,
        shops_service=shops_service,
        session_service=session_service,
        conversation_service=conversation_service,
        cache_service=cache_service,
        metrics_service=metrics_service,
        exemplar_service=exemplar_service,
        exemplar_repository=exemplar_repository,
        embedding_cache=embedding_cache,
        user_id=user_id,
    )
