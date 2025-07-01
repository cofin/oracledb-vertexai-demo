from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.repositories.response_cache import ResponseCacheRepository
    from app.schemas import ResponseCacheDTO


class ResponseCacheService:
    """Oracle response caching using a repository."""

    def __init__(self, response_cache_repository: ResponseCacheRepository):
        """Initialize with response cache repository."""
        self.repository = response_cache_repository

    def _generate_cache_key(self, query: str, user_id: str = "default") -> str:
        """Generate deterministic cache key."""
        content = f"{query.strip()}:{user_id}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def get_cached_response(self, query: str, user_id: str = "default") -> dict | None:
        """Get cached response if not expired."""
        from datetime import UTC, datetime
        cache_key = self._generate_cache_key(query, user_id)
        cached = await self.repository.get_by_key(cache_key)
        if cached and cached.expires_at.replace(tzinfo=UTC) > datetime.now(UTC):
            return cached.response
        return None

    async def cache_response(
        self,
        query: str,
        response: dict,
        ttl_minutes: int = 5,
        user_id: str = "default",
    ) -> ResponseCacheDTO:
        """Cache response with TTL."""
        cache_key = self._generate_cache_key(query, user_id)
        return await self.repository.create_or_update(cache_key, query, response, ttl_minutes)

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        return await self.repository.cleanup_expired()

    async def get_cache_stats(self, hours: int = 24) -> dict:
        """Get cache hit rate and statistics."""
        # This logic would need to be implemented in the repository
        # if it were to be used.
        return {
            "cache_hit_rate": 0.0,
            "total_cached_queries": 0,
            "total_cache_hits": 0,
            "avg_hits_per_entry": 0.0,
        }
