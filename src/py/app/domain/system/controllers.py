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
from litestar.params import Dependency
from litestar.response import File

from app.domain.system import schemas
from app.domain.system.schemas import IntentExemplar
from app.domain.system.services import CacheService, ExemplarService, MetricsService
from app.lib.di import Inject
from app.lib.service import FilterTypes, OffsetPagination, create_filter_dependencies
from app.lib.settings import BASE_DIR


class ExemplarController(Controller):
    """Intent-classification exemplar endpoints (powers the explore page).

    Ch 4 wires the live-vs-ground-truth panel onto this listing — Ch 2 ships the
    plumbing only.
    """

    path = "/api/exemplars"
    tags = ["Exemplars"]
    dependencies = create_filter_dependencies({
        "pagination_type": "limit_offset",
        "sort_field": "id",
        "sort_order": "asc",
        "id_filter": int,
        "id_field": "id",
        "search": ["intent", "phrase"],
        "search_ignore_case": True,
        "created_at": True,
    })

    @get("/", operation_id="ListExemplars", name="exemplars:list", summary="List Intent Exemplars")
    async def list_exemplars(
        self,
        exemplars_service: Inject[ExemplarService],
        filters: list[FilterTypes] = Dependency(skip_validation=True),
    ) -> OffsetPagination[IntentExemplar]:
        """List intent exemplars with pagination, search, and filtering."""
        return await exemplars_service.list_with_count(*filters)


class SystemController(Controller):
    """System controller for root-level and un-grouped system routes."""

    @get(path="/favicon.ico", name="favicon", exclude_from_auth=True, include_in_schema=False)
    async def favicon(self) -> File:
        """Serve favicon with security headers."""
        return File(
            path=BASE_DIR.parents[2] / "src" / "js" / "public" / "favicon.ico",
            headers={"Cache-Control": "public, max-age=31536000", "X-Content-Type-Options": "nosniff"},
        )


class MetricsController(Controller):
    """Metrics controller for React dashboard APIs."""

    @get(path="/metrics", name="metrics")
    async def get_metrics(self, metrics_service: Inject[MetricsService]) -> dict[str, Any]:
        """Get performance metrics with validation."""
        try:
            metrics = await metrics_service.get_performance_stats(hours=24)
            return {
                "totalSearches": metrics.get("total_searches", 0),
                "avgSearchTimeMs": metrics.get("avg_search_time_ms", 0),
                "avgOracleTimeMs": metrics.get("avg_oracle_time_ms", 0),
                "avgSimilarityScore": metrics.get("avg_similarity_score", 0),
            }
        except (ValueError, TypeError):
            return {"totalSearches": 0, "avgSearchTimeMs": 0, "avgOracleTimeMs": 0, "avgSimilarityScore": 0}

    @get(path="/api/metrics/summary", name="metrics.summary")
    async def get_metrics_summary(
        self,
        metrics_service: Inject[MetricsService],
        cache_service: Inject[CacheService],
    ) -> schemas.MetricsSummaryResponse:
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

        return schemas.MetricsSummaryResponse(
            total_searches=schemas.MetricCard(
                label="Total Searches",
                value=f"{perf_stats['total_searches']:,}",
                trend=total_trend,
                trend_value=f"{total_change:.1f}%",
            ),
            avg_response_time=schemas.MetricCard(
                label="Avg Response Time",
                value=f"{perf_stats['avg_search_time_ms']:.0f}ms",
                trend="down" if perf_stats["avg_search_time_ms"] < 50 else "up",  # noqa: PLR2004
                trend_value=None,
            ),
            avg_oracle_time=schemas.MetricCard(
                label="Oracle Vector Time",
                value=f"{perf_stats['avg_oracle_time_ms']:.0f}ms",
                trend="neutral",
                trend_value=None,
            ),
            cache_hit_rate=schemas.MetricCard(
                label="Cache Hit Rate",
                value=f"{cache_stats['cache_hit_rate']:.1f}%",
                trend="up" if cache_stats["cache_hit_rate"] > 80 else "down",  # noqa: PLR2004
                trend_value=None,
            ),
        )

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
