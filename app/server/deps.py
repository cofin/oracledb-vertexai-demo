from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from app import config
from app.db.repositories import (
    ChatConversationRepository,
    CompanyRepository,
    EmbeddingCacheRepository,
    IntentExemplarRepository,
    InventoryRepository,
    ProductRepository,
    ResponseCacheRepository,
    SearchMetricsRepository,
    ShopRepository,
    UserSessionRepository,
)
from app.services import (
    ChatConversationService,
    CompanyService,
    EmbeddingCache,
    IntentExemplarService,
    IntentService,
    InventoryService,
    ProductRecommendationService,
    ProductService,
    RecommendationService,
    ResponseCacheService,
    SearchMetricsService,
    ShopService,
    UserSessionService,
    VectorDemoService,
    VertexAIService,
)
from app.services.browser_session import BrowserFingerprint

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from litestar import Request
    from oracledb import AsyncConnection

RepositoryT = TypeVar("RepositoryT")
ServiceT = TypeVar("ServiceT")


def create_service_provider(
    repo_class: type[RepositoryT],
    service_class: type[ServiceT],
    **kwargs: Any,
) -> Callable[[AsyncConnection], ServiceT]:
    def provider(db_connection: AsyncConnection) -> ServiceT:
        repository = repo_class(db_connection)  # type: ignore[call-arg]
        return service_class(repository, **kwargs)  # type: ignore[call-arg]

    return provider


async def provide_db_connection() -> AsyncGenerator[AsyncConnection, None]:
    """Provide a database connection."""
    async with config.oracle_async.get_connection() as conn:
        yield conn


provide_company_service = create_service_provider(CompanyRepository, CompanyService)
provide_product_service = create_service_provider(ProductRepository, ProductService)
provide_shop_service = create_service_provider(ShopRepository, ShopService)
provide_inventory_service = create_service_provider(InventoryRepository, InventoryService)
provide_user_session_service = create_service_provider(UserSessionRepository, UserSessionService)
provide_chat_conversation_service = create_service_provider(ChatConversationRepository, ChatConversationService)
provide_response_cache_service = create_service_provider(ResponseCacheRepository, ResponseCacheService)
provide_search_metrics_service = create_service_provider(SearchMetricsRepository, SearchMetricsService)
provide_intent_exemplar_service = create_service_provider(IntentExemplarRepository, IntentExemplarService)
provide_embedding_cache = create_service_provider(EmbeddingCacheRepository, EmbeddingCache, ttl_hours=24)
async def provide_intent_service(
    intent_exemplar_service: IntentExemplarService,
    vertex_ai_service: VertexAIService,
    embedding_cache: EmbeddingCache,
) -> IntentService:
    """Provide an intent service instance."""
    return IntentService(
        exemplar_repository=intent_exemplar_service.repository,
        vertex_ai_service=vertex_ai_service,
        embedding_cache=embedding_cache,
    )

async def provide_vector_demo_service(
    vertex_ai_service: VertexAIService,
    products_service: ProductService,
    metrics_service: SearchMetricsService,
    embedding_cache: EmbeddingCache,
) -> VectorDemoService:
    """Provide a vector demo service instance."""
    return VectorDemoService(
        vertex_ai_service=vertex_ai_service,
        products_service=products_service,
        metrics_service=metrics_service,
        embedding_cache=embedding_cache,
    )

async def provide_oracle_vector_search_service(
    vertex_ai_service: VertexAIService,
    products_service: ProductService,
    metrics_service: SearchMetricsService,
    embedding_cache: EmbeddingCache,
) -> VectorDemoService:
    """Provide an oracle vector search service instance."""
    return VectorDemoService(
        vertex_ai_service=vertex_ai_service,
        products_service=products_service,
        metrics_service=metrics_service,
        embedding_cache=embedding_cache,
    )


async def provide_vertex_ai_service() -> VertexAIService:
    """Provide Vertex AI service."""
    return VertexAIService()


async def provide_product_recommendation_service(
    intent_service: IntentService, products_service: ProductService
) -> ProductRecommendationService:
    """Provide product recommendation services."""
    return ProductRecommendationService(intent_service, products_service)


async def provide_recommendation_service(
    request: Request,
    vertex_ai_service: VertexAIService,
    products_service: ProductService,
    shops_service: ShopService,
    session_service: UserSessionService,
    conversation_service: ChatConversationService,
    cache_service: ResponseCacheService,
    metrics_service: SearchMetricsService,
    product_recommendation_service: ProductRecommendationService,
    embedding_cache: EmbeddingCache,
) -> RecommendationService:
    """Provide recommendation service with Oracle integration."""
    user_id = BrowserFingerprint.get_stable_user_id(request)
    return RecommendationService(
        vertex_ai_service=vertex_ai_service,
        products_service=products_service,
        shops_service=shops_service,
        session_service=session_service,
        conversation_service=conversation_service,
        cache_service=cache_service,
        metrics_service=metrics_service,
        product_recommendation_service=product_recommendation_service,
        embedding_cache=embedding_cache,
        user_id=user_id,
    )
