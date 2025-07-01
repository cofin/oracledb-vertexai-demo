from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.db.repositories.embedding_cache import EmbeddingCacheRepository
    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()


class EmbeddingCache:
    """Oracle-based cache for embedding vectors using a repository."""

    def __init__(self, embedding_cache_repository: EmbeddingCacheRepository, ttl_hours: int = 24):
        """Initialize with repository."""
        self.repository = embedding_cache_repository
        self.ttl_hours = ttl_hours
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
        """Get embedding with two-tier caching (memory + Oracle)."""
        normalized = self._normalize_query(query)
        cached = self._get_from_memory(normalized)
        if cached is not None:
            logger.debug("embedding_cache_hit", layer="memory", query=query[:50])
            return cached, True

        cache_key = self._cache_key(query)
        cached_embedding = await self.repository.get_by_key(cache_key)
        if cached_embedding:
            await self.repository.increment_hit_count(cache_key)
            embedding = cached_embedding.embedding
            self._set_in_memory(normalized, embedding)
            logger.debug("embedding_cache_hit", layer="oracle", query=query[:50])
            return embedding, True

        logger.debug("embedding_cache_miss", query=query[:50])
        embedding = await vertex_ai_service.create_embedding(query)
        self._set_in_memory(normalized, embedding)
        await self.repository.create_or_update(cache_key, query, embedding, self.ttl_hours)
        return embedding, False
