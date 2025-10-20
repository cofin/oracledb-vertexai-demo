# ruff: noqa: TC001
"""Vertex AI integration service for embeddings and chat."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, overload

import structlog
from google import genai
from google.auth import default as google_auth_default

from app.lib.settings import get_settings
from app.services.cache import CacheService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


logger = structlog.get_logger()


class VertexAIService:
    """Vertex AI service for embeddings and chat completions."""

    def __init__(self, cache_service: CacheService | None = None) -> None:
        """Initialize Vertex AI service.

        Args:
            cache_service: Optional cache service for embedding caching
        """
        from google import genai
        from google.cloud import aiplatform

        self.settings = get_settings()
        self._genai_client: genai.Client | None = None
        self._cache_service: CacheService | None = cache_service

        # Initialize Vertex AI
        if self.settings.vertex_ai.PROJECT_ID:
            aiplatform.init(
                project=self.settings.vertex_ai.PROJECT_ID,
                location=self.settings.vertex_ai.LOCATION,
            )
            credentials, _ = google_auth_default(scopes=["https://www.googleapis.com/auth/cloud-platform"])

            if self.settings.vertex_ai.API_KEY:
                logger.warning(
                    "API key provided but Vertex AI requires ADC/service account credentials; ignoring api_key",
                )

            self._genai_client = genai.Client(
                vertexai=True,
                project=self.settings.vertex_ai.PROJECT_ID,
                location=self.settings.vertex_ai.LOCATION,
                credentials=credentials,
            )
            logger.info(
                "Vertex AI initialized",
                project=self.settings.vertex_ai.PROJECT_ID,
                location=self.settings.vertex_ai.LOCATION,
                embedding_model=self.settings.vertex_ai.EMBEDDING_MODEL,
                chat_model=self.settings.vertex_ai.CHAT_MODEL,
            )
        else:
            api_key = self.settings.vertex_ai.API_KEY
            if api_key:
                self._genai_client = genai.Client(api_key=api_key)
                logger.info("Google AI client initialized using API key")
            else:
                self._genai_client = None
                logger.warning("Vertex AI not initialized: PROJECT_ID not configured and no API key provided")

    async def _get_batch_text_embeddings(self, texts: list[str], model_name: str) -> list[list[float]]:
        """Handle batch embedding generation with rate limiting."""
        if not texts:
            return []

        if not self._genai_client:
            msg = "GenAI client not initialized"
            raise RuntimeError(msg)

        batch_size = 5
        embeddings = []

        for i in range(0, len(texts), batch_size):
            if i > 0:
                await asyncio.sleep(1)  # Rate limiting

            batch = texts[i : i + batch_size]
            response = await self._genai_client.aio.models.embed_content(model=model_name, contents=batch)

            if not response.embeddings:
                msg = f"No embeddings returned from Vertex AI for batch starting at index {i}"
                raise ValueError(msg)

            batch_embeddings = [list(e.values) for e in response.embeddings if e.values is not None]
            embeddings.extend(batch_embeddings)

        return embeddings

    @overload
    async def get_text_embedding(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]: ...

    @overload
    async def get_text_embedding(
        self,
        text: str,
        model: str | None = None,
        *,
        return_cache_status: bool = True,
    ) -> tuple[list[float], bool]: ...

    @overload
    async def get_text_embedding(
        self,
        text: list[str],
        model: str | None = None,
    ) -> list[list[float]]: ...

    async def get_text_embedding(
        self,
        text: str | list[str],
        model: str | None = None,
        *,
        return_cache_status: bool = False,
    ) -> list[float] | list[list[float]] | tuple[list[float], bool]:
        """Generate text embedding(s) using Vertex AI with optional cache status.

        Args:
            text: Text or list of texts to embed
            model: Optional model override
            return_cache_status: If True, return (embedding, cache_hit) tuple for single text

        Returns:
            - For single text without cache status: embedding vector
            - For single text with cache status: (embedding vector, cache_hit)
            - For batch text: list of embedding vectors

        Raises:
            RuntimeError: If Vertex AI not initialized
            ValueError: If embedding generation fails or cache status requested for batch
        """
        if not self._genai_client:
            msg = "Vertex AI not initialized"
            raise RuntimeError(msg)

        model_name = model or self.settings.vertex_ai.EMBEDDING_MODEL

        # Handle batch embeddings
        if isinstance(text, list):
            if return_cache_status:
                msg = "Cache status not supported for batch embeddings"
                raise ValueError(msg)
            return await self._get_batch_text_embeddings(text, model_name)

        # Single text embedding with optional cache tracking
        cache_hit = False

        try:
            # Check cache first if available
            if self._cache_service and self.settings.cache.EMBEDDING_CACHE_ENABLED:
                cached = await self._cache_service.get_cached_embedding(text, model_name)
                if cached:
                    if return_cache_status:
                        return cached.embedding, True
                    return cached.embedding

            # Generate new embedding
            embedding = await self._get_embedding_async(text, model_name)

            # Cache the result if cache service is available
            if self._cache_service and self.settings.cache.EMBEDDING_CACHE_ENABLED:
                try:
                    await self._cache_service.set_cached_embedding(text, embedding, model_name)
                except Exception as e:  # noqa: BLE001
                    logger.warning("Failed to cache embedding", error=str(e))

        except Exception as e:
            logger.exception("Failed to generate embedding", model=model_name, error=str(e))
            msg = f"Failed to generate embedding: {e}"
            raise ValueError(msg) from e

        if return_cache_status:
            return embedding, cache_hit
        return embedding

    async def generate_chat_response_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming chat response using Vertex AI.

        Args:
            messages: List of chat messages with 'role' and 'content'
            model: Optional model override
            temperature: Response temperature (0.0-1.0)
            max_output_tokens: Maximum response tokens

        Yields:
            Text chunks from the streaming response

        Raises:
            RuntimeError: If Vertex AI not initialized
            ValueError: If streaming fails
        """
        if not self._genai_client:
            msg = "Vertex AI not initialized"
            raise RuntimeError(msg)

        model_name = model or self.settings.vertex_ai.CHAT_MODEL

        try:
            async for chunk in self._generate_chat_response_stream_async(
                messages,
                model_name,
                temperature,
                max_output_tokens,
            ):
                yield chunk

        except Exception as e:
            logger.exception(
                "Failed to generate streaming chat response",
                message_count=len(messages),
                model=model_name,
                error=str(e),
            )
            msg = f"Failed to generate streaming chat response: {e}"
            raise ValueError(msg) from e

    async def _generate_chat_response_stream_async(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_output_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Asynchronous streaming chat response generation using Google GenAI SDK."""
        if not self._genai_client:
            msg = "GenAI client not initialized"
            raise RuntimeError(msg)

        # Convert messages to Google GenAI format
        formatted_messages = []
        for message in messages:
            role = "user" if message["role"] == "user" else "model"
            formatted_messages.append({"role": role, "parts": [{"text": message["content"]}]})

        # Generate streaming response using Google GenAI SDK
        async for chunk in await self._genai_client.aio.models.generate_content_stream(
            model=model,
            contents=formatted_messages,
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        ):
            # Extract text from chunk
            if chunk.candidates:
                candidate = chunk.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.text:
                            yield part.text

    async def _get_embedding_async(self, text: str, model: str) -> list[float]:
        """Asynchronous embedding generation using Google GenAI SDK."""
        if not self._genai_client:
            msg = "GenAI client not initialized"
            raise RuntimeError(msg)

        response = await self._genai_client.aio.models.embed_content(
            model=model,
            contents=text,
        )
        if not response.embeddings or len(response.embeddings) == 0:
            msg = "No embeddings returned from API"
            raise ValueError(msg)

        # At this point response.embeddings is guaranteed to exist and have at least one element
        first_embedding = response.embeddings[0]
        embedding_values = first_embedding.values
        if embedding_values is None:
            msg = "No embeddings returned from API"
            raise ValueError(msg)

        # At this point embedding_values is guaranteed to be not None
        return list(embedding_values)

    @property
    def is_initialized(self) -> bool:
        """Check if Vertex AI is initialized."""
        return self._genai_client is not None

    def get_embedding_dimensions(self) -> int:
        """Get embedding dimensions for current model."""
        return self.settings.vertex_ai.EMBEDDING_DIMENSIONS


class OracleVectorSearchService:
    """Oracle vector search service using SQLSpec driver patterns.

    This service provides vector similarity search functionality for Oracle Database 23ai
    using the VECTOR_DISTANCE function with proper embedding caching.
    """

    def __init__(
        self,
        products_service: Any,
        vertex_ai_service: VertexAIService,
        embedding_cache: CacheService | None = None,
    ) -> None:
        """Initialize Oracle vector search service.

        Args:
            products_service: Product service for database operations
            vertex_ai_service: Vertex AI service for embedding generation
            embedding_cache: Optional cache service for embeddings
        """
        self.products_service = products_service
        self.vertex_ai_service = vertex_ai_service
        self.embedding_cache = embedding_cache

    async def similarity_search(self, query: str, k: int = 4) -> tuple[list[dict[str, Any]], bool, dict[str, float]]:
        """Perform Oracle vector similarity search.

        Args:
            query: Search query text
            k: Number of results to return

        Returns:
            Tuple of (matched products, embedding_cache_hit, timing_data)
        """
        import time

        start_time = time.time()

        try:
            # Create embedding for query (with caching if available)
            embedding_start = time.time()

            embedding_cache_hit = False
            if self.embedding_cache:
                logger.debug("product_search_using_cache", query=query[:50])
                # Try to get from cache
                cached = await self.embedding_cache.get_cached_embedding(
                    query, self.vertex_ai_service.settings.vertex_ai.EMBEDDING_MODEL
                )
                if cached:
                    query_embedding = cached.embedding
                    embedding_cache_hit = True
                else:
                    query_embedding = await self.vertex_ai_service.get_text_embedding(query)
                    # Cache it
                    await self.embedding_cache.set_cached_embedding(
                        query, query_embedding, self.vertex_ai_service.settings.vertex_ai.EMBEDDING_MODEL
                    )
            else:
                logger.debug("product_search_no_cache", query=query[:50])
                query_embedding = await self.vertex_ai_service.get_text_embedding(query)

            embedding_time = (time.time() - embedding_start) * 1000

            # Perform Oracle vector search
            oracle_start = time.time()

            # Execute search using SQLSpec driver - automatic vector conversion
            products = await self.products_service.driver.select(
                """
                SELECT
                    p.id AS "id",
                    p.name AS "name",
                    p.description AS "description",
                    VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) AS "distance"
                FROM product p
                WHERE p.embedding IS NOT NULL
                ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
                FETCH FIRST :limit ROWS ONLY
                """,
                query_vector=query_embedding,  # SQLSpec handles vector conversion automatically
                limit=k,
            )

            oracle_time = (time.time() - oracle_start) * 1000

            # Format results - driver returns dicts, add metadata field
            formatted_products = [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "distance": row["distance"],
                    "metadata": {"id": row["id"]},
                }
                for row in products
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
            return [], False, {"embedding_ms": 0.0, "oracle_ms": 0.0, "total_ms": 0.0}
        else:
            return formatted_products, embedding_cache_hit, timing_data
