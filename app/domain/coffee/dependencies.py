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

from typing import TYPE_CHECKING, Any

from langchain_community.vectorstores.oraclevs import OracleVS

from app.config import get_settings
from app.config.app import alchemy
from app.domain.coffee.llm import get_retrieval_chain
from app.domain.coffee.services import (
    CompanyService,
    InventoryService,
    ProductService,
    RecommendationService,
    ShopService,
)
from app.domain.coffee.utils import get_embeddings_service, get_llm

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from langchain_core.embeddings import Embeddings
    from langchain_core.runnables import Runnable
    from litestar import Request
    from oracledb import Connection
    from sqlalchemy.ext.asyncio import AsyncSession


def provide_recommendation_service(
    request: Request,
    vector_store: OracleVS,
    retrieval_chain: Runnable[Any, Any],
    products_service: ProductService,
    shops_service: ShopService,
) -> Generator[RecommendationService, None, None]:
    """Provide the embedding service."""
    yield RecommendationService(
        vector_store=vector_store,
        retrieval_chain=retrieval_chain,
        products_service=products_service,
        shops_service=shops_service,
        history_meta={"user_id": "1", "conversation_id": request.get_session_id() or "1"},
    )


def provide_embeddings_service() -> Generator[Embeddings, None, None]:
    """Provide the embedding service."""
    settings = get_settings()
    model_type = settings.app.EMBEDDING_MODEL_TYPE
    yield get_embeddings_service(model_type=model_type)


def provide_product_description_vector_store(
    db_connection: Connection,
    embeddings: Embeddings,
) -> Generator[OracleVS, None, None]:
    """Construct a vector store."""
    yield OracleVS(
        client=db_connection,
        embedding_function=embeddings,
        table_name="PRODUCT_DESCRIPTION_VS",
        query="Where can I get a good coffee nearby?",
    )


def provide_retrieval_chain() -> Generator[Runnable[Any, Any], None, None]:
    """Construct a vector store."""
    llm = get_llm()
    yield get_retrieval_chain(llm)


async def provide_companies_service(db_session: AsyncSession) -> AsyncGenerator[CompanyService, None]:
    """Provide Company service.

    Args:
        db_session (AsyncSession | None, optional): current database session. Defaults to None.

    Returns:
        CompanyService: A role service object
    """
    async with CompanyService.new(session=db_session, config=alchemy) as service:
        yield service


async def provide_products_service(db_session: AsyncSession | None = None) -> AsyncGenerator[ProductService, None]:
    """Provide products service.

    Args:
        db_session (AsyncSession | None, optional): current database session. Defaults to None.

    Returns:
        ProductService: A role service object
    """
    async with ProductService.new(session=db_session, config=alchemy) as service:
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
    async with InventoryService.new(session=db_session, config=alchemy) as service:
        yield service


async def provide_shops_service(db_session: AsyncSession | None = None) -> AsyncGenerator[ShopService, None]:
    """Provide shops service.

    Args:
        db_session (AsyncSession | None, optional): current database session. Defaults to None.

    Returns:
        ShopService: A user role service object
    """
    async with ShopService.new(session=db_session, config=alchemy) as service:
        yield service
