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

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Any

import structlog
from advanced_alchemy.filters import CollectionFilter, LimitOffset
from advanced_alchemy.repository import SQLAlchemyAsyncRepository, SQLAlchemyAsyncSlugRepository
from advanced_alchemy.service import (
    SQLAlchemyAsyncRepositoryService,
)
from langchain.schema import SystemMessage
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import (
    ConfigurableFieldSpec,
    Runnable,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from sqlalchemy import select

from app.db.models import Company, Inventory, Product, Shop
from app.domain.coffee.utils import (
    get_chat_history_manager,
    get_llm,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from langchain_community.vectorstores.oraclevs import OracleVS
    from langchain_core.runnables import Runnable

    from app.domain.coffee.schemas import CoffeeChatReply, HistoryMeta


logger = structlog.get_logger()


class RecommendationService:
    def __init__(
        self,
        vector_store: OracleVS,
        products_service: ProductService,
        shops_service: ShopService,
        history_meta: HistoryMeta,
        system_context_message: str | None = None,
    ) -> None:
        """Provides a coffee recommendation based on provided input"""
        self.vector_store = vector_store
        self.products_service = products_service
        self.shops_service = shops_service
        self.history_meta = history_meta
        self.system_message = self._setup_system_message(system_context_message)

    async def get_recommendation(self, query: str, system_message: SystemMessage | None = None) -> CoffeeChatReply:
        chain = self.get_retrieval_chain(system_message)
        chat_metadata, matched_product_ids = await self._route_products_question(query, {})
        chat_metadata, _matched_location_count = await self._route_locations_question(
            query,
            matched_product_ids,
            chat_metadata,
        )
        user_id, conversation_id = self.history_meta.get("user_id", "1"), self.history_meta.get("conversation_id", "1")
        history_manager = get_chat_history_manager(user_id, conversation_id)

        llm_response = await chain.ainvoke(
            {
                "question": self._format_user_input(query, chat_metadata),
                "chat_history": await history_manager.aget_messages(),
            },
            config={
                "configurable": {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                },
            },
        )
        await history_manager.aadd_messages([HumanMessage(content=query), llm_response])
        return self.format_response(query, llm_response.content, chat_metadata)

    def get_retrieval_chain(self, system_message: SystemMessage | None = None) -> Runnable[Any, Any]:
        ### Contextualize question ###
        system_message = system_message if system_message is not None else self.system_message
        model = get_llm()
        prompt = ChatPromptTemplate.from_messages(
            [system_message, MessagesPlaceholder("chat_history"), ("human", "{question}")],
        )
        runnable = prompt | model
        return RunnableWithMessageHistory(
            runnable=runnable,  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]
            get_session_history=get_chat_history_manager,
            history_factory_config=[
                ConfigurableFieldSpec(
                    id="user_id",
                    annotation=str,
                    name="User ID",
                    description="Unique identifier for the user.",
                    default="",
                    is_shared=True,
                ),
                ConfigurableFieldSpec(
                    id="conversation_id",
                    annotation=str,
                    name="Conversation ID",
                    description="Unique identifier for the conversation.",
                    default="",
                    is_shared=True,
                ),
            ],
            input_messages_key="question",
            history_messages_key="chat_history",
        )

    @staticmethod
    def format_response(query: str, chat_response: Any, chat_metadata: Any) -> CoffeeChatReply:
        return {
            "message": query,
            "messages": [
                {"message": query, "source": "human"},
                {"message": chat_response, "source": "ai"},
            ],
            "answer": chat_response,
            "points_of_interest": chat_metadata.get("locations", []),
            "llm_response": chat_response,
        }

    def _setup_system_message(self, message: str | None = None) -> SystemMessage:
        """Set up the system message"""
        setup = dedent("""
            You are a helpful AI assistant specializing in coffee recommendations.
            Given a user's chat history and the latest user query and a list of matching coffees from a database, provide an engaging and informative response.
            If the user is asking about coffee recommendations and locations, provide the information and finish the response with "the map below displays the locations where you can find the coffee."
            If the user is asking a general question or making a statement, respond appropriately without using the database.
            Your responses should be as concise as possible.

            When providing locations, only provide responses that utilize the count of stores found that match the product selection.  The Locations will be provided separately by another component of the user interface.
        """)
        system_message = message or dedent(setup).strip()
        return SystemMessage(content=system_message)

    def _format_user_input(
        self,
        query: str,
        chat_metadata: dict[str, Any],
    ) -> Any:
        formatted_query: str = dedent(f"""
            # User Query:
            {query}

        """)
        if chat_metadata.get("product_matches"):
            fragment = "\n".join(chat_metadata.get("product_matches", []))
            formatted_query += dedent(f"""
                # Matching coffee products (if applicable):
            {fragment}
            """)
        if chat_metadata.get("product_matches") and chat_metadata.get("locations"):
            fragment = f"\n# There are {len(chat_metadata.get('locations', []))} location(s) with these products\n"
            formatted_query += dedent(f"""
                # Product Availability:
            {fragment}
            """)
        return formatted_query

    async def _route_products_question(
        self,
        query: str,
        chat_metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Sequence[int]]:
        query = query.lower()
        # this should be a sub-chain route: https://python.langchain.com/docs/how_to/routing/
        chat_metadata = chat_metadata if chat_metadata is not None else {}
        if any(word in query.lower() for word in _RECOMMEND_KEYWORDS.union(_LOCATION_KEYWORDS)):
            matched_documents = await self.vector_store.asimilarity_search(query=query, k=4)
            matched_product_ids = [match.metadata["id"] for match in matched_documents]
            similar_products = await self.products_service.list(
                CollectionFilter[int](
                    field_name="id",
                    values=matched_product_ids,
                ),
                LimitOffset(2, 0),
            )
            chat_metadata["product_matches"] = [f"- {obj.name}: {obj.description}" for obj in similar_products]
            return chat_metadata, matched_product_ids
        return chat_metadata, []

    async def _route_locations_question(
        self,
        query: str,
        matched_product_ids: Sequence[int] | None = None,
        chat_metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int]:
        query = query.lower()
        matched_product_ids = matched_product_ids if matched_product_ids is not None else []
        chat_metadata = chat_metadata if chat_metadata is not None else {}
        # this should be a sub-chain route: https://python.langchain.com/docs/how_to/routing/
        if any(word in query for word in _LOCATION_KEYWORDS) and matched_product_ids:
            shops_with_products = await self.shops_service.list(
                Shop.id.in_(select(Inventory.shop_id).where(Inventory.product_id.in_(matched_product_ids))),
                LimitOffset(4, 0),
            )
            chat_metadata["locations"] = [
                obj.to_dict(exclude={"created_at", "updated_at"}) for obj in shops_with_products
            ]
            return chat_metadata, len(shops_with_products)
        return chat_metadata, 0


# recommendation
# to do: integrate proper routing: https://python.langchain.com/docs/how_to/routing/
_LOCATION_KEYWORDS = {"where", "find", "locations", "show me", "near", "looking", "need", "want", "give me", "gimme"}
_RECOMMEND_KEYWORDS = {
    "coffee",
    "recommend",
    "looking",
    "latte",
    "cap",
    "americano",
    "caffeine",
    "beans",
    "need",
    "want",
    "show",
    "where",
    "give me",
    "gimme",
}


# EVERYTHING BELOW HERE ARE REGULAR SQLALCHEMY MODELS.
# The logic below is purely for easy CRUD interaction with models
# See: https://github.com/litestar-org/advanced-alchemy


# Company Repository and Service


class CompanyRepository(SQLAlchemyAsyncRepository[Company]):
    model_type = Company


class CompanyService(SQLAlchemyAsyncRepositoryService[Company]):
    """Handles database operations for user roles."""

    repository_type = CompanyRepository


# Product Repository and Service


class ProductRepository(SQLAlchemyAsyncRepository[Product]):
    model_type = Product


class ProductService(SQLAlchemyAsyncRepositoryService[Product]):
    """Handles database operations for user roles."""

    repository_type = ProductRepository


# Shop Repository and Service


class ShopRepository(SQLAlchemyAsyncSlugRepository[Shop]):
    model_type = Shop


class ShopService(SQLAlchemyAsyncRepositoryService[Shop]):
    """Handles database operations for user roles."""

    repository_type = ShopRepository


# Inventory Repository and Service


class InventoryRepository(SQLAlchemyAsyncRepository[Inventory]):
    model_type = Inventory


class InventoryService(SQLAlchemyAsyncRepositoryService[Inventory]):
    """Handles database operations for user roles."""

    repository_type = InventoryRepository
