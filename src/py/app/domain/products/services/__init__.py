# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.genai import Client

from app.domain.system.services import CacheService
from app.lib.di import Provider, Scope, provide
from app.lib.settings import get_settings

from .services import OracleVectorSearchService, ProductService, StoreService, VertexAIService

settings = get_settings()


class ProductsServiceProvider(Provider):
    scope = Scope.REQUEST

    product_service = provide(ProductService)
    store_service = provide(StoreService)

    @provide(scope=Scope.APP)
    def get_vertex_ai_service(self, client: Client, cache_service: CacheService) -> VertexAIService:
        return VertexAIService(
            client=client,
            model=settings.vertex_ai.CHAT_MODEL,
            embedding_model=settings.vertex_ai.EMBEDDING_MODEL,
            cache_service=cache_service,
        )

    @provide
    def get_vector_search_service(
        self, vertex_ai_service: VertexAIService, product_service: ProductService
    ) -> OracleVectorSearchService:
        return OracleVectorSearchService(vertex_ai_service=vertex_ai_service, product_service=product_service)


__all__ = (
    "OracleVectorSearchService",
    "ProductService",
    "ProductsServiceProvider",
    "StoreService",
    "VertexAIService",
)
