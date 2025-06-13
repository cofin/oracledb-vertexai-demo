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
