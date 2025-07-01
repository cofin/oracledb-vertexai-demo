from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.repositories.search_metrics import SearchMetricsRepository
    from app.schemas import SearchMetricsCreate, SearchMetricsDTO


class SearchMetricsService:
    """Search performance metrics using a repository."""

    def __init__(self, search_metrics_repository: SearchMetricsRepository):
        """Initialize with search metrics repository."""
        self.repository = search_metrics_repository

    async def record_search(self, metrics_data: SearchMetricsCreate) -> SearchMetricsDTO:
        """Record search performance metrics."""
        return await self.repository.record_search(metrics_data)

    async def get_performance_stats(self, hours: int = 24) -> dict:
        """Get performance statistics."""
        # This logic would need to be implemented in the repository
        # if it were to be used.
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
        # This logic would need to be implemented in the repository
        # if it were to be used.
        return {
            "labels": [],
            "total_latency": [],
            "oracle_latency": [],
            "vertex_latency": [],
        }

    async def get_scatter_data(self, hours: int = 1) -> list[dict]:
        """Get similarity score vs response time for scatter plot."""
        # This logic would need to be implemented in the repository
        # if it were to be used.
        return []

    async def get_performance_breakdown(self) -> dict:
        """Get average time breakdown for doughnut chart."""
        # This logic would need to be implemented in the repository
        # if it were to be used.
        return {
            "labels": ["Embedding Generation", "Vector Search", "AI Processing", "Other"],
            "data": [0, 0, 0, 0],
        }

    async def get_query_details(self, query_id: str) -> dict | None:
        """Get detailed metrics for a specific query."""
        metric = await self.repository.get_by_id(query_id)
        if not metric:
            return None
        return metric.to_dict()
