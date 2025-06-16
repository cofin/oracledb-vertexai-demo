"""Native recommendation service using Oracle + Vertex AI."""

import time
import uuid
from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from app.services.embedding_cache import EmbeddingCache
    from app.services.product import ProductService
    from app.services.shop import ShopService
from app import schemas
from app.services.chat_conversation import ChatConversationService
from app.services.embedding_cache import EmbeddingCache
from app.services.intent_exemplar import IntentExemplarService
from app.services.intent_router import IntentRouter
from app.services.persona_manager import PersonaManager
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
        embedding_cache: EmbeddingCache | None = None,
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
        self.embedding_cache = embedding_cache
        self.user_id = user_id

        # Initialize intent router with embedding cache
        # Connection will be passed to route_intent method
        self.intent_router = IntentRouter(
            self.products_service.connection,
            vertex_ai_service,
            embedding_cache,
        )

        # Inject Oracle services into Vertex AI
        self.vertex_ai.set_services(metrics_service, cache_service)

    async def get_recommendation(
        self, query: str, persona: str = "enthusiast", session_id: str | None = None
    ) -> schemas.CoffeeChatReply:
        """Get coffee recommendation with Oracle integration."""

        query_id = str(uuid.uuid4())
        start_time = time.time()

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
        intent_start = time.time()
        chat_metadata, matched_product_ids, vector_timings = await self._route_products_question(query, chat_metadata)
        intent_time = (time.time() - intent_start) * 1000

        # Track intent detection embedding cache hits
        intent_embedding_cache_hit = chat_metadata.get("intent_embedding_cache_hit", False)

        # For accurate cache reporting, only show cache hit if the FIRST embedding lookup was cached
        # The second lookup (product search) will always hit if intent detection populated the cache
        overall_embedding_cache_hit = intent_embedding_cache_hit

        # Get detected intent from metadata
        intent_routing = chat_metadata.get("intent_routing", {})
        detected_intent = intent_routing.get("detected_intent", "GENERAL_CONVERSATION")

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

        # Generate AI response with intent-aware system message and persona
        ai_start = time.time()
        ai_response, response_cache_hit = await self.vertex_ai.chat_with_history(
            query=query,
            context=context,
            conversation_history=history_for_ai,
            user_id=self.user_id,
            intent=detected_intent,
            persona=persona,
        )
        ai_time = (time.time() - ai_start) * 1000

        # DEBUG: Track response cache status for UI debugging
        logger.info("response_cache_status", response_cache_hit=response_cache_hit, query=query[:50])

        # Get embedding cache hit status from metadata
        embedding_cache_hit = overall_embedding_cache_hit

        # Calculate total time
        total_time = (time.time() - start_time) * 1000

        # Record metrics for this query (if not from cache)
        if not response_cache_hit:
            # Get similarity score from product matches if available
            similarity_score = None
            if matched_product_ids and chat_metadata.get("product_matches"):
                # Use a reasonable similarity score for successful product matches
                similarity_score = 0.8

            await self.metrics_service.record_search(
                schemas.SearchMetricsCreate(
                    query_id=query_id,
                    user_id=self.user_id,
                    search_time_ms=total_time,
                    embedding_time_ms=vector_timings["embedding_ms"],  # Actual embedding generation time
                    oracle_time_ms=vector_timings["oracle_ms"],  # Actual Oracle vector search time
                    ai_time_ms=ai_time,  # LLM generation time
                    intent_time_ms=intent_time,  # Intent detection time
                    similarity_score=similarity_score,
                    result_count=len(matched_product_ids),
                )
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
                "total_time_ms": total_time,
                "embedding_time_ms": vector_timings["embedding_ms"],
                "oracle_time_ms": vector_timings["oracle_ms"],
                "ai_time_ms": ai_time,
                "intent_time_ms": intent_time,
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
            from_cache=response_cache_hit,
            embedding_cache_hit=embedding_cache_hit,
            intent_detected=detected_intent,
        )

    async def _route_products_question(
        self,
        query: str,
        chat_metadata: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Sequence[int], dict]:
        """Route question through semantic intent detection and product matching.

        Returns:
            - chat_metadata: Enhanced with routing information
            - matched_product_ids: List of matching product IDs
            - vector_timings: Timing data from vector search operations
        """

        chat_metadata = chat_metadata or {}
        vector_timings = {"embedding_ms": 0, "oracle_ms": 0, "total_ms": 0}

        # Use semantic intent detection with Oracle connection
        intent, confidence, exemplar, intent_embedding_cache_hit = await self.intent_router.route_intent_single(query)

        # Store intent embedding cache hit status
        chat_metadata["intent_embedding_cache_hit"] = intent_embedding_cache_hit

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
            # Perform vector search using Oracle with embedding cache tracking
            matched_documents, embedding_cache_hit, vector_timings = await self.vector_search.similarity_search(query=query, k=4)
            matched_product_ids = [match["metadata"]["id"] for match in matched_documents]

            # Store embedding cache hit status in metadata
            chat_metadata["embedding_cache_hit"] = embedding_cache_hit

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

                return chat_metadata, matched_product_ids, vector_timings

        return chat_metadata, [], vector_timings

    def _format_context(self, query: str, chat_metadata: dict[str, Any]) -> str:
        """Format context for AI prompt."""

        formatted_parts = [f"# User Query:\n{query}"]

        if chat_metadata.get("product_matches"):
            products_text = "\n".join(chat_metadata["product_matches"])
            formatted_parts.append(f"# Matching coffee products (if applicable):\n{products_text}")

        return "\n\n".join(formatted_parts)

    async def stream_recommendation(
        self, query: str, persona: str = "enthusiast", session_id: str | None = None
    ) -> AsyncGenerator[str, None]:
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
        chat_metadata, matched_product_ids, _vector_timings = await self._route_products_question(query, chat_metadata)

        # Get conversation history
        conversation_history = await self.conversation_service.get_conversation_history(
            self.user_id,
            limit=10,
            session_id=session["id"],
        )

        # Format conversation history for Vertex AI
        history_for_ai = [{"role": msg["role"], "content": msg["content"]} for msg in reversed(conversation_history)]

        # Get detected intent from metadata
        intent_routing = chat_metadata.get("intent_routing", {})
        detected_intent = intent_routing.get("detected_intent", "GENERAL_CONVERSATION")

        # Build context and prompt with persona
        context = self._format_context(query, chat_metadata)
        system_msg = self.vertex_ai.create_system_message(intent=detected_intent, persona=persona)

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

        # Get temperature from persona
        temperature = PersonaManager.get_temperature(persona)

        # Stream response
        full_response = ""
        async for chunk in self.vertex_ai.stream_content(prompt, self.user_id, temperature=temperature):
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
                "streamed": True,
            },
        )
