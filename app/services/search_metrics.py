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

"""Search metrics service using raw Oracle SQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import oracledb

    from app.schemas import SearchMetricsCreate


class SearchMetricsService:
    """Search performance metrics using raw SQL."""

    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        """Initialize with Oracle connection."""
        self.connection = connection

    async def record_search(self, metrics_data: SearchMetricsCreate) -> dict[str, Any]:
        """Record search performance metrics."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
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
                """,
                {
                    "query_id": metrics_data.query_id,
                    "user_id": metrics_data.user_id,
                    "search_time_ms": metrics_data.search_time_ms,
                    "embedding_time_ms": metrics_data.embedding_time_ms,
                    "oracle_time_ms": metrics_data.oracle_time_ms,
                    "similarity_score": metrics_data.similarity_score,
                    "result_count": metrics_data.result_count,
                },
            )

            await self.connection.commit()

            # Get the inserted record
            await cursor.execute(
                """
                SELECT
                    id,
                    query_id,
                    user_id,
                    search_time_ms,
                    embedding_time_ms,
                    oracle_time_ms,
                    similarity_score,
                    result_count,
                    created_at,
                    updated_at
                FROM search_metrics
                WHERE query_id = :query_id
                ORDER BY created_at DESC
                FETCH FIRST 1 ROWS ONLY
                """,
                {"query_id": metrics_data.query_id},
            )

            row = await cursor.fetchone()
            if not row:
                msg = "Failed to create search metrics"
                raise RuntimeError(msg)

            return {
                "id": row[0],
                "query_id": row[1],
                "user_id": row[2],
                "search_time_ms": row[3],
                "embedding_time_ms": row[4],
                "oracle_time_ms": row[5],
                "similarity_score": row[6],
                "result_count": row[7],
                "created_at": row[8],
                "updated_at": row[9],
            }
        finally:
            cursor.close()

    async def get_performance_stats(self, hours: int = 24) -> dict:
        """Get performance statistics."""
        since = datetime.now(UTC) - timedelta(hours=hours)

        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    COUNT(id) as total_searches,
                    AVG(search_time_ms) as avg_search_time,
                    AVG(embedding_time_ms) as avg_embedding_time,
                    AVG(oracle_time_ms) as avg_oracle_time,
                    AVG(similarity_score) as avg_similarity,
                    MAX(search_time_ms) as max_search_time,
                    MIN(search_time_ms) as min_search_time
                FROM search_metrics
                WHERE created_at > :since
                """,
                {"since": since},
            )

            row = await cursor.fetchone()

            return {
                "total_searches": row[0] or 0,
                "avg_search_time_ms": round(row[1] or 0, 2),
                "avg_embedding_time_ms": round(row[2] or 0, 2),
                "avg_oracle_time_ms": round(row[3] or 0, 2),
                "avg_similarity_score": round(row[4] or 0, 3),
                "max_search_time_ms": row[5] or 0,
                "min_search_time_ms": row[6] or 0,
                "period_hours": hours,
            }
        finally:
            cursor.close()

    async def get_time_series_data(self, minutes: int = 60) -> dict:
        """Get time-series performance data for charts."""
        cursor = self.connection.cursor()
        try:
            # Oracle doesn't support bind variables with INTERVAL, so we calculate the timestamp
            since_time = datetime.now(UTC) - timedelta(minutes=minutes)
            await cursor.execute(
                """
                SELECT
                    TO_CHAR(created_at, 'HH24:MI') as time_bucket,
                    AVG(search_time_ms) as avg_total,
                    AVG(oracle_time_ms) as avg_oracle,
                    AVG(embedding_time_ms) as avg_embedding,
                    COUNT(*) as request_count
                FROM search_metrics
                WHERE created_at > :since_time
                GROUP BY TO_CHAR(created_at, 'HH24:MI')
                ORDER BY time_bucket
                """,
                {"since_time": since_time},
            )

            labels = []
            total_latency = []
            oracle_latency = []
            vertex_latency = []

            async for row in cursor:
                labels.append(row[0])
                total_latency.append(round(row[1] or 0, 2))
                oracle_latency.append(round(row[2] or 0, 2))
                vertex_latency.append(round(row[3] or 0, 2))

            return {
                "labels": labels,
                "total_latency": total_latency,
                "oracle_latency": oracle_latency,
                "vertex_latency": vertex_latency,
            }
        finally:
            cursor.close()

    async def get_scatter_data(self, hours: int = 1) -> list[dict]:
        """Get similarity score vs response time for scatter plot."""
        cursor = self.connection.cursor()
        try:
            # Oracle doesn't support bind variables with INTERVAL, so we calculate the timestamp
            since_time = datetime.now(UTC) - timedelta(hours=hours)
            await cursor.execute(
                """
                SELECT
                    similarity_score,
                    oracle_time_ms,
                    search_time_ms
                FROM search_metrics
                WHERE created_at > :since_time
                AND similarity_score IS NOT NULL
                ORDER BY created_at DESC
                FETCH FIRST 500 ROWS ONLY
                """,
                {"since_time": since_time},
            )

            return [
                {"x": round(row[0] or 0, 3), "y": round(row[1] or 0, 2), "total": round(row[2] or 0, 2)}
                async for row in cursor
            ]
        finally:
            cursor.close()

    async def get_performance_breakdown(self) -> dict:
        """Get average time breakdown for doughnut chart."""
        stats = await self.get_performance_stats(hours=1)

        embedding_pct = stats["avg_embedding_time_ms"]
        oracle_pct = stats["avg_oracle_time_ms"]
        app_pct = stats["avg_search_time_ms"] - embedding_pct - oracle_pct

        return {
            "labels": ["Vertex AI Embedding", "Oracle Vector Search", "Application Logic"],
            "data": [embedding_pct, oracle_pct, max(0, app_pct)],
        }
