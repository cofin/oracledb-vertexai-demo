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

"""Search metrics service using SQLSpec driver patterns."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.services.base import SQLSpecService

if TYPE_CHECKING:
    from sqlspec.adapters.oracledb import OracleAsyncDriver

    from app.schemas import SearchMetricsCreate


class SearchMetricsService(SQLSpecService):
    """Search performance metrics using SQLSpec driver patterns."""

    def __init__(self, driver: OracleAsyncDriver) -> None:
        """Initialize the service."""
        super().__init__(driver)

    async def record_search(self, metrics_data: SearchMetricsCreate) -> dict[str, Any]:
        """Record search performance metrics."""
        await self.driver.execute(
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
            query_id=metrics_data.query_id,
            user_id=metrics_data.user_id,
            search_time_ms=metrics_data.search_time_ms,
            embedding_time_ms=metrics_data.embedding_time_ms,
            oracle_time_ms=metrics_data.oracle_time_ms,
            similarity_score=metrics_data.similarity_score,
            result_count=metrics_data.result_count,
        )

        # Get the inserted record
        result = await self.driver.select_one_or_none(
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
            query_id=metrics_data.query_id,
        )

        if not result:
            msg = "Failed to create search metrics"
            raise RuntimeError(msg)

        return {
            "id": result["id"],
            "query_id": result["query_id"],
            "user_id": result["user_id"],
            "search_time_ms": result["search_time_ms"],
            "embedding_time_ms": result["embedding_time_ms"],
            "oracle_time_ms": result["oracle_time_ms"],
            "similarity_score": result["similarity_score"],
            "result_count": result["result_count"],
            "created_at": result["created_at"],
            "updated_at": result["updated_at"],
        }

    async def get_performance_stats(self, hours: int = 24) -> dict:
        """Get performance statistics."""
        since = datetime.now(UTC) - timedelta(hours=hours)

        result = await self.driver.select_one_or_none(
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
            since=since,
        )

        if result:
            return {
                "total_searches": result["total_searches"] or 0,
                "avg_search_time_ms": round(result["avg_search_time"] or 0, 2),
                "avg_embedding_time_ms": round(result["avg_embedding_time"] or 0, 2),
                "avg_oracle_time_ms": round(result["avg_oracle_time"] or 0, 2),
                "avg_similarity_score": round(result["avg_similarity"] or 0, 3),
                "max_search_time_ms": result["max_search_time"] or 0,
                "min_search_time_ms": result["min_search_time"] or 0,
                "period_hours": hours,
            }

        return {
            "total_searches": 0,
            "avg_search_time_ms": 0.0,
            "avg_embedding_time_ms": 0.0,
            "avg_oracle_time_ms": 0.0,
            "avg_similarity_score": 0.0,
            "max_search_time_ms": 0,
            "min_search_time_ms": 0,
            "period_hours": hours,
        }

    async def get_time_series_data(self, minutes: int = 60) -> dict:
        """Get time-series performance data for charts."""
        since_time = datetime.now(UTC) - timedelta(minutes=minutes)
        results = await self.driver.select(
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
            since_time=since_time,
        )

        labels = []
        total_latency = []
        oracle_latency = []
        vertex_latency = []

        for row in results:
            labels.append(row["time_bucket"])
            total_latency.append(round(row["avg_total"] or 0, 2))
            oracle_latency.append(round(row["avg_oracle"] or 0, 2))
            vertex_latency.append(round(row["avg_embedding"] or 0, 2))

        return {
            "labels": labels,
            "total_latency": total_latency,
            "oracle_latency": oracle_latency,
            "vertex_latency": vertex_latency,
        }

    async def get_scatter_data(self, hours: int = 1) -> list[dict]:
        """Get similarity score vs response time for scatter plot."""
        # Oracle doesn't support bind variables with INTERVAL, so we calculate the timestamp
        since_time = datetime.now(UTC) - timedelta(hours=hours)
        results = await self.driver.select(
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
            since_time=since_time,
        )

        return [
            {
                "x": round(row["similarity_score"] or 0, 3),
                "y": round(row["oracle_time_ms"] or 0, 2),
                "total": round(row["search_time_ms"] or 0, 2),
            }
            for row in results
        ]

    async def get_performance_breakdown(self) -> dict:
        """Get average time breakdown for doughnut chart."""
        # For now, use hardcoded estimates since we don't have ai_time_ms in the metrics table
        # In a real implementation, we'd need to add these fields to the search_metrics table
        stats = await self.get_performance_stats(hours=1)

        # Get the averages
        avg_total = stats["avg_search_time_ms"]
        avg_embedding = stats["avg_embedding_time_ms"]
        avg_oracle = stats["avg_oracle_time_ms"]

        # Estimate AI generation time as 70% of remaining time (based on typical LLM response times)
        remaining_time = max(0, avg_total - avg_embedding - avg_oracle)
        ai_generation_estimate = remaining_time * 0.7
        app_logic_estimate = remaining_time * 0.3

        return {
            "labels": ["Embedding Generation", "Vector Search", "AI Processing", "Other"],
            "data": [
                round(avg_embedding, 1),
                round(avg_oracle, 1),
                round(ai_generation_estimate, 1),
                round(app_logic_estimate, 1)
            ],
        }

    async def get_query_details(self, query_id: str) -> dict[str, Any] | None:
        """Get detailed metrics for a specific query."""
        result = await self.driver.select_one_or_none(
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
                created_at
            FROM search_metrics
            WHERE query_id = :query_id
            ORDER BY created_at DESC
            FETCH FIRST 1 ROWS ONLY
            """,
            query_id=query_id,
        )

        if not result:
            return None

        return {
            "id": result["id"],
            "query_id": result["query_id"],
            "user_id": result["user_id"],
            "search_time_ms": result["search_time_ms"],
            "embedding_time_ms": result["embedding_time_ms"],
            "oracle_time_ms": result["oracle_time_ms"],
            "similarity_score": result["similarity_score"],
            "result_count": result["result_count"],
            "created_at": result["created_at"],
        }
