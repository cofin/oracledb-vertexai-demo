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
from typing import TYPE_CHECKING, Any, Literal, TypedDict

from advanced_alchemy.filters import CollectionFilter, LimitOffset
from advanced_alchemy.service import (
    SQLAlchemyAsyncRepositoryService,
)
from sqlalchemy import select

from app.db.models import Company, Inventory, Product, Shop
from app.domain.coffee.repositories import CompanyRepository, InventoryRepository, ProductRepository, ShopRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from langchain_community.vectorstores.oraclevs import OracleVS
    from langchain_core.runnables import Runnable


class PointsOfInterest(TypedDict):
    id: int
    name: str
    address: str
    latitude: float
    longitude: float


class ChatMessage(TypedDict):
    message: str
    source: Literal["human", "ai", "system"]


class CoffeeChatReply(TypedDict):
    message: str
    messages: list[ChatMessage]
    answer: str
    points_of_interest: list[PointsOfInterest]


class HistoryMeta(TypedDict):
    conversation_id: str
    user_id: str


class RecommendationService:
    def __init__(
        self,
        vector_store: OracleVS,
        retrieval_chain: Runnable[Any, Any],
        products_service: ProductService,
        shops_service: ShopService,
        history_meta: HistoryMeta,
    ) -> None:
        self.vector_store = vector_store
        self.retrieval_chain = retrieval_chain
        self.products_service = products_service
        self.shops_service = shops_service
        self.history_meta = history_meta

    async def ask_question(self, query: str) -> CoffeeChatReply:
        chat_metadata: dict[str, Any] = {}
        matched_product_ids: Sequence[int] = []
        if any(word in query for word in ("coffee", "recommend")):
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
        if any(word in query for word in ("where", "find", "locations", "show me", "near")) and matched_product_ids:
            shops_with_products = await self.shops_service.list(
                Shop.id.in_(select(Inventory.shop_id).where(Inventory.product_id.in_(matched_product_ids))),
                LimitOffset(4, 0),
            )
            chat_metadata["locations"] = [
                obj.to_dict(exclude={"created_at", "updated_at"}) for obj in shops_with_products
            ]
        llm_response = await self._llm_response(
            query,
            chat_metadata,
        )
        chat_response: CoffeeChatReply = {
            "message": query,
            "messages": [
                {"message": query, "source": "human"},
                {"message": llm_response, "source": "ai"},
            ],
            "answer": llm_response,
            "points_of_interest": chat_metadata.get("locations", []),
        }
        return chat_response

    async def _llm_response(
        self,
        query: str,
        chat_metadata: dict[str, Any],
    ) -> str:
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
        chat_response = await self.retrieval_chain.ainvoke(
            {"input": formatted_query},
            config={
                "configurable": {
                    "conversation_id": self.history_meta["conversation_id"] or "1",
                    "user_id": self.history_meta["user_id"],
                },
            },
        )
        return chat_response.content  # type: ignore


class ProductService(SQLAlchemyAsyncRepositoryService[Product]):
    """Handles database operations for user roles."""

    repository_type = ProductRepository


class InventoryService(SQLAlchemyAsyncRepositoryService[Inventory]):
    """Handles database operations for user roles."""

    repository_type = InventoryRepository


class CompanyService(SQLAlchemyAsyncRepositoryService[Company]):
    """Handles database operations for user roles."""

    repository_type = CompanyRepository


class ShopService(SQLAlchemyAsyncRepositoryService[Shop]):
    """Handles database operations for user roles."""

    repository_type = ShopRepository
