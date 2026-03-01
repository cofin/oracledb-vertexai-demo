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

from typing import Any

from litestar import Controller, get
from litestar.response import File

from app.domain.system import schemas
from app.domain.system.services import CacheService, MetricsService
from app.lib.di import Inject
from app.lib.settings import BASE_DIR


class SystemController(Controller):
    """System controller for root-level and un-grouped system routes."""

    @get(path="/favicon.ico", name="favicon", exclude_from_auth=True, include_in_schema=False)
    async def favicon(self) -> File:
        """Serve favicon with security headers."""
        return File(
            path=BASE_DIR / "server" / "static" / "favicon.ico",
            headers={"Cache-Control": "public, max-age=31536000", "X-Content-Type-Options": "nosniff"},
        )


class MetricsController(Controller):
    """Metrics controller for React dashboard APIs."""

    @get(path="/metrics", name="metrics")
    async def get_metrics(self, metrics_service: Inject[MetricsService]) -> dict:
        """Get performance metrics with validation."""
        try:
            metrics = await metrics_service.get_performance_stats(hours=24)
            return {
                "total_searches": metrics.get("total_searches", 0),
                "avg_search_time_ms": metrics.get("avg_search_time_ms", 0),
                "avg_oracle_time_ms": metrics.get("avg_oracle_time_ms", 0),
                "avg_similarity_score": metrics.get("avg_similarity_score", 0),
            }
        except (ValueError, TypeError):
            return {"total_searches": 0, "avg_search_time_ms": 0, "avg_oracle_time_ms": 0, "avg_similarity_score": 0}

    @get(path="/api/metrics/summary", name="metrics.summary")
    async def get_metrics_summary(
        self,
        metrics_service: Inject[MetricsService],
        cache_service: Inject[CacheService],
    ) -> dict[str, Any]:
        """Get summary metrics for UI cards."""
        perf_stats = await metrics_service.get_performance_stats(hours=1)
        cache_stats = await cache_service.get_cache_stats()
        prev_stats = await metrics_service.get_performance_stats(hours=2)

        def calculate_trend(current: float, previous: float) -> tuple[str, float]:
            if not previous:
                return "neutral", 0
            change = ((current - previous) / previous) * 100
            return ("up" if change > 0 else "down", abs(change))

        total_trend, total_change = calculate_trend(perf_stats["total_searches"], prev_stats["total_searches"])

        return {
            "total_searches": {
                "label": "Total Searches",
                "value": f"{perf_stats['total_searches']:,}",
                "trend": total_trend,
                "trend_value": f"{total_change:.1f}%",
            },
            "avg_response_time": {
                "label": "Avg Response Time",
                "value": f"{perf_stats['avg_search_time_ms']:.0f}ms",
                "trend": "down" if perf_stats["avg_search_time_ms"] < 50 else "up",  # noqa: PLR2004
                "trend_value": None,
            },
            "avg_oracle_time": {
                "label": "Oracle Vector Time",
                "value": f"{perf_stats['avg_oracle_time_ms']:.0f}ms",
                "trend": "neutral",
                "trend_value": None,
            },
            "cache_hit_rate": {
                "label": "Cache Hit Rate",
                "value": f"{cache_stats['cache_hit_rate']:.1f}%",
                "trend": "up" if cache_stats["cache_hit_rate"] > 80 else "down",  # noqa: PLR2004
                "trend_value": None,
            },
        }

    @get(path="/api/metrics/charts", name="metrics.charts")
    async def get_chart_data(self, metrics_service: Inject[MetricsService]) -> schemas.ChartDataResponse:
        """Get chart data for dashboard visualizations."""
        # Simplified for demo (logic moved to service in real app)
        return schemas.ChartDataResponse(
            time_series=schemas.TimeSeriesData(
                labels=[],
                total_latency=[],
                oracle_latency=[],
                vertex_latency=[],
            ),
            scatter_data=[],
            breakdown_data={},
        )
