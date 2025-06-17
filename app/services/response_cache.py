# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Response cache service using raw Oracle SQL."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import msgspec

from app.services.base import BaseService


class ResponseCacheService(BaseService):
    """Oracle response caching using raw SQL."""

    def _generate_cache_key(self, query: str, user_id: str = "default") -> str:
        """Generate deterministic cache key."""
        content = f"{query.strip()}:{user_id}"
        return hashlib.sha256(content.encode()).hexdigest()  # Use SHA256 instead of MD5

    async def get_cached_response(self, query: str, user_id: str = "default") -> dict | None:
        """Get cached response if not expired."""
        cache_key = self._generate_cache_key(query, user_id)
        now = datetime.now(UTC)

        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, response, expires_at, hit_count
                FROM response_cache
                WHERE cache_key = :cache_key
                """,
                {"cache_key": cache_key},
            )

            row = await cursor.fetchone()
            if row:
                # Oracle TIMESTAMP WITH TIME ZONE might come back as naive datetime
                expires_at = row[2]
                if expires_at.tzinfo is None:
                    # Assume UTC if timezone is missing
                    expires_at = expires_at.replace(tzinfo=UTC)

                if expires_at > now:  # expires_at > now
                    # Increment hit count
                    await cursor.execute(
                        """
                        UPDATE response_cache
                        SET hit_count = hit_count + 1
                        WHERE id = :id
                        """,
                        {"id": row[0]},
                    )
                    await self.connection.commit()

                    return row[1] if isinstance(row[1], dict) else msgspec.json.decode(row[1]) if row[1] else {}
            return None

    async def cache_response(
        self,
        query: str,
        response: dict,
        ttl_minutes: int = 5,
        user_id: str = "default",
    ) -> dict[str, Any]:
        """Cache response with TTL."""
        cache_key = self._generate_cache_key(query, user_id)
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
        response_json = msgspec.json.encode(response).decode("utf-8") if isinstance(response, dict) else response
        async with self.get_cursor() as cursor:
            # Use MERGE for upsert
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

            # Return the cache entry
            await cursor.execute(
                """
                SELECT
                    id,
                    cache_key,
                    query_text,
                    response,
                    expires_at,
                    hit_count,
                    created_at,
                    updated_at
                FROM response_cache
                WHERE cache_key = :cache_key
                """,
                {"cache_key": cache_key},
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "cache_key": row[1],
                    "query_text": row[2],
                    "response": row[3] if isinstance(row[3], dict) else msgspec.json.decode(row[3]) if row[3] else {},
                    "expires_at": row[4],
                    "hit_count": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                }

            msg = "Failed to create cache entry"
            raise RuntimeError(msg)

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        now = datetime.now(UTC)
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                DELETE FROM response_cache
                WHERE expires_at < :now
                """,
                {"now": now},
            )
            await self.connection.commit()
            return cursor.rowcount

    async def get_cache_stats(self, hours: int = 24) -> dict:
        """Get cache hit rate and statistics."""
        since = datetime.now(UTC) - timedelta(hours=hours)

        async with self.get_cursor() as cursor:
            # Get total cache hits and entries
            await cursor.execute(
                """
                SELECT
                    COUNT(*) as total_entries,
                    SUM(hit_count) as total_hits,
                    AVG(hit_count) as avg_hits_per_entry
                FROM response_cache
                WHERE created_at > :since
                """,
                {"since": since},
            )

            row = await cursor.fetchone()
            total_entries = row[0] or 0
            total_hits = row[1] or 0

            # Calculate hit rate
            # Hit rate = hits / (hits + misses)
            # Where misses = entries (each entry represents at least one miss)
            total_requests = total_entries + total_hits
            hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "cache_hit_rate": round(hit_rate, 1),
                "total_cached_queries": total_entries,
                "total_cache_hits": int(total_hits),
                "avg_hits_per_entry": round(row[2] or 0, 1),
            }
