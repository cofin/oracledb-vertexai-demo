import uuid

import oracledb

from app.schemas import SearchMetricsCreate, SearchMetricsDTO

from .base import BaseRepository


class SearchMetricsRepository(BaseRepository[SearchMetricsDTO]):
    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        super().__init__(connection, SearchMetricsDTO)

    async def record_search(self, metrics_data: SearchMetricsCreate) -> None:
        metric_id = uuid.uuid4()
        query = """
            INSERT INTO search_metrics (
                id,
                query_id,
                user_id,
                search_time_ms,
                embedding_time_ms,
                oracle_time_ms,
                ai_time_ms,
                intent_time_ms,
                similarity_score,
                result_count
            )
            VALUES (
                :id,
                :query_id,
                :user_id,
                :search_time_ms,
                :embedding_time_ms,
                :oracle_time_ms,
                :ai_time_ms,
                :intent_time_ms,
                :similarity_score,
                :result_count
            )
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                {
                    "id": metric_id.bytes,
                    "query_id": metrics_data.query_id,
                    "user_id": metrics_data.user_id,
                    "search_time_ms": metrics_data.search_time_ms,
                    "embedding_time_ms": metrics_data.embedding_time_ms,
                    "oracle_time_ms": metrics_data.oracle_time_ms,
                    "ai_time_ms": metrics_data.ai_time_ms,
                    "intent_time_ms": metrics_data.intent_time_ms,
                    "similarity_score": metrics_data.similarity_score,
                    "result_count": metrics_data.result_count,
                },
            )
            await self.connection.commit()

    async def get_by_id(self, metric_id: str) -> SearchMetricsDTO | None:
        query = "SELECT id, query_id, user_id, search_time_ms, embedding_time_ms, oracle_time_ms, ai_time_ms, intent_time_ms, similarity_score, result_count, created_at, updated_at FROM search_metrics WHERE id = :id"
        return await self.fetch_one(query, {"id": metric_id})

    async def get_by_query_id(self, query_id: str) -> SearchMetricsDTO | None:
        """Get search metrics by query_id."""
        query = "SELECT id, query_id, user_id, search_time_ms, embedding_time_ms, oracle_time_ms, ai_time_ms, intent_time_ms, similarity_score, result_count, created_at, updated_at FROM search_metrics WHERE query_id = :query_id"
        return await self.fetch_one(query, {"query_id": query_id})

    async def get_performance_stats(self, hours: int = 24) -> dict:
        """Get performance statistics from the database."""
        query = f"""
            SELECT
                COUNT(*) as total_searches,
                AVG(search_time_ms) as avg_search_time_ms,
                AVG(embedding_time_ms) as avg_embedding_time_ms,
                AVG(oracle_time_ms) as avg_oracle_time_ms,
                AVG(similarity_score) as avg_similarity_score,
                MAX(search_time_ms) as max_search_time_ms,
                MIN(search_time_ms) as min_search_time_ms
            FROM search_metrics
            WHERE created_at >= SYSTIMESTAMP - INTERVAL '{hours}' HOUR
        """  # noqa: S608
        async with self.connection.cursor() as cursor:
            await cursor.execute(query)
            row = await cursor.fetchone()
            if row:
                columns = [desc[0].lower() for desc in cursor.description]
                return dict(zip(columns, row, strict=False))
        return {}

    async def get_scatter_data(self, hours: int = 1) -> list[dict]:
        """Get similarity score vs response time for scatter plot."""
        query = f"""
            SELECT
                search_time_ms,
                similarity_score
            FROM search_metrics
            WHERE created_at >= SYSTIMESTAMP - INTERVAL '{hours}' HOUR
            AND similarity_score IS NOT NULL
        """  # noqa: S608
        async with self.connection.cursor() as cursor:
            await cursor.execute(query)
            columns = [desc[0].lower() for desc in cursor.description]
            return [dict(zip(columns, row, strict=False)) async for row in cursor]

    async def get_time_series_data(self, minutes: int = 60) -> list[dict]:
        """Get time-series performance data for charts."""
        query = f"""
            SELECT
                TO_CHAR(created_at, 'HH24:MI') as time_bucket,
                AVG(search_time_ms) as total_latency,
                AVG(oracle_time_ms) as oracle_latency,
                AVG(embedding_time_ms) as vertex_latency
            FROM search_metrics
            WHERE created_at >= SYSTIMESTAMP - INTERVAL '{minutes}' MINUTE
            GROUP BY TO_CHAR(created_at, 'HH24:MI')
            ORDER BY time_bucket
        """  # noqa: S608
        async with self.connection.cursor() as cursor:
            await cursor.execute(query)
            columns = [desc[0].lower() for desc in cursor.description]
            return [dict(zip(columns, row, strict=False)) async for row in cursor]

    async def get_performance_breakdown(self) -> dict:
        """Get average time breakdown for doughnut chart."""
        query = """
            SELECT
                AVG(embedding_time_ms) as avg_embedding_time,
                AVG(oracle_time_ms) as avg_vector_search_time,
                AVG(ai_time_ms) as avg_ai_time,
                AVG(search_time_ms) - AVG(embedding_time_ms) - AVG(oracle_time_ms) - AVG(ai_time_ms) as avg_other_time
            FROM search_metrics
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(query)
            row = await cursor.fetchone()
            if row:
                columns = [desc[0].lower() for desc in cursor.description]
                return dict(zip(columns, row, strict=False))
        return {}
