"""Native recommendation service using Oracle + Vertex AI."""

import time
import uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import structlog

from app import schemas
from app.schemas import QueryId, UserId

if TYPE_CHECKING:
    from app.services.embedding_cache import EmbeddingCache
    from app.services.product import ProductService
    from app.services.shop import ShopService
from app.services.chat_conversation import ChatConversationService
from app.services.embedding_cache import EmbeddingCache
from app.services.persona_manager import PersonaManager
from app.services.product_recommendation import ProductRecommendationService
from app.services.response_cache import ResponseCacheService
from app.services.search_metrics import SearchMetricsService
from app.services.user_session import UserSessionService
from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class RecommendationService:
    """Coffee recommendation service using native Vertex AI and Oracle."""

    def __init__(
        self,
        vertex_ai_service: VertexAIService,
        products_service: "ProductService",
        shops_service: "ShopService",
        session_service: UserSessionService,
        conversation_service: ChatConversationService,
        cache_service: ResponseCacheService,
        metrics_service: SearchMetricsService,
        product_recommendation_service: ProductRecommendationService,
        embedding_cache: EmbeddingCache | None = None,
        user_id: str = "default",
    ) -> None:
        self.vertex_ai = vertex_ai_service
        self.products_service = products_service
        self.shops_service = shops_service
        self.session_service = session_service
        self.conversation_service = conversation_service
        self.cache_service = cache_service
        self.metrics_service = metrics_service
        self.product_recommendation_service = product_recommendation_service
        self.embedding_cache = embedding_cache
        self.user_id = user_id

        # Inject Oracle services into Vertex AI
        self.vertex_ai.set_services(metrics_service, cache_service)

    async def get_recommendation(
        self,
        query: str,
        persona: str = "enthusiast",
        session_id: str | None = None,
    ) -> schemas.CoffeeChatReply:
        """Get coffee recommendation with Oracle integration."""

        query_id = str(uuid.uuid4())
        start_time = time.time()

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

        # Get embedding for the user query once.
        embedding_start = time.time()
        if self.embedding_cache:
            query_embedding, embedding_cache_hit = await self.embedding_cache.get_embedding(query, self.vertex_ai)
        else:
            query_embedding = await self.vertex_ai.create_embedding(query)
            embedding_cache_hit = False
        embedding_time = (time.time() - embedding_start) * 1000

        # Route the question through product and location matching
        chat_metadata: dict[str, Any] = {}
        intent_start = time.time()
        chat_metadata, matched_product_ids, vector_timings, similarity_score = await self.product_recommendation_service.recommend_products(
            query, query_embedding, chat_metadata
        )
        vector_timings["embedding_ms"] = embedding_time
        intent_time = (time.time() - intent_start) * 1000

        # Get detected intent from metadata
        intent_routing = chat_metadata.get("intent_routing", {})
        detected_intent = intent_routing.get("detected_intent", "GENERAL_CONVERSATION")

        # Get conversation history
        conversation_history = await self.conversation_service.get_conversation_history(
            self.user_id,
            limit=10,
            session_id=session.id,
        )

        # Format conversation history for Vertex AI
        history_for_ai = [
            {"role": msg.role, "content": msg.content}
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

        # Calculate total time
        total_time = (time.time() - start_time) * 1000

        # Record metrics for this query (if not from cache)
        if not response_cache_hit:
            await self.metrics_service.record_search(
                schemas.SearchMetricsCreate(
                    query_id=QueryId(query_id),
                    user_id=UserId(self.user_id) if self.user_id else None,
                    search_time_ms=total_time,
                    embedding_time_ms=embedding_time,
                    oracle_time_ms=vector_timings.get("oracle_ms", 0),
                    ai_time_ms=ai_time,
                    intent_time_ms=intent_time,
                    similarity_score=similarity_score,
                    result_count=len(matched_product_ids),
                )
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
            query_id=QueryId(query_id),
            session_id=schemas.SessionId(session_id),
            search_metrics=await self.metrics_service.get_performance_stats(hours=1),
            from_cache=response_cache_hit,
            embedding_cache_hit=embedding_cache_hit,
            intent_detected=detected_intent,
        )

    def _format_context(self, query: str, chat_metadata: dict[str, Any]) -> str:
        """Format context for AI prompt."""

        formatted_parts = [f"# User Query:\n{query}"]

        if chat_metadata.get("product_matches"):
            products_text = "\n".join(chat_metadata["product_matches"])
            formatted_parts.append(f"# Matching coffee products (if applicable):\n{products_text}")

        return "\n\n".join(formatted_parts)

    async def stream_recommendation(
        self,
        query: str,
        persona: str = "enthusiast",
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
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

        # Get embedding for the user query once for streaming
        if self.embedding_cache:
            query_embedding, _ = await self.embedding_cache.get_embedding(query, self.vertex_ai)
        else:
            query_embedding = await self.vertex_ai.create_embedding(query)

        # Route the question using pre-computed embedding
        chat_metadata: dict[str, Any] = {}
        chat_metadata, matched_product_ids, _vector_timings, _similarity = await self.product_recommendation_service.recommend_products(query, query_embedding, chat_metadata)

        # Get conversation history
        conversation_history = await self.conversation_service.get_conversation_history(
            self.user_id,
            limit=10,
            session_id=session.id,
        )

        # Format conversation history for Vertex AI
        history_for_ai = [{"role": msg.role, "content": msg.content} for msg in reversed(conversation_history)]

        # Get detected intent from metadata
        intent_routing = chat_metadata.get("intent_routing", {})
        detected_intent = intent_routing.get("detected_intent", "GENERAL_CONVERSATION")

        # Build context and prompt with persona
        context = self._format_context(query, chat_metadata)
        system_msg = self.vertex_ai.create_system_message(intent=detected_intent, persona=persona)

        prompt_parts = [system_msg]

        if history_for_ai:
            prompt_parts.append("\n# Conversation History:")
            for msg in history_for_ai[-5:]:
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
                "streamed": True,
            },
        )
