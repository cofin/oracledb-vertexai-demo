"""Oracle-based cache for embedding vectors using dedicated embedding_cache table.

This cache is specifically for storing and retrieving vector embeddings generated from text queries.
It's separate from the response_cache which stores complete LLM responses.

Key differences from response_cache:
- Stores raw vector embeddings (768-dimensional float arrays) using Oracle's native VECTOR type
- Used during vector similarity search to avoid re-computing embeddings for the same text
- Optimized for mathematical operations and vector distance calculations
- Has longer TTL (24 hours default) since embeddings are more expensive to generate
- Uses two-tier caching (memory + Oracle) for maximum performance

The response_cache stores:
- Complete LLM responses as JSON
- Short TTL (5 minutes default) for fresher responses
- Text-based queries and their full AI-generated answers

The embedding_cache stores:
- Vector representations of text queries
- Used as input for vector similarity search against products
- Enables fast product matching without regenerating embeddings
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import structlog

from app.services.base import SQLSpecService

if TYPE_CHECKING:
    from sqlspec.adapters.oracledb import OracleAsyncDriver

    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class EmbeddingCache(SQLSpecService):
    """Oracle-based cache for embedding vectors using dedicated embedding_cache table with VECTOR type.

    This service provides efficient caching of vector embeddings to avoid expensive re-computation
    during vector similarity searches. It implements a two-tier cache (memory + Oracle) for optimal
    performance and uses Oracle 23AI's native VECTOR data type for efficient storage and retrieval.

    Cache Flow:
    1. Check in-memory cache first (fastest)
    2. Check Oracle embedding_cache table if memory miss
    3. Generate new embedding via Vertex AI if both miss
    4. Store in both memory and Oracle for future use

    This is distinct from ResponseCacheService which caches complete LLM responses.
    """

    def __init__(self, driver: OracleAsyncDriver, ttl_hours: int = 24) -> None:
        """Initialize with driver.

        Args:
            driver: SQLSpec async driver adapter
            ttl_hours: Time to live for cache entries in hours
        """
        super().__init__(driver)
        self.ttl_hours = ttl_hours
        # Memory cache for current session
        self._memory_cache: dict[str, list[float]] = {}

    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent caching."""
        return query.lower().strip()

    def _cache_key(self, query: str) -> str:
        """Generate cache key for query."""
        normalized = self._normalize_query(query)
        return f"embedding:{hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()}"

    def _get_from_memory(self, normalized_query: str) -> list[float] | None:
        """Memory cache layer for current session."""
        return self._memory_cache.get(normalized_query)

    def _set_in_memory(self, normalized_query: str, embedding: list[float]) -> None:
        """Store in memory cache."""
        self._memory_cache[normalized_query] = embedding

    async def get_embedding(self, query: str, vertex_ai_service: VertexAIService) -> tuple[list[float], bool]:
        """Get embedding with two-tier caching (memory + Oracle).

        This method implements the core caching logic for embeddings used in vector similarity search.
        It first checks the in-memory cache, then the Oracle embedding_cache table, and finally
        generates a new embedding via Vertex AI if needed.

        Args:
            query: The text query to get embedding for (normalized internally)
            vertex_ai_service: Vertex AI service for generating embeddings if cache miss

        Returns:
            Tuple of (embedding vector, cache_hit_flag) where:
            - embedding vector: The 768-dimensional embedding as a list of floats
            - cache_hit_flag: True if found in cache, False if generated new

        Cache Strategy:
        - Memory cache: Fastest lookup for current session
        - Oracle cache: Persistent across sessions, uses native VECTOR type
        - Vertex AI: Fallback for cache misses, most expensive operation
        """
        # Normalize query
        normalized = self._normalize_query(query)

        # Try memory cache first
        cached = self._get_from_memory(normalized)
        if cached is not None:
            logger.debug("embedding_cache_hit", layer="memory", query=query[:50])
            return cached, True

        # Try Oracle cache
        cache_key = self._cache_key(query)
        try:
            # Check cache with non-expired entries
            result = await self.driver.select_one_or_none(
                """
                SELECT embedding
                FROM embedding_cache
                WHERE cache_key = :cache_key
                  AND expires_at > CURRENT_TIMESTAMP
                """,
                cache_key=cache_key,
            )

            if result and result["embedding"]:
                # Update hit count
                await self.driver.execute(
                    """
                    UPDATE embedding_cache
                    SET hit_count = hit_count + 1
                    WHERE cache_key = :cache_key
                    """,
                    cache_key=cache_key,
                )

                # SQLSpec handles Oracle VECTOR to Python list conversion automatically
                embedding_vector = result["embedding"]
                embedding = embedding_vector if isinstance(embedding_vector, list) else list(embedding_vector)

                # Store in memory cache
                self._set_in_memory(normalized, embedding)
                logger.debug("embedding_cache_hit", layer="oracle", query=query[:50])
                return embedding, True

        except Exception as e:  # noqa: BLE001
            logger.warning("oracle_cache_read_error", error=str(e))

        # Compute embedding
        logger.debug("embedding_cache_miss", query=query[:50])
        embedding = await vertex_ai_service.create_embedding(query)

        # Store in memory cache
        self._set_in_memory(normalized, embedding)

        # Store in Oracle cache
        await self._store_in_oracle(cache_key, query, embedding)

        return embedding, False

    async def _store_in_oracle(self, cache_key: str, query: str, embedding: list[float]) -> None:
        """Store embedding in Oracle cache using native VECTOR type.

        This method persists the embedding to Oracle's embedding_cache table using the native
        VECTOR(768, FLOAT32) data type for optimal storage and retrieval performance.

        The Oracle VECTOR type enables:
        - Efficient storage of high-dimensional vectors
        - Fast vector distance calculations
        - Native support for similarity operations
        - Optimized memory usage compared to JSON storage

        SQLSpec automatically handles vector conversions - no need for array.array().
        """
        try:
            # Calculate expiration
            expires_at = datetime.now(UTC) + timedelta(hours=self.ttl_hours)

            # Upsert into cache - SQLSpec handles vector conversion automatically
            await self.driver.execute(
                """
                MERGE INTO embedding_cache ec
                USING (SELECT :cache_key AS cache_key FROM dual) src
                ON (ec.cache_key = src.cache_key)
                WHEN MATCHED THEN
                    UPDATE SET
                        query_text = :query_text,
                        embedding = :embedding,
                        expires_at = :expires_at,
                        hit_count = 0
                WHEN NOT MATCHED THEN
                    INSERT (cache_key, query_text, embedding, expires_at, hit_count)
                    VALUES (:cache_key2, :query_text2, :embedding2, :expires_at2, 0)
                """,
                cache_key=cache_key,
                cache_key2=cache_key,
                query_text=query,
                query_text2=query,
                embedding=embedding,
                embedding2=embedding,
                expires_at=expires_at,
                expires_at2=expires_at,
            )

            logger.debug("embedding_cache_stored", cache_key=cache_key[:20], query=query[:50])

        except Exception as e:  # noqa: BLE001
            logger.warning("oracle_cache_write_error", error=str(e))

    async def clear_expired(self) -> int:
        """Clear expired cache entries from Oracle embedding_cache table.

        This maintenance operation removes embeddings that have exceeded their TTL,
        helping to keep the cache size manageable and ensure data freshness.

        Returns:
            Number of embedding cache entries cleared
        """
        rowcount = await self.driver.execute("""
            DELETE FROM embedding_cache
            WHERE expires_at < CURRENT_TIMESTAMP
        """)

        logger.info("embedding_cache_cleanup", deleted=rowcount)
        return rowcount.rows_affected
