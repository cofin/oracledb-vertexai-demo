# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

from litestar import Controller, get

from app.domain.system.schemas import (
    MetricCard,
    MetricsDashboard,
    MetricsSummary,
    MetricsTimeSeries,
)
from app.domain.system.services import CacheService, MetricsService
from app.lib.di import Inject


class MetricsController(Controller):
    """Metrics endpoints feeding the explore-page panels and ops dashboard."""

    @get(path="/metrics", name="metrics")
    async def get_metrics(self, metrics_service: Inject[MetricsService]) -> MetricsDashboard:
        """24-hour rollup for the legacy operations dashboard."""
        try:
            stats = await metrics_service.get_performance_stats(hours=24)
            return MetricsDashboard(
                total_searches=stats.total_searches,
                avg_search_time_ms=stats.avg_search_time_ms,
                avg_oracle_time_ms=stats.avg_oracle_time_ms,
                avg_similarity_score=stats.avg_similarity_score,
            )
        except (ValueError, TypeError):
            return MetricsDashboard(
                total_searches=0,
                avg_search_time_ms=0.0,
                avg_oracle_time_ms=0.0,
                avg_similarity_score=0.0,
            )

    @get(path="/api/metrics/summary", name="metrics.summary")
    async def get_metrics_summary(
        self,
        metrics_service: Inject[MetricsService],
        cache_service: Inject[CacheService],
    ) -> MetricsSummary:
        """Cards for explore-page Panel 3 (consumed via ``ls-for``)."""
        perf_stats = await metrics_service.get_performance_stats(hours=1)
        cache_stats = await cache_service.get_cache_stats()
        prev_stats = await metrics_service.get_performance_stats(hours=2)

        def calculate_trend(current: float, previous: float) -> tuple[str, float]:
            if not previous:
                return "neutral", 0
            change = ((current - previous) / previous) * 100
            return ("up" if change > 0 else "down", abs(change))

        total_trend, total_change = calculate_trend(perf_stats.total_searches, prev_stats.total_searches)

        return MetricsSummary(
            cards=[
                MetricCard(
                    label="Total Searches",
                    value=f"{perf_stats.total_searches:,}",
                    trend=total_trend,
                    trend_value=f"{total_change:.1f}%",
                ),
                MetricCard(
                    label="Avg Response Time",
                    value=f"{perf_stats.avg_search_time_ms:.0f}ms",
                    trend="down" if perf_stats.avg_search_time_ms < 50 else "up",  # noqa: PLR2004
                ),
                MetricCard(
                    label="Oracle Vector Time",
                    value=f"{perf_stats.avg_oracle_time_ms:.0f}ms",
                ),
                MetricCard(
                    label="Cache Hit Rate",
                    value=f"{cache_stats.cache_hit_rate:.1f}%",
                    trend="up" if cache_stats.cache_hit_rate > 80 else "down",  # noqa: PLR2004
                ),
            ],
        )

    @get(path="/api/metrics/charts", name="metrics.charts")
    async def get_chart_data(self, metrics_service: Inject[MetricsService]) -> MetricsTimeSeries:
        """Per-minute latency tracks for the explore-page chart (last hour)."""
        return await metrics_service.get_time_series(hours=1)
