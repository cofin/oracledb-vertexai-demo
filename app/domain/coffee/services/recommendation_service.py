"""Native recommendation service using Oracle + Vertex AI."""

import uuid
from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.coffee.services import ProductService, ShopService

import structlog
from advanced_alchemy.filters import CollectionFilter, LimitOffset
from sqlalchemy import select

from app.db.models import Inventory, Shop
from app.domain.coffee.schemas import ChatMessage, CoffeeChatReply, PointsOfInterest
from app.domain.coffee.services.oracle_services import (
    ChatConversationService,
    ResponseCacheService,
    SearchMetricsService,
    UserSessionService,
)
from app.domain.coffee.services.vertex_ai import OracleVectorSearchService, VertexAIService

logger = structlog.get_logger()


class RecommendationService:
    """Coffee recommendation service using native Vertex AI and Oracle."""

    def __init__(
        self,
        vertex_ai_service: VertexAIService,
        vector_search_service: OracleVectorSearchService,
        products_service: "ProductService",
        shops_service: "ShopService",
        session_service: UserSessionService,
        conversation_service: ChatConversationService,
        cache_service: ResponseCacheService,
        metrics_service: SearchMetricsService,
        user_id: str = "default",
    ) -> None:
        self.vertex_ai = vertex_ai_service
        self.vector_search = vector_search_service
        self.products_service = products_service
        self.shops_service = shops_service
        self.session_service = session_service
        self.conversation_service = conversation_service
        self.cache_service = cache_service
        self.metrics_service = metrics_service
        self.user_id = user_id

        # Inject Oracle services into Vertex AI
        self.vertex_ai.set_services(metrics_service, cache_service)

    async def get_recommendation(self, query: str, session_id: str | None = None) -> CoffeeChatReply:
        """Get coffee recommendation with Oracle integration."""

        query_id = str(uuid.uuid4())

        # Get or create session
        if not session_id:
            session = await self.session_service.create_session(self.user_id)
            session_id = session.session_id
        else:
            active_session = await self.session_service.get_active_session(session_id)
            if active_session:
                session = active_session
            else:
                session = await self.session_service.create_session(self.user_id)
                session_id = session.session_id

        # Route the question through product and location matching
        chat_metadata, matched_product_ids = await self._route_products_question(query)
        chat_metadata, location_count = await self._route_locations_question(
            query, matched_product_ids, chat_metadata,
        )

        # Get conversation history
        conversation_history = await self.conversation_service.get_conversation_history(
            self.user_id, limit=10, session_id=session.id,
        )

        # Format conversation history for Vertex AI
        history_for_ai = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(conversation_history)  # Reverse to get chronological order
        ]

        # Build context from metadata
        context = self._format_context(query, chat_metadata)

        # Generate AI response
        ai_response = await self.vertex_ai.chat_with_history(
            query=query,
            context=context,
            conversation_history=history_for_ai,
            user_id=self.user_id,
        )

        # Save conversation to Oracle
        await self.conversation_service.add_message(
            session_id=session.id,
            user_id=self.user_id,
            role="user",
            content=query,
            message_metadata={"query_id": query_id},
        )

        await self.conversation_service.add_message(
            session_id=session.id,
            user_id=self.user_id,
            role="assistant",
            content=ai_response,
            message_metadata={
                "query_id": query_id,
                "product_matches": len(matched_product_ids),
                "location_count": location_count,
            },
        )

        # Format response
        return CoffeeChatReply(
            message=query,
            messages=[
                ChatMessage(message=query, source="human"),
                ChatMessage(message=ai_response, source="ai"),
            ],
            answer=ai_response,
            points_of_interest=chat_metadata.get("locations", []),
            query_id=query_id,
            search_metrics=await self.metrics_service.get_performance_stats(hours=1),
        )

    async def _route_products_question(
        self,
        query: str,
        chat_metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Sequence[int]]:
        """Route question through product matching."""

        chat_metadata = chat_metadata or {}
        query_lower = query.lower()

        # Check if this is a coffee recommendation query
        recommend_keywords = {
            "coffee", "recommend", "looking", "latte", "cap", "americano",
            "caffeine", "beans", "need", "want", "show", "where", "give me", "gimme",
        }

        location_keywords = {
            "where", "find", "locations", "show me", "near", "looking",
            "need", "want", "give me", "gimme",
        }

        if any(word in query_lower for word in recommend_keywords.union(location_keywords)):
            # Perform vector search using Oracle
            matched_documents = await self.vector_search.similarity_search(query=query, k=4)
            matched_product_ids = [match["metadata"]["id"] for match in matched_documents]

            if matched_product_ids:
                # Get product details
                similar_products = await self.products_service.list(
                    CollectionFilter[int](
                        field_name="id",
                        values=matched_product_ids,
                    ),
                    LimitOffset(2, 0),
                )

                chat_metadata["product_matches"] = [
                    f"- {obj.name}: {obj.description}"
                    for obj in similar_products
                ]

                return chat_metadata, matched_product_ids

        return chat_metadata, []

    async def _route_locations_question(
        self,
        query: str,
        matched_product_ids: Sequence[int] | None = None,
        chat_metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int]:
        """Route question through location matching."""

        query_lower = query.lower()
        matched_product_ids = matched_product_ids or []
        chat_metadata = chat_metadata or {}

        location_keywords = {
            "where", "find", "locations", "show me", "near", "looking",
            "need", "want", "give me", "gimme",
        }

        if any(word in query_lower for word in location_keywords) and matched_product_ids:
            # Find shops that have these products
            shops_with_products = await self.shops_service.list(
                Shop.id.in_(
                    select(Inventory.shop_id).where(
                        Inventory.product_id.in_(matched_product_ids),
                    ),
                ),
                LimitOffset(4, 0),
            )

            # Convert to points of interest
            locations = [
                PointsOfInterest(
                    id=shop.id,
                    name=shop.name,
                    address=shop.address,
                    latitude=float(shop.latitude) if shop.latitude else 0.0,
                    longitude=float(shop.longitude) if shop.longitude else 0.0,
                )
                for shop in shops_with_products
            ]

            chat_metadata["locations"] = [loc.__dict__ for loc in locations]
            return chat_metadata, len(shops_with_products)

        return chat_metadata, 0

    def _format_context(self, query: str, chat_metadata: dict[str, Any]) -> str:
        """Format context for AI prompt."""

        formatted_parts = [f"# User Query:\n{query}"]

        if chat_metadata.get("product_matches"):
            products_text = "\n".join(chat_metadata["product_matches"])
            formatted_parts.append(f"# Matching coffee products (if applicable):\n{products_text}")

        if chat_metadata.get("product_matches") and chat_metadata.get("locations"):
            location_count = len(chat_metadata["locations"])
            formatted_parts.append(
                f"# Product Availability:\nThere are {location_count} location(s) with these products",
            )

        return "\n\n".join(formatted_parts)

    async def stream_recommendation(self, query: str, session_id: str | None = None) -> AsyncGenerator[str, None]:
        """Stream recommendation response."""

        # Get or create session
        if not session_id:
            session = await self.session_service.create_session(self.user_id)
            session_id = session.session_id
        else:
            active_session = await self.session_service.get_active_session(session_id)
            if active_session:
                session = active_session
            else:
                session = await self.session_service.create_session(self.user_id)
                session_id = session.session_id

        # Route the question (same as regular recommendation)
        chat_metadata, matched_product_ids = await self._route_products_question(query)
        chat_metadata, location_count = await self._route_locations_question(
            query, matched_product_ids, chat_metadata,
        )

        # Get conversation history
        conversation_history = await self.conversation_service.get_conversation_history(
            self.user_id, limit=10, session_id=session.id,
        )

        # Format conversation history for Vertex AI
        history_for_ai = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(conversation_history)
        ]

        # Build context and prompt
        context = self._format_context(query, chat_metadata)
        system_msg = self.vertex_ai.create_system_message()

        prompt_parts = [system_msg]

        if history_for_ai:
            prompt_parts.append("\n# Conversation History:")
            for msg in history_for_ai[-5:]:  # Last 5 messages for streaming
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"{role.title()}: {content}")

        if context:
            prompt_parts.append(f"\n{context}")

        prompt = "\n".join(prompt_parts)

        # Stream response
        full_response = ""
        async for chunk in self.vertex_ai.stream_content(prompt, self.user_id):
            full_response += chunk
            yield chunk

        # Save conversation to Oracle after streaming completes
        query_id = str(uuid.uuid4())

        await self.conversation_service.add_message(
            session_id=session.id,
            user_id=self.user_id,
            role="user",
            content=query,
            message_metadata={"query_id": query_id},
        )

        await self.conversation_service.add_message(
            session_id=session.id,
            user_id=self.user_id,
            role="assistant",
            content=full_response,
            message_metadata={
                "query_id": query_id,
                "product_matches": len(matched_product_ids),
                "location_count": location_count,
                "streamed": True,
            },
        )
