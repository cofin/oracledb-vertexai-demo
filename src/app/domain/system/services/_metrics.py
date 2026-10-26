# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Search performance telemetry and dashboard metrics projection service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlspec import sql

from app.domain.system.schemas import (
    MetricsBreakdown,
    MetricsBreakdownRow,
    MetricsCharts,
    MetricsScatterPoint,
    MetricsTimeSeries,
    MetricsTimeSeriesPoints,
    MetricsTimeSeriesRow,
    PerformanceStats,
    SearchMetricsCreate,
)
from app.lib.service import OracleLoaderService
from app.utils.serialization import schema_dump

__all__ = ("MetricsService",)


class MetricsService(OracleLoaderService):
    """Handles performance metrics and search logging."""

    __slots__ = ()

    async def record_search(self, metrics: SearchMetricsCreate) -> None:
        """Persist a search telemetry row into ``search_metric``."""
        await self.driver.execute(sql.insert("search_metric").values(**schema_dump(metrics, wire_format=False)))
        await self.driver.commit()

    async def get_performance_stats(self, hours: int = 24, *, window_end_hours: int = 0) -> PerformanceStats:
        """Aggregate search latency and similarity statistics over a disjoint hour window."""
        row = await self.driver.select_one_or_none(
            self.get_sql("get-performance-stats"),
            window_start_hours=hours,
            window_end_hours=window_end_hours,
            schema_type=PerformanceStats,
        )
        return row or PerformanceStats(
            total_searches=0, avg_search_time_ms=0.0, avg_oracle_time_ms=0.0, avg_similarity_score=0.0
        )

    async def get_time_series(self, hours: int = 1) -> MetricsTimeSeries:
        """Aggregate per-minute latency buckets for the requested window.

        Returns:
            A :class:`MetricsTimeSeries` with parallel ``labels`` and ``series`` arrays.
        """
        since = datetime.now(UTC) - timedelta(hours=hours)
        return await self._select_time_series(since)

    async def get_chart_data(self, hours: int = 1) -> MetricsCharts:
        """Return all Explore dashboard chart projections for a shared time window."""
        since = datetime.now(UTC) - timedelta(hours=hours)
        time_series = await self._select_time_series(since)
        scatter = await self.driver.select(
            self.get_sql("metrics-scatter-points"), since=since, schema_type=MetricsScatterPoint
        )
        breakdown_row = await self.driver.select_one_or_none(
            self.get_sql("metrics-breakdown"), since=since, schema_type=MetricsBreakdownRow
        )
        breakdown = breakdown_row or MetricsBreakdownRow(
            embedding_ms=0.0, oracle_ms=0.0, ai_ms=0.0, intent_ms=0.0, other_ms=0.0
        )
        return MetricsCharts(
            time_series=time_series,
            scatter=scatter,
            breakdown=MetricsBreakdown(
                labels=[
                    "Vertex AI Embedding",
                    "Oracle Vector Search",
                    "AI Processing",
                    "Intent Routing",
                    "Application Logic",
                ],
                values=[
                    breakdown.embedding_ms,
                    breakdown.oracle_ms,
                    breakdown.ai_ms,
                    breakdown.intent_ms,
                    breakdown.other_ms,
                ],
            ),
        )

    async def _select_time_series(self, since: datetime) -> MetricsTimeSeries:
        """Fetch per-minute latency buckets newer than ``since``."""
        rows = await self.driver.select(
            self.get_sql("metrics-time-series"), since=since, schema_type=MetricsTimeSeriesRow
        )
        return MetricsTimeSeries(
            labels=[row.bucket for row in rows],
            series=MetricsTimeSeriesPoints(
                total_ms=[row.total_ms for row in rows],
                oracle_ms=[row.oracle_ms for row in rows],
                embedding_ms=[row.embedding_ms for row in rows],
            ),
        )
