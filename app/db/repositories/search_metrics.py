from app.schemas import SearchMetricsDTO, SearchMetricsCreate
from .base import BaseRepository

class SearchMetricsRepository(BaseRepository[SearchMetricsDTO]):
    def __init__(self, connection):
        super().__init__(connection, SearchMetricsDTO)

    async def record_search(self, metrics_data: SearchMetricsCreate) -> SearchMetricsDTO:
        query = """
            INSERT INTO search_metrics (
                query_id,
                user_id,
                search_time_ms,
                embedding_time_ms,
                oracle_time_ms,
                similarity_score,
                result_count
            )
            VALUES (
                :query_id,
                :user_id,
                :search_time_ms,
                :embedding_time_ms,
                :oracle_time_ms,
                :similarity_score,
                :result_count
            )
            RETURNING id INTO :id
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                {
                    "query_id": metrics_data.query_id,
                    "user_id": metrics_data.user_id,
                    "search_time_ms": metrics_data.search_time_ms,
                    "embedding_time_ms": metrics_data.embedding_time_ms,
                    "oracle_time_ms": metrics_data.oracle_time_ms,
                    "similarity_score": metrics_data.similarity_score,
                    "result_count": metrics_data.result_count,
                    "id": cursor.var(str),
                },
            )
            metric_id = cursor.bindvars["id"].getvalue()
            await self.connection.commit()
        return await self.get_by_id(metric_id)

    async def get_by_id(self, metric_id: str) -> SearchMetricsDTO | None:
        query = "SELECT id, query_id, user_id, search_time_ms, embedding_time_ms, oracle_time_ms, similarity_score, result_count, created_at, updated_at FROM search_metrics WHERE id = :id"
        return await self.fetch_one(query, {"id": metric_id})
