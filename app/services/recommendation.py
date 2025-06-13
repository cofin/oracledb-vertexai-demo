"""Native recommendation service using Oracle + Vertex AI."""

import uuid
from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from app.services.product import ProductService
    from app.services.shop import ShopService
from app import schemas
from app.services.chat_conversation import ChatConversationService
from app.services.intent_exemplar import IntentExemplarService
from app.services.intent_router import IntentRouter
from app.services.response_cache import ResponseCacheService
from app.services.search_metrics import SearchMetricsService
from app.services.user_session import UserSessionService
from app.services.vertex_ai import OracleVectorSearchService, VertexAIService

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
        exemplar_service: IntentExemplarService | None = None,
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
        self.exemplar_service = exemplar_service
        self.user_id = user_id

        # Initialize intent router with exemplar service
        self.intent_router = IntentRouter(vertex_ai_service, exemplar_service)

        # Inject Oracle services into Vertex AI
        self.vertex_ai.set_services(metrics_service, cache_service)

    async def get_recommendation(self, query: str, session_id: str | None = None) -> schemas.CoffeeChatReply:
        """Get coffee recommendation with Oracle integration."""

        query_id = str(uuid.uuid4())

        # Get or create session
        if not session_id:
            session = await self.session_service.create_session(self.user_id)
            session_id = session["session_id"]
        else:
            active_session = await self.session_service.get_active_session(session_id)
            if active_session:
                session = active_session
            else:
                session = await self.session_service.create_session(self.user_id)
                session_id = session["session_id"]

        # Route the question through product and location matching
        chat_metadata: dict[str, Any] = {}
        chat_metadata, matched_product_ids = await self._route_products_question(query, chat_metadata)
        chat_metadata, location_count = await self._route_locations_question(
            query,
            matched_product_ids,
            chat_metadata,
        )

        # Get conversation history
        conversation_history = await self.conversation_service.get_conversation_history(
            self.user_id,
            limit=10,
            session_id=session["id"],
        )

        # Format conversation history for Vertex AI
        history_for_ai = [
            {"role": msg["role"], "content": msg["content"]}
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
            session_id=session["id"],
            user_id=self.user_id,
            role="user",
            content=query,
            message_metadata={"query_id": query_id},
        )

        await self.conversation_service.add_message(
            session_id=session["id"],
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
        return schemas.CoffeeChatReply(
            message=query,
            messages=[
                schemas.ChatMessage(message=query, source="human"),
                schemas.ChatMessage(message=ai_response, source="ai"),
            ],
            answer=ai_response,
            query_id=query_id,
            search_metrics=await self.metrics_service.get_performance_stats(hours=1),
        )

    async def _route_products_question(
        self,
        query: str,
        chat_metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Sequence[int]]:
        """Route question through semantic intent detection and product matching."""

        chat_metadata = chat_metadata or {}

        # Use semantic intent detection
        intent, confidence, exemplar = await self.intent_router.route_intent(query)

        # Log the routing decision for analysis
        logger.info(
            "Intent routing decision",
            query=query,
            intent=intent,
            confidence=confidence,
            exemplar=exemplar,
        )

        # Add routing metadata for transparency
        chat_metadata["intent_routing"] = {
            "detected_intent": intent,
            "confidence": confidence,
            "matched_exemplar": exemplar,
        }

        # Only perform vector search for product-related intents
        if intent == "PRODUCT_RAG":
            # Perform vector search using Oracle
            matched_documents = await self.vector_search.similarity_search(query=query, k=4)
            matched_product_ids = [match["metadata"]["id"] for match in matched_documents]

            if matched_product_ids:
                # Get product details using our new service
                similar_products = []
                for product_id in matched_product_ids[:2]:  # Limit to 2 products
                    product = await self.products_service.get_by_id(product_id)
                    if product:
                        similar_products.append(product)

                chat_metadata["product_matches"] = [
                    f"- {product['name']}: {product['description']}" for product in similar_products
                ]

                return chat_metadata, matched_product_ids

        return chat_metadata, []

    async def _route_locations_question(
        self,
        query: str,
        matched_product_ids: Sequence[int] | None = None,
        chat_metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int]:
        """Route question through location matching based on intent."""

        matched_product_ids = matched_product_ids or []
        chat_metadata = chat_metadata or {}

        # Check if the intent indicates location query
        intent_routing = chat_metadata.get("intent_routing", {})
        intent = intent_routing.get("detected_intent", "")

        # Handle location queries
        if intent == "LOCATION_RAG":
            shops_with_products = []

            if matched_product_ids:
                # Find shops that have these specific products
                # Get all shops and check their inventory
                all_shops = await self.shops_service.get_all()

                for shop in all_shops[:10]:  # Check first 10 shops
                    shop_inventory = await self.shops_service.get_with_inventory(shop["id"])
                    if shop_inventory and shop_inventory.get("inventory"):
                        # Check if this shop has any of the matched products
                        inventory_product_ids = [item["product_id"] for item in shop_inventory["inventory"]]
                        if any(pid in matched_product_ids for pid in inventory_product_ids):
                            shops_with_products.append(shop)
                            if len(shops_with_products) >= 4:  # noqa: PLR2004
                                break
            else:
                # If no specific products, just list some shops
                all_shops = await self.shops_service.get_all()
                shops_with_products = all_shops[:4]

            # Store shop information for context
            chat_metadata["shop_locations"] = [
                {"name": shop["name"], "address": shop["address"]} for shop in shops_with_products
            ]
            return chat_metadata, len(shops_with_products)

        return chat_metadata, 0

    def _format_context(self, query: str, chat_metadata: dict[str, Any]) -> str:
        """Format context for AI prompt."""

        formatted_parts = [f"# User Query:\n{query}"]

        if chat_metadata.get("product_matches"):
            products_text = "\n".join(chat_metadata["product_matches"])
            formatted_parts.append(f"# Matching coffee products (if applicable):\n{products_text}")

        if chat_metadata.get("shop_locations"):
            shops = chat_metadata["shop_locations"]
            location_count = len(shops)

            # Limit to first 5 shops for token management
            max_shops_in_context = 5
            if location_count > max_shops_in_context:
                shops = shops[:max_shops_in_context]
                formatted_parts.append(
                    f"# Product Availability:\nFound at {location_count} locations. Here are {max_shops_in_context} of them:"
                )
            else:
                formatted_parts.append(
                    f"# Product Availability:\nAvailable at the following {location_count} location(s):"
                )

            # Add shop details with basic sanitization
            shop_list = []
            for shop in shops:
                # Basic sanitization - remove potential prompt injection attempts
                name = shop["name"].replace("\n", " ").replace("\r", " ")[:100]
                address = shop["address"].replace("\n", " ").replace("\r", " ")[:200]
                shop_list.append(f"- {name}: {address}")

            formatted_parts.append("\n".join(shop_list))

        return "\n\n".join(formatted_parts)

    async def stream_recommendation(self, query: str, session_id: str | None = None) -> AsyncGenerator[str, None]:
        """Stream recommendation response."""

        # Get or create session
        if not session_id:
            session = await self.session_service.create_session(self.user_id)
            session_id = session["session_id"]
        else:
            active_session = await self.session_service.get_active_session(session_id)
            if active_session:
                session = active_session
            else:
                session = await self.session_service.create_session(self.user_id)
                session_id = session["session_id"]

        # Route the question (same as regular recommendation)
        chat_metadata: dict[str, Any] = {}
        chat_metadata, matched_product_ids = await self._route_products_question(query, chat_metadata)
        chat_metadata, location_count = await self._route_locations_question(
            query,
            matched_product_ids,
            chat_metadata,
        )

        # Get conversation history
        conversation_history = await self.conversation_service.get_conversation_history(
            self.user_id,
            limit=10,
            session_id=session["id"],
        )

        # Format conversation history for Vertex AI
        history_for_ai = [{"role": msg["role"], "content": msg["content"]} for msg in reversed(conversation_history)]

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
            session_id=session["id"],
            user_id=self.user_id,
            role="user",
            content=query,
            message_metadata={"query_id": query_id},
        )

        await self.conversation_service.add_message(
            session_id=session["id"],
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
