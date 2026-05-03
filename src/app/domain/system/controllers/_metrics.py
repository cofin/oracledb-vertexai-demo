# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from litestar import Controller, get

from app.domain.system.schemas import MetricCard, MetricsCharts, MetricsSummary
from app.domain.system.services import CacheService, MetricsService
from app.lib.di import Inject


class MetricsController(Controller):
    """Endpoints feeding the explore-page metrics panels."""

    @get(path="/api/metrics/summary", name="metrics.summary")
    async def get_metrics_summary(
        self,
        metrics_service: Inject[MetricsService],
        cache_service: Inject[CacheService],
    ) -> MetricsSummary:
        """Return summary cards for the metrics summary panel."""
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
    async def get_chart_data(self, metrics_service: Inject[MetricsService]) -> MetricsCharts:
        """Return the Explore dashboard chart payload."""
        return await metrics_service.get_chart_data(hours=1)
