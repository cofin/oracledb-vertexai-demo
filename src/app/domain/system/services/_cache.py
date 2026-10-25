# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Response and embedding cache persistence service."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlspec import sql

from app.domain.system.schemas import CacheStats, CacheStatsRow, EmbeddingCache, ResponseCache
from app.lib.service import OracleLoaderService
from app.utils.serialization import encode_json

__all__ = ("CacheService",)


class CacheService(OracleLoaderService):
    """Handles database operations for response and embedding cache."""

    __slots__ = ()

    async def get_cached_response(self, cache_key: str) -> ResponseCache | None:
        """Fetch an unexpired cached response row by ``cache_key``."""
        return await self.driver.select_one_or_none(
            self.get_sql("get-cached-response"), key=cache_key, schema_type=ResponseCache
        )

    async def delete_expired_responses(self) -> int:
        """Delete expired response-cache rows.

        Returns:
            Number of expired response-cache rows deleted.
        """
        res = await self.driver.execute(
            sql.delete().from_("response_cache").where("expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP")
        )
        await self.driver.commit()
        return res.rows_affected

    async def delete_stale_agent_sessions(self, retention_days: int = 7) -> int:
        """Delete stale ``agent_session`` rows older than ``retention_days``.

        Args:
            retention_days: Retention window in days before an idle session is pruned.

        Returns:
            Number of ``agent_session`` rows deleted.
        """
        res = await self.driver.execute(
            self.get_sql("delete-stale-agent-sessions"), retention_days=max(1, retention_days)
        )
        await self.driver.commit()
        return res.rows_affected

    async def set_cached_response(
        self, cache_key: str, response_data: dict[str, Any], ttl_minutes: int = 60
    ) -> ResponseCache | None:
        """Atomically upsert a cached response payload with an expiration window in minutes."""
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
        await self.driver.execute(
            self.get_sql("upsert-response-cache"),
            cache_key=cache_key,
            response_data=encode_json(response_data),
            expires_at=expires_at,
        )
        await self.driver.commit()
        return await self.get_cached_response(cache_key)

    async def get_embedding(self, text: str, model: str) -> list[float] | None:
        """Retrieve a cached embedding vector and increment its hit counter."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        cached = await self.driver.select_one_or_none(
            self.get_sql("get-cached-embedding"), hash=text_hash, model=model, schema_type=EmbeddingCache
        )
        if cached is None:
            return None
        await self.driver.execute(
            sql
            .update("embedding_cache")
            .set(hit_count=sql.raw("hit_count + 1"), last_accessed=sql.raw("CURRENT_TIMESTAMP"))
            .where_eq("text_hash", text_hash)
            .where_eq("model", model)
        )
        await self.driver.commit()
        return cached.embedding

    async def save_embedding(self, text: str, embedding: list[float], model: str) -> None:
        """Atomically upsert a text embedding vector into ``embedding_cache``."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        await self.driver.execute(
            self.get_sql("upsert-embedding-cache"), text_hash=text_hash, embedding=embedding, model=model
        )
        await self.driver.commit()

    async def get_cache_stats(self) -> CacheStats:
        """Compute embedding cache entry count, total hits, and estimated hit rate."""
        row = await self.driver.select_one_or_none(self.get_sql("get-cache-stats"), schema_type=CacheStatsRow)
        total_hits = row.total_hits if row else 0
        return CacheStats(
            total_hits=total_hits,
            total_entries=row.total_entries if row else 0,
            cache_hit_rate=(total_hits / (total_hits + 100)) * 100,
        )

    async def invalidate_cache(self, cache_type: str | None = None) -> int:
        """Clear cache tables.

        Returns:
            Number of rows deleted across the targeted cache tables.
        """
        total_deleted = 0
        if cache_type in {None, "response"}:
            res = await self.driver.execute(sql.delete().from_("response_cache"))
            total_deleted += res.rows_affected
        if cache_type in {None, "embedding"}:
            res = await self.driver.execute(sql.delete().from_("embedding_cache"))
            total_deleted += res.rows_affected
        await self.driver.commit()
        return total_deleted
