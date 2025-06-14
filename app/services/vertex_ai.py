"""Native Vertex AI service without LangChain."""

from __future__ import annotations

import array
import time
import uuid
from typing import TYPE_CHECKING, Any, cast

import structlog
import vertexai
from google.api_core import exceptions as google_exceptions
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel

from app.lib.settings import get_settings
from app.schemas import SearchMetricsCreate

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

        # Initialize Vertex AI
        vertexai.init(
            project=settings.app.GOOGLE_PROJECT_ID,
            location="us-central1",
        )

        # Initialize models from settings
        self.model_name = settings.app.GEMINI_MODEL
        self.embedding_model = settings.app.EMBEDDING_MODEL

        # Initialize the model
        self.model = GenerativeModel(self.model_name)
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
        # Extract just the model name from the full path
        active_model_full = self.model._model_name  # noqa: SLF001
        active_model_name = active_model_full.split("/")[-1] if "/" in active_model_full else active_model_full

        return {
            "active_model": active_model_name,
            "active_model_full": active_model_full,
            "configured_model": self.model_name,
            "embedding_model": self.embedding_model,
        }

    async def generate_content(
        self,
        prompt: str,
        user_id: str = "default",
        use_cache: bool = True,
    ) -> str:
        """Generate content with Oracle caching."""

        # Try cache first
        if use_cache and self.cache_service:
            cached = await self.cache_service.get_cached_response(prompt, user_id)
            if cached:
                content = cached.get("content", "")
                return str(content)

        # Record timing
        start_time = time.time()

        try:
            response = await self.model.generate_content_async(prompt)
            content = response.text

            # Cache successful response
            if use_cache and self.cache_service:
                await self.cache_service.cache_response(
                    prompt,
                    {"content": content, "model": self.model_name},
                    ttl_minutes=5,
                    user_id=user_id,
                )

        except google_exceptions.GoogleAPIError as e:
            # Handle API errors gracefully
            return f"I apologize, but I'm experiencing technical difficulties. Please try again. Error: {e!s}"
        else:
            return cast("str", content)

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
    ) -> AsyncGenerator[str, None]:
        """Stream content generation."""
        try:
            response = await self.model.generate_content_async(
                prompt,
                stream=True,
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except google_exceptions.GoogleAPIError as e:
            yield f"Error: {e!s}"

    async def create_embedding(self, text: str) -> list[float]:
        """Create embeddings using Vertex AI."""
        try:
            # Use the native Vertex AI embedding model

            model = TextEmbeddingModel.from_pretrained(self.embedding_model)
            embeddings = await model.get_embeddings_async([text])

            if embeddings and len(embeddings) > 0:
                return cast("list[float]", embeddings[0].values)
            # Fallback to mock embedding for development

        except Exception:
            # Log the error and fallback to mock embedding
            logger.exception("Embedding generation failed, using fallback")
            return [0.0] * 768  # Standard embedding dimension
        else:
            return [0.0] * 768

    def create_system_message(self, message: str | None = None, intent: str | None = None) -> str:
        """Create system message based on detected intent."""
        if intent == "GENERAL_CONVERSATION":
            default_message = """
You are a friendly AI assistant for Cymbal Coffee. While you specialize in coffee, you can also help with general conversation.

For general queries or greetings:
- Be friendly and conversational
- If asked about topics unrelated to coffee, politely acknowledge that your expertise is in coffee
- You can engage in light conversation but gently guide back to how you can help with coffee-related questions
- Never make up information about coffee products that weren't provided in the context

Keep your responses concise, friendly, and honest.
            """.strip()
        else:
            default_message = """
You are a helpful AI assistant specializing in coffee recommendations for Cymbal Coffee Connoisseur.
Given a user's chat history, the latest user query, and relevant context about our products, provide an engaging and informative response.

Focus on:
- Product recommendations based on user preferences
- Detailed descriptions of coffee varieties and flavors
- Helping users discover new coffee experiences
- Answering questions about coffee preparation and brewing methods

Keep your responses concise and conversational.

Format your responses for a chat interface:
- Use plain text without markdown formatting
- Keep responses natural and conversational
- Use regular punctuation and spacing
- Avoid bullet points or special formatting - write in flowing sentences
            """.strip()

        return message or default_message

    async def chat_with_history(
        self,
        query: str,
        context: str = "",
        conversation_history: list[dict] | None = None,
        user_id: str = "default",
        intent: str | None = None,
    ) -> str:
        """Chat with conversation history and context."""

        # Build prompt with system message, history, and context
        system_msg = self.create_system_message(intent=intent)

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

        return await self.generate_content(prompt, user_id)


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

    async def similarity_search(self, query: str, k: int = 4) -> list[dict]:
        """Perform Oracle vector similarity search."""
        start_time = time.time()

        try:
            # Create embedding for query (with caching if available)
            embedding_start = time.time()

            if self.embedding_cache:
                logger.debug("product_search_using_cache", query=query[:50])
                query_embedding = await self.embedding_cache.get_embedding(query, self.vertex_ai_service)
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
            cursor = self.products_service.connection.cursor()
            try:
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
            finally:
                cursor.close()

            # Record metrics
            if self.vertex_ai_service.metrics_service:
                total_time = (time.time() - start_time) * 1000
                await self.vertex_ai_service.metrics_service.record_search(
                    SearchMetricsCreate(
                        query_id=str(uuid.uuid4()),
                        search_time_ms=total_time,
                        embedding_time_ms=embedding_time,
                        oracle_time_ms=oracle_time,
                        similarity_score=1.0 - (products[0]["distance"] if products else 1.0),
                        result_count=len(products),
                    ),
                )

        except (KeyError, AttributeError) as e:
            # Return empty results on error, but log it
            logger.exception("Vector search error", error=str(e))
            return []
        else:
            return products
