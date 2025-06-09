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

"""User Account Controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import alchemy
from app.domain.coffee.services import (
    CompanyService,
    InventoryService,
    ProductService,
    ShopService,
)
from app.domain.coffee.services.vertex_ai import VertexAIService, OracleVectorSearchService
from app.domain.coffee.services.recommendation_service import NativeRecommendationService
from app.domain.coffee.services.oracle_services import (
    UserSessionService,
    ChatConversationService,
    ResponseCacheService,
    SearchMetricsService,
)
from app.lib.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from litestar import Request
    from sqlalchemy.ext.asyncio import AsyncSession


async def provide_vertex_ai_service() -> AsyncGenerator[VertexAIService, None]:
    """Provide Vertex AI service."""
    yield VertexAIService()


async def provide_oracle_vector_search_service(
    products_service: ProductService,
    vertex_ai_service: VertexAIService
) -> AsyncGenerator[OracleVectorSearchService, None]:
    """Provide Oracle vector search service."""
    yield OracleVectorSearchService(products_service, vertex_ai_service)


async def provide_user_session_service(db_session: AsyncSession) -> AsyncGenerator[UserSessionService, None]:
    """Provide user session service."""
    async with UserSessionService.new(
        session=db_session,
        config=alchemy,
        execution_options={"populate_existing": True},
    ) as service:
        yield service


async def provide_chat_conversation_service(db_session: AsyncSession) -> AsyncGenerator[ChatConversationService, None]:
    """Provide chat conversation service."""
    async with ChatConversationService.new(
        session=db_session,
        config=alchemy,
        execution_options={"populate_existing": True},
    ) as service:
        yield service


async def provide_response_cache_service(db_session: AsyncSession) -> AsyncGenerator[ResponseCacheService, None]:
    """Provide response cache service."""
    async with ResponseCacheService.new(
        session=db_session,
        config=alchemy,
        execution_options={"populate_existing": True},
    ) as service:
        yield service


async def provide_search_metrics_service(db_session: AsyncSession) -> AsyncGenerator[SearchMetricsService, None]:
    """Provide search metrics service."""
    async with SearchMetricsService.new(
        session=db_session,
        config=alchemy,
        execution_options={"populate_existing": True},
    ) as service:
        yield service


async def provide_native_recommendation_service(
    request: Request,
    vertex_ai_service: VertexAIService,
    vector_search_service: OracleVectorSearchService,
    products_service: ProductService,
    shops_service: ShopService,
    session_service: UserSessionService,
    conversation_service: ChatConversationService,
    cache_service: ResponseCacheService,
    metrics_service: SearchMetricsService,
) -> AsyncGenerator[NativeRecommendationService, None]:
    """Provide native recommendation service with Oracle integration."""
    user_id = "1"  # You can get this from request.user if you have auth
    
    yield NativeRecommendationService(
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


async def provide_companies_service(db_session: AsyncSession) -> AsyncGenerator[CompanyService, None]:
    """Provide Company service.

    Args:
        db_session (AsyncSession | None, optional): current database session. Defaults to None.

    Returns:
        CompanyService: A role service object
    """
    async with CompanyService.new(
        session=db_session,
        config=alchemy,
        execution_options={"populate_existing": True},
    ) as service:
        yield service


async def provide_products_service(db_session: AsyncSession | None = None) -> AsyncGenerator[ProductService, None]:
    """Provide products service.

    Args:
        db_session (AsyncSession | None, optional): current database session. Defaults to None.

    Returns:
        ProductService: A role service object
    """
    async with ProductService.new(
        session=db_session,
        config=alchemy,
        execution_options={"populate_existing": True},
    ) as service:
        yield service


async def provide_inventory_service(
    db_session: AsyncSession | None = None,
) -> AsyncGenerator[InventoryService, None]:
    """Provide user oauth account service.

    Args:
        db_session (AsyncSession | None, optional): current database session. Defaults to None.

    Returns:
        InventoryService: A user oauth account service object
    """
    async with InventoryService.new(
        session=db_session,
        config=alchemy,
        execution_options={"populate_existing": True},
    ) as service:
        yield service


async def provide_shops_service(db_session: AsyncSession | None = None) -> AsyncGenerator[ShopService, None]:
    """Provide shops service.

    Args:
        db_session (AsyncSession | None, optional): current database session. Defaults to None.

    Returns:
        ShopService: A user role service object
    """
    async with ShopService.new(
        session=db_session,
        config=alchemy,
        execution_options={"populate_existing": True},
    ) as service:
        yield service
