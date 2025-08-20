from datetime import UTC, datetime, timedelta

import msgspec
import oracledb

from app.schemas import ResponseCacheDTO

from .base import BaseRepository


class ResponseCacheRepository(BaseRepository[ResponseCacheDTO]):
    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        super().__init__(connection, ResponseCacheDTO)

    async def get_by_key(self, cache_key: str) -> ResponseCacheDTO | None:
        query = "SELECT id, cache_key, query_text, response, expires_at, hit_count, created_at, updated_at FROM response_cache WHERE cache_key = :cache_key"
        return await self.fetch_one(query, {"cache_key": cache_key})

    async def create_or_update(
        self,
        cache_key: str,
        query_text: str,
        response: dict,
        ttl_minutes: int,
    ) -> ResponseCacheDTO:
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
        response_json = msgspec.json.encode(response).decode("utf-8")
        query = """
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
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                {
                    "cache_key": cache_key,
                    "cache_key2": cache_key,
                    "query_text": query_text,
                    "query_text2": query_text,
                    "response": response_json,
                    "response2": response_json,
                    "expires_at": expires_at,
                    "expires_at2": expires_at,
                },
            )
            await self.connection.commit()
        result = await self.get_by_key(cache_key)
        if result is None:
            msg = "Failed to create or update response cache"
            raise RuntimeError(msg)
        return result

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        from datetime import UTC, datetime
        now = datetime.now(UTC)
        query = "DELETE FROM response_cache WHERE expires_at < :now"
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"now": now})
            await self.connection.commit()
            return int(cursor.rowcount)

    async def get_cache_stats(self, hours: int = 24) -> dict:
        """Get cache hit rate and statistics."""
        from datetime import UTC, datetime, timedelta

        since = datetime.now(UTC) - timedelta(hours=hours)
        query = """
            SELECT
                COUNT(*) as total_entries,
                SUM(hit_count) as total_hits,
                AVG(hit_count) as avg_hits_per_entry
            FROM response_cache
            WHERE created_at > :since
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"since": since})
            row = await cursor.fetchone()
            if not row:
                return {
                    "cache_hit_rate": 0.0,
                    "total_cached_queries": 0,
                    "total_cache_hits": 0,
                    "avg_hits_per_entry": 0.0,
                }
            total_entries, total_hits, avg_hits = row
            total_requests = (total_entries or 0) + (total_hits or 0)
            hit_rate = ((total_hits or 0) / total_requests * 100) if total_requests > 0 else 0.0
            return {
                "cache_hit_rate": round(hit_rate, 1),
                "total_cached_queries": total_entries or 0,
                "total_cache_hits": int(total_hits or 0),
                "avg_hits_per_entry": round(avg_hits or 0, 1),
            }
