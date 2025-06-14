"""Oracle-based cache for embedding vectors using response_cache table."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import msgspec
import structlog

if TYPE_CHECKING:
    import oracledb

    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class EmbeddingCacheEntry(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Cache entry for embeddings."""

    embedding: list[float]
    query: str
    created_at: str


class EmbeddingCache:
    """Oracle-based cache for embedding vectors using response_cache table."""

    def __init__(self, connection: oracledb.AsyncConnection, ttl_hours: int = 24) -> None:
        """Initialize with Oracle connection.

        Args:
            connection: Oracle database connection
            ttl_hours: Time to live for cache entries in hours
        """
        self.connection = connection
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

    async def get_embedding(self, query: str, vertex_ai_service: VertexAIService) -> list[float]:
        """Get embedding with caching.

        Args:
            query: The text query to get embedding for
            vertex_ai_service: Vertex AI service for generating embeddings

        Returns:
            The embedding vector
        """
        # Normalize query
        normalized = self._normalize_query(query)

        # Try memory cache first
        cached = self._get_from_memory(normalized)
        if cached is not None:
            logger.debug("embedding_cache_hit", layer="memory", query=query[:50])
            return cached

        # Try Oracle cache
        cache_key = self._cache_key(query)
        cursor = self.connection.cursor()
        try:
            # Check cache with non-expired entries
            await cursor.execute(
                """
                SELECT response
                FROM response_cache
                WHERE cache_key = :cache_key
                  AND expires_at > CURRENT_TIMESTAMP
            """,
                {"cache_key": cache_key},
            )

            result = await cursor.fetchone()
            if result:
                # Update hit count
                await cursor.execute(
                    """
                    UPDATE response_cache
                    SET hit_count = hit_count + 1
                    WHERE cache_key = :cache_key
                """,
                    {"cache_key": cache_key},
                )
                await self.connection.commit()

                # Decode the cached entry
                cache_entry = msgspec.json.decode(result[0], type=EmbeddingCacheEntry)
                embedding = cache_entry.embedding

                # Store in memory cache
                self._set_in_memory(normalized, embedding)
                logger.debug("embedding_cache_hit", layer="oracle", query=query[:50])
                return embedding

        except Exception as e:  # noqa: BLE001
            logger.warning("oracle_cache_read_error", error=str(e))
        finally:
            cursor.close()

        # Compute embedding
        logger.debug("embedding_cache_miss", query=query[:50])
        embedding = await vertex_ai_service.create_embedding(query)

        # Store in memory cache
        self._set_in_memory(normalized, embedding)

        # Store in Oracle cache
        await self._store_in_oracle(cache_key, query, embedding)

        return embedding

    async def _store_in_oracle(self, cache_key: str, query: str, embedding: list[float]) -> None:
        """Store embedding in Oracle cache."""
        cursor = self.connection.cursor()
        try:
            # Create cache entry
            cache_entry = EmbeddingCacheEntry(
                embedding=embedding, query=query, created_at=datetime.now(UTC).isoformat()
            )

            # Calculate expiration
            expires_at = datetime.now(UTC) + timedelta(hours=self.ttl_hours)

            # Encode to JSON using msgspec
            response_json = msgspec.json.encode(cache_entry).decode("utf-8")

            # Upsert into cache
            await cursor.execute(
                """
                MERGE INTO response_cache rc
                USING (SELECT :cache_key AS cache_key FROM dual) src
                ON (rc.cache_key = src.cache_key)
                WHEN MATCHED THEN
                    UPDATE SET
                        query_text = :query_text,
                        response = :response,
                        expires_at = :expires_at,
                        hit_count = 0
                WHEN NOT MATCHED THEN
                    INSERT (cache_key, query_text, response, expires_at, hit_count)
                    VALUES (:cache_key2, :query_text2, :response2, :expires_at2, 0)
            """,
                {
                    "cache_key": cache_key,
                    "cache_key2": cache_key,
                    "query_text": query,
                    "query_text2": query,
                    "response": response_json,
                    "response2": response_json,
                    "expires_at": expires_at,
                    "expires_at2": expires_at,
                },
            )

            await self.connection.commit()

        except Exception as e:  # noqa: BLE001
            logger.warning("oracle_cache_write_error", error=str(e))
        finally:
            cursor.close()

    async def clear_expired(self) -> int:
        """Clear expired cache entries.

        Returns:
            Number of entries cleared
        """
        cursor = self.connection.cursor()
        try:
            await cursor.execute("""
                DELETE FROM response_cache
                WHERE cache_key LIKE 'embedding:%'
                  AND expires_at < CURRENT_TIMESTAMP
            """)

            deleted = cursor.rowcount
            await self.connection.commit()

            logger.info("cache_cleanup", deleted=deleted)
            return deleted

        finally:
            cursor.close()
