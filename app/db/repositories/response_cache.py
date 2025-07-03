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
        from datetime import UTC, datetime, timedelta

        import msgspec
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
            raise RuntimeError("Failed to create or update response cache")
        return result

    async def cleanup_expired(self) -> int:
        from datetime import UTC, datetime
        now = datetime.now(UTC)
        query = "DELETE FROM response_cache WHERE expires_at < :now"
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"now": now})
            await self.connection.commit()
            return int(cursor.rowcount)
