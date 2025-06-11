"""Native Vertex AI service without LangChain."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any, cast

import structlog
import vertexai
from google.api_core import exceptions as google_exceptions
from sqlalchemy import text
from vertexai.generative_models import GenerativeModel

from app.schemas import SearchMetricsCreate
from app.lib.settings import get_settings

logger = structlog.get_logger()

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from app.services.account import ResponseCacheService, SearchMetricsService


class VertexAIService:
    """Native Vertex AI service without LangChain."""

    def __init__(self) -> None:
        settings = get_settings()

        # Initialize Vertex AI
        vertexai.init(
            project=settings.app.GOOGLE_PROJECT_ID,
            location="us-central1",
        )

        # Initialize models
        self.model = GenerativeModel("gemini-1.5-flash-002")  # More stable than exp model
        self.embedding_model = "text-embedding-004"

        # Oracle services for metrics and caching
        self.metrics_service: SearchMetricsService | None = None
        self.cache_service: ResponseCacheService | None = None

    def set_services(self, metrics_service: SearchMetricsService, cache_service: ResponseCacheService) -> None:
        """Inject Oracle services."""
        self.metrics_service = metrics_service
        self.cache_service = cache_service

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
                    {"content": content, "model": "gemini-1.5-flash-002"},
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
            from vertexai.language_models import TextEmbeddingModel

            model = TextEmbeddingModel.from_pretrained(self.embedding_model)
            embeddings = await model.get_embeddings_async([text])

            if embeddings and len(embeddings) > 0:
                return cast("list[float]", embeddings[0].values)
            # Fallback to mock embedding for development

        except Exception as e:  # noqa: BLE001
            # Log the error and fallback to mock embedding
            logger.warning("Embedding generation failed, using fallback", error=str(e))
            return [0.0] * 768  # Standard embedding dimension
        else:
            return [0.0] * 768

    def create_system_message(self, message: str | None = None) -> str:
        """Create system message for coffee recommendations."""
        default_message = """
You are a helpful AI assistant specializing in coffee recommendations.
Given a user's chat history and the latest user query and a list of matching coffees from a database, provide an engaging and informative response.
If the user is asking about coffee recommendations and locations, provide the information and finish the response with "the map below displays the locations where you can find the coffee."
If the user is asking a general question or making a statement, respond appropriately without using the database.
Your responses should be as concise as possible.

When providing locations, only provide responses that utilize the count of stores found that match the product selection. The Locations will be provided separately by another component of the user interface.
        """.strip()

        return message or default_message

    async def chat_with_history(
        self,
        query: str,
        context: str = "",
        conversation_history: list[dict] | None = None,
        user_id: str = "default",
    ) -> str:
        """Chat with conversation history and context."""

        # Build prompt with system message, history, and context
        system_msg = self.create_system_message()

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

    def __init__(self, products_service: Any, vertex_ai_service: VertexAIService) -> None:
        self.products_service = products_service
        self.vertex_ai_service = vertex_ai_service

    async def similarity_search(self, query: str, k: int = 4) -> list[dict]:
        """Perform Oracle vector similarity search."""
        start_time = time.time()

        try:
            # Create embedding for query
            embedding_start = time.time()
            query_embedding = await self.vertex_ai_service.create_embedding(query)
            embedding_time = (time.time() - embedding_start) * 1000

            # Perform Oracle vector search
            oracle_start = time.time()

            # Use Oracle VECTOR_DISTANCE function
            # Raw SQL for Oracle vector search
            search_query = text("""
                SELECT p.id, p.name, p.description,
                       VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) as distance
                FROM product p
                WHERE p.embedding IS NOT NULL
                ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
                FETCH FIRST :limit ROWS ONLY
            """)

            # Execute search
            result = await self.products_service.repository.session.execute(
                search_query,
                {
                    "query_vector": query_embedding,
                    "limit": k,
                },
            )

            oracle_time = (time.time() - oracle_start) * 1000

            # Format results
            products = [
                {
                    "id": row.id,
                    "name": row.name,
                    "description": row.description,
                    "distance": row.distance,
                    "metadata": {"id": row.id},
                }
                for row in result
            ]

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
