"""Native Vertex AI service without LangChain."""

from __future__ import annotations

import array
import time
import uuid
from typing import TYPE_CHECKING, Any, cast

import structlog
from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types

from app.lib.settings import get_settings
from app.schemas import SearchMetricsCreate
from app.services.persona_manager import PersonaManager

logger = structlog.get_logger()

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from app.services.embedding_cache import EmbeddingCache
    from app.services.response_cache import ResponseCacheService
    from app.services.search_metrics import SearchMetricsService


class VertexAIService:
    """Native Vertex AI service without LangChain."""

    def __init__(self) -> None:
        settings = get_settings()

        # Initialize Google GenAI client
        self.client = genai.Client(
            vertexai=True,
            project=settings.app.GOOGLE_PROJECT_ID,
            location="us-central1",
        )

        # Initialize models from settings
        self.model_name = settings.app.GEMINI_MODEL
        self.embedding_model = settings.app.EMBEDDING_MODEL

        logger.info("Initialized model", model=self.model_name)

        # Oracle services for metrics and caching
        self.metrics_service: SearchMetricsService | None = None
        self.cache_service: ResponseCacheService | None = None

    def set_services(self, metrics_service: SearchMetricsService, cache_service: ResponseCacheService) -> None:
        """Inject Oracle services."""
        self.metrics_service = metrics_service
        self.cache_service = cache_service

    def get_model_info(self) -> dict[str, str]:
        """Get information about the currently active model."""
        return {
            "active_model": self.model_name,
            "active_model_full": self.model_name,
            "configured_model": self.model_name,
            "embedding_model": self.embedding_model,
        }

    async def generate_content(
        self,
        prompt: str,
        user_id: str = "default",
        use_cache: bool = True,
        temperature: float = 0.7,
    ) -> tuple[str, bool]:
        """Generate content with Oracle caching, returning cache status."""
        return await self.generate_content_with_cache_key(prompt, prompt, user_id, use_cache, temperature)

    async def generate_content_with_cache_key(
        self,
        prompt: str,
        cache_key: str,
        user_id: str = "default",
        use_cache: bool = True,
        temperature: float = 0.7,
    ) -> tuple[str, bool]:
        """Generate content with custom cache key, returning cache status."""

        # Try cache first
        if use_cache and self.cache_service:
            cached = await self.cache_service.get_cached_response(cache_key, user_id)
            if cached is not None:
                content = cached.get("content", "")
                if content:  # Only return cache hit if there's actual content
                    return str(content), True  # Cache hit

        # Record timing
        start_time = time.time()

        try:
            # Configure generation with temperature
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature),
            )
            content = response.text

            # Cache successful response
            if use_cache and self.cache_service:
                try:
                    await self.cache_service.cache_response(
                        cache_key,
                        {"content": content, "model": self.model_name},
                        ttl_minutes=5,
                        user_id=user_id,
                    )
                except Exception as cache_error:  # noqa: BLE001
                    logger.warning("oracle_cache_write_error", error=str(cache_error), cache_key=cache_key[:50])

        except google_exceptions.GoogleAPIError as e:
            # Handle API errors gracefully
            return f"I apologize, but I'm experiencing technical difficulties. Please try again. Error: {e!s}", False
        else:
            return cast("str", content), False  # Cache miss

        finally:
            # Record metrics
            if self.metrics_service:
                total_time = (time.time() - start_time) * 1000
                await self.metrics_service.record_search(
                    SearchMetricsCreate(
                        query_id=str(uuid.uuid4()),
                        user_id=user_id,
                        search_time_ms=total_time,
                        embedding_time_ms=0,  # Not applicable for generation
                        oracle_time_ms=0,  # Measured separately
                        result_count=1,
                    ),
                )

    async def stream_content(
        self,
        prompt: str,
        user_id: str = "default",
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream content generation."""
        try:
            # Configure generation with temperature for streaming
            async for chunk in await self.client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature),
            ):
                if chunk.text:
                    yield chunk.text

        except google_exceptions.GoogleAPIError as e:
            yield f"Error: {e!s}"

    async def create_embedding(self, text: str) -> list[float]:
        """Create embeddings using Google GenAI."""
        try:
            # Use the Google GenAI embedding model
            response = await self.client.aio.models.embed_content(
                model=self.embedding_model,
                contents=text,
            )

            if response.embeddings and len(response.embeddings) > 0:
                return cast("list[float]", response.embeddings[0].values)
            # Fallback to mock embedding for development

        except Exception:
            # Log the error and fallback to mock embedding
            logger.exception("Embedding generation failed, using fallback")
            return [0.0] * 768  # Standard embedding dimension
        else:
            return [0.0] * 768

    def create_system_message(
        self, message: str | None = None, intent: str | None = None, persona: str = "enthusiast"
    ) -> str:
        """Create system message based on detected intent and persona."""

        # Base system message varies by intent
        if intent == "GENERAL_CONVERSATION":
            base_message = """
You are a friendly AI assistant for Cymbal Coffee. While you specialize in coffee, you can also help with general conversation.

For general queries or greetings:
- Be friendly and conversational
- If asked about topics unrelated to coffee, politely acknowledge that your expertise is in coffee
- You can engage in light conversation but gently guide back to how you can help with coffee-related questions
- Never make up information about coffee products that weren't provided in the context
            """.strip()
        else:
            base_message = """
You are a helpful coffee expert for Cymbal Coffee. Give quick, friendly recommendations and advice.

Keep responses SHORT and conversational - this is a chat interface:
- 1-3 sentences max unless they ask for details
- Be direct and helpful
- Focus on practical recommendations
- No bullet points or long explanations
- Sound natural and friendly like you're talking to a customer at the counter
            """.strip()

        # If a custom message is provided, use it as the base
        if message:
            base_message = message

        # Enhance with persona-specific context
        return PersonaManager.get_system_prompt(persona, base_message)

    async def chat_with_history(
        self,
        query: str,
        context: str = "",
        conversation_history: list[dict] | None = None,
        user_id: str = "default",
        intent: str | None = None,
        persona: str = "enthusiast",
    ) -> tuple[str, bool]:
        """Chat with conversation history and context, returning cache status."""

        # Build prompt with system message, history, and context
        system_msg = self.create_system_message(intent=intent, persona=persona)

        prompt_parts = [system_msg]

        # Add conversation history
        if conversation_history:
            prompt_parts.append("\n# Conversation History:")
            for msg in conversation_history[-10:]:  # Last 10 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"{role.title()}: {content}")

        # Add context if provided
        if context:
            prompt_parts.append(f"\n# Context:\n{context}")

        # Add current query
        prompt_parts.append(f"\n# Current Query:\n{query}")

        prompt = "\n".join(prompt_parts)

        # Get temperature from persona
        temperature = PersonaManager.get_temperature(persona)

        # Create a cache key based on query, context, and persona instead of full prompt
        # This allows caching responses for similar queries with same context/persona
        # but avoids false cache hits from different conversation histories
        cache_key = f"{query}|{context}|{intent}|{persona}"

        # TEMP DEBUG: Check for cache key collisions
        logger.info(
            "cache_key_debug",
            cache_key=cache_key,
            query=query,
            context_len=len(context),
            intent=intent,
            persona=persona,
        )

        return await self.generate_content_with_cache_key(prompt, cache_key, user_id, temperature=temperature)


class OracleVectorSearchService:
    """Oracle vector search without LangChain."""

    def __init__(
        self,
        products_service: Any,
        vertex_ai_service: VertexAIService,
        embedding_cache: EmbeddingCache | None = None,
    ) -> None:
        self.products_service = products_service
        self.vertex_ai_service = vertex_ai_service
        self.embedding_cache = embedding_cache

    async def similarity_search(self, query: str, k: int = 4) -> tuple[list[dict], bool, dict]:
        """Perform Oracle vector similarity search.

        Returns:
            - list of matched products
            - boolean indicating embedding cache hit
            - dict with timing data: {"embedding_ms": float, "oracle_ms": float, "total_ms": float}
        """
        start_time = time.time()

        try:
            # Create embedding for query (with caching if available)
            embedding_start = time.time()

            embedding_cache_hit = False
            if self.embedding_cache:
                logger.debug("product_search_using_cache", query=query[:50])
                query_embedding, embedding_cache_hit = await self.embedding_cache.get_embedding(
                    query, self.vertex_ai_service
                )
            else:
                logger.debug("product_search_no_cache", query=query[:50])
                query_embedding = await self.vertex_ai_service.create_embedding(query)

            embedding_time = (time.time() - embedding_start) * 1000

            # Perform Oracle vector search
            oracle_start = time.time()

            # Convert embedding to Oracle VECTOR format

            # Convert to float32 array for Oracle VECTOR
            vector_array = array.array("f", query_embedding)

            # Execute search using raw Oracle SQL
            async with self.products_service.get_cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT p.id, p.name, p.description,
                           VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) as distance
                    FROM product p
                    WHERE p.embedding IS NOT NULL
                    ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
                    FETCH FIRST :limit ROWS ONLY
                    """,
                    {
                        "query_vector": vector_array,
                        "limit": k,
                    },
                )

                oracle_time = (time.time() - oracle_start) * 1000

                # Format results
                products = [
                    {
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "distance": row[3],
                        "metadata": {"id": row[0]},
                    }
                    async for row in cursor
                ]

            # Calculate total time and return timing data
            total_time = (time.time() - start_time) * 1000
            timing_data = {
                "embedding_ms": embedding_time,
                "oracle_ms": oracle_time,
                "total_ms": total_time,
            }

        except (KeyError, AttributeError) as e:
            # Return empty results on error, but log it
            logger.exception("Vector search error", error=str(e))
            return [], False, {"embedding_ms": 0, "oracle_ms": 0, "total_ms": 0}
        else:
            return products, embedding_cache_hit, timing_data
