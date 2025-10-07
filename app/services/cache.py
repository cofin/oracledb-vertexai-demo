"""Cache service for managing response and embedding cache."""

from __future__ import annotations

import hashlib
from typing import Any

from app.schemas import EmbeddingCache, ResponseCache
from app.services.base import SQLSpecService


class CacheService(SQLSpecService):
    """Handles database operations for response and embedding cache."""

    async def get_cached_response(self, cache_key: str) -> ResponseCache | None:
        """Get cached response by key.

        Args:
            cache_key: Cache key to lookup

        Returns:
            Cached response or None if not found or expired
        """
        return await self.driver.select_one_or_none(
            """
            SELECT id, cache_key, response_data, expires_at, created_at
            FROM response_cache
            WHERE cache_key = :cache_key
              AND (expires_at IS NULL OR expires_at > SYSTIMESTAMP)
            """,
            cache_key=cache_key,
            schema_type=ResponseCache,
        )

    async def set_cached_response(
        self,
        cache_key: str,
        response_data: dict[str, Any],
        ttl_minutes: int = 5,
    ) -> ResponseCache:
        """Cache a response with TTL using Oracle MERGE.

        Args:
            cache_key: Unique cache key
            response_data: Response data to cache (as JSON)
            ttl_minutes: Time to live in minutes

        Returns:
            Created cache entry
        """
        # Oracle MERGE statement (upsert)
        await self.driver.execute(
            """
            MERGE INTO response_cache rc
            USING (
                SELECT :cache_key AS cache_key,
                       :response_data AS response_data,
                       SYSTIMESTAMP + INTERVAL ':ttl_minutes' MINUTE AS expires_at
                FROM dual
            ) src
            ON (rc.cache_key = src.cache_key)
            WHEN MATCHED THEN
                UPDATE SET
                    rc.response_data = src.response_data,
                    rc.expires_at = src.expires_at,
                    rc.created_at = SYSTIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (cache_key, response_data, expires_at, created_at)
                VALUES (src.cache_key, src.response_data, src.expires_at, SYSTIMESTAMP)
            """,
            cache_key=cache_key,
            response_data=response_data,
            ttl_minutes=ttl_minutes,
        )

        # Fetch the result
        return await self.driver.select_one(
            """
            SELECT id, cache_key, response_data, expires_at, created_at
            FROM response_cache
            WHERE cache_key = :cache_key
            """,
            cache_key=cache_key,
            schema_type=ResponseCache,
        )

    async def get_response_cache_by_id(self, cache_id: int) -> ResponseCache:
        """Get response cache entry by ID.

        Args:
            cache_id: Cache entry ID

        Returns:
            Cache entry

        Raises:
            ValueError: If cache entry not found
        """
        return await self.get_or_404(
            """
            SELECT id, cache_key, response_data, expires_at, created_at
            FROM response_cache
            WHERE id = :cache_id
            """,
            cache_id=cache_id,
            schema_type=ResponseCache,
            error_message=f"Cache entry {cache_id} not found",
        )

    async def get_cached_embedding(self, text: str, model_name: str) -> EmbeddingCache | None:
        """Get cached embedding for text.

        Args:
            text: Text that was embedded
            model_name: Embedding model name

        Returns:
            Cached embedding or None if not found
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        result = await self.driver.select_one_or_none(
            """
            SELECT id, text_hash, embedding, model, hit_count, last_accessed, created_at
            FROM embedding_cache
            WHERE text_hash = :text_hash
              AND model = :model_name
            """,
            text_hash=text_hash,
            model_name=model_name,
            schema_type=EmbeddingCache,
        )

        if result:
            # Update hit count and last accessed
            await self.driver.execute(
                """
                UPDATE embedding_cache
                SET hit_count = hit_count + 1,
                    last_accessed = SYSTIMESTAMP
                WHERE id = :result_id
                """,
                result_id=result.id,
            )

        return result

    async def set_cached_embedding(
        self,
        text: str,
        embedding: list[float],
        model_name: str,
    ) -> EmbeddingCache:
        """Cache an embedding using Oracle MERGE.

        Args:
            text: Text that was embedded
            embedding: The embedding vector
            model_name: Model used for embedding

        Returns:
            Created cache entry
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Oracle MERGE statement
        await self.driver.execute(
            """
            MERGE INTO embedding_cache ec
            USING (
                SELECT :text_hash AS text_hash,
                       :embedding AS embedding,
                       :model_name AS model,
                       1 AS hit_count,
                       SYSTIMESTAMP AS last_accessed
                FROM dual
            ) src
            ON (ec.text_hash = src.text_hash AND ec.model = src.model)
            WHEN MATCHED THEN
                UPDATE SET
                    ec.embedding = src.embedding,
                    ec.hit_count = ec.hit_count + 1,
                    ec.last_accessed = SYSTIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (text_hash, embedding, model, hit_count, last_accessed, created_at)
                VALUES (src.text_hash, src.embedding, src.model, src.hit_count, src.last_accessed, SYSTIMESTAMP)
            """,
            text_hash=text_hash,
            embedding=embedding,
            model_name=model_name,
        )

        # Fetch result WITHOUT embedding to avoid vector serialization issues
        result = await self.driver.select_one(
            """
            SELECT id, text_hash, model, hit_count, last_accessed, created_at
            FROM embedding_cache
            WHERE text_hash = :text_hash AND model = :model_name
            """,
            text_hash=text_hash,
            model_name=model_name,
        )

        # Manually construct the complete object with the embedding we already have
        return EmbeddingCache(
            id=result["id"],
            text_hash=result["text_hash"],
            embedding=embedding,
            model=result["model"],
            hit_count=result["hit_count"],
            last_accessed=result["last_accessed"],
            created_at=result["created_at"],
        )

    async def invalidate_cache(self, cache_type: str | None = None, include_exemplars: bool = False) -> int:
        """Invalidate cache entries.

        Args:
            cache_type: Type of cache to clear ('response', 'embedding', or None for all)
            include_exemplars: Whether to also clear intent exemplar embeddings (slow to regenerate)

        Returns:
            Number of records deleted
        """
        deleted_count = 0

        if cache_type in (None, "response"):
            result = await self.driver.execute("DELETE FROM response_cache")
            deleted_count += result.rows_affected if hasattr(result, 'rows_affected') else 0

        if cache_type in (None, "embedding"):
            result = await self.driver.execute("DELETE FROM embedding_cache")
            deleted_count += result.rows_affected if hasattr(result, 'rows_affected') else 0

        # Only clear exemplars if explicitly requested (expensive to regenerate)
        if include_exemplars:
            result = await self.driver.execute("UPDATE intent_exemplar SET embedding = NULL")
            deleted_count += result.rows_affected if hasattr(result, 'rows_affected') else 0

        return deleted_count

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of records deleted
        """
        result = await self.driver.execute(
            "DELETE FROM response_cache WHERE expires_at IS NOT NULL AND expires_at < SYSTIMESTAMP",
        )
        return result.rows_affected if hasattr(result, 'rows_affected') else 0

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        response_count = await self.driver.select_value("SELECT COUNT(*) FROM response_cache")
        embedding_count = await self.driver.select_value("SELECT COUNT(*) FROM embedding_cache")
        embedding_hits = await self.driver.select_value("SELECT NVL(SUM(hit_count), 0) FROM embedding_cache")

        return {
            "response_cache_entries": response_count,
            "embedding_cache_entries": embedding_count,
            "total_embedding_hits": embedding_hits,
        }

    async def get(self, cache_key: str) -> dict[str, Any] | None:
        """Simple cache get method.

        Args:
            cache_key: Cache key to lookup

        Returns:
            Cached data or None if not found
        """
        cached = await self.get_cached_response(cache_key)
        return cached.response_data if cached else None

    async def set(self, cache_key: str, data: dict[str, Any], ttl: int = 5) -> None:
        """Simple cache set method.

        Args:
            cache_key: Cache key
            data: Data to cache
            ttl: Time to live in minutes
        """
        await self.set_cached_response(cache_key, data, ttl)
