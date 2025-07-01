from app.schemas import EmbeddingCacheDTO
from .base import BaseRepository

class EmbeddingCacheRepository(BaseRepository[EmbeddingCacheDTO]):
    def __init__(self, connection):
        super().__init__(connection, EmbeddingCacheDTO)

    async def get_by_key(self, cache_key: str) -> EmbeddingCacheDTO | None:
        query = "SELECT id, cache_key, query_text, embedding, expires_at, hit_count, created_at, updated_at FROM embedding_cache WHERE cache_key = :cache_key AND expires_at > CURRENT_TIMESTAMP"
        return await self.fetch_one(query, {"cache_key": cache_key})

    async def create_or_update(
        self,
        cache_key: str,
        query_text: str,
        embedding: list[float],
        ttl_hours: int,
    ) -> EmbeddingCacheDTO:
        import array
        from datetime import datetime, timedelta, UTC
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        embedding_array = array.array("f", embedding)
        query = """
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
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                {
                    "cache_key": cache_key,
                    "cache_key2": cache_key,
                    "query_text": query_text,
                    "query_text2": query_text,
                    "embedding": embedding_array,
                    "embedding2": embedding_array,
                    "expires_at": expires_at,
                    "expires_at2": expires_at,
                },
            )
            await self.connection.commit()
        return await self.get_by_key(cache_key)

    async def increment_hit_count(self, cache_key: str) -> None:
        query = "UPDATE embedding_cache SET hit_count = hit_count + 1 WHERE cache_key = :cache_key"
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"cache_key": cache_key})
            await self.connection.commit()
