from dishka import Provider, Scope, provide

from app.domain.system.services._cache import CacheService

from ._product import ProductService
from ._store import StoreService
from ._vertex_ai import OracleVectorSearchService, VertexAIService


class ProductsServiceProvider(Provider):
    scope = Scope.REQUEST

    product_service = provide(ProductService)
    store_service = provide(StoreService)

    @provide
    def get_vertex_ai_service(self, cache_service: CacheService) -> VertexAIService:
        return VertexAIService(cache_service=cache_service)

    oracle_vector_search_service = provide(OracleVectorSearchService)

__all__ = (
    "OracleVectorSearchService",
    "ProductService",
    "ProductsServiceProvider",
    "StoreService",
    "VertexAIService",
)
