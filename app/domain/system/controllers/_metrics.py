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

import re
import secrets

from litestar import Controller, get
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate, HXStopPolling

from app import schemas
from app.domain.products.services._vertex_ai import VertexAIService
from app.domain.system.services import CacheService, MetricsService
from app.lib.di import Inject


class MetricsController(Controller):
    """Metrics Controller for dashboard data."""

    @staticmethod
    def generate_csp_nonce() -> str:
        """Generate a  CSP nonce."""
        return secrets.token_urlsafe(16)

    @get(path="/dashboard", name="performance_dashboard")
    async def performance_dashboard(self, metrics_service: Inject[MetricsService]) -> HTMXTemplate:
        """Display performance dashboard."""
        metrics = await metrics_service.get_performance_stats(hours=24)

        return HTMXTemplate(
            template_name="performance_dashboard.html",
            context={
                "metrics": metrics,
                "csp_nonce": self.generate_csp_nonce(),
            },
            trigger_event="dashboard:loaded",
            params={"total_searches": metrics.get("total_searches", 0)},
            after="settle",
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
            },
        )

    @get(path="/metrics", name="metrics")
    async def get_metrics(self, metrics_service: Inject[MetricsService], request: HTMXRequest) -> dict | HXStopPolling:
        """Get performance metrics with validation."""
        if request.headers.get("X-Requested-With") != "XMLHttpRequest" and not request.htmx:
            return {"error": "Invalid request"}

        try:
            metrics = await metrics_service.get_performance_stats(hours=24)
            if request.htmx and metrics.get("total_searches", 0) == 0:
                return HXStopPolling()
            return {
                "total_searches": int(metrics.get("total_searches", 0)),
                "avg_search_time_ms": float(metrics.get("avg_search_time_ms", 0)),
                "avg_oracle_time_ms": float(metrics.get("avg_oracle_time_ms", 0)),
                "avg_similarity_score": float(metrics.get("avg_similarity_score", 0)),
            }
        except (ValueError, TypeError):
            return {"total_searches": 0, "avg_search_time_ms": 0, "avg_oracle_time_ms": 0, "avg_similarity_score": 0}

    @get(path="/api/metrics/summary", name="metrics.summary")
    async def get_metrics_summary(
        self,
        metrics_service: Inject[MetricsService],
        cache_service: Inject[CacheService],
        request: HTMXRequest,
    ) -> HTMXTemplate:
        """Get summary metrics for dashboard cards."""
        perf_stats = await metrics_service.get_performance_stats(hours=1)
        cache_stats = await cache_service.get_cache_stats()

        prev_stats = await metrics_service.get_performance_stats(hours=2)

        def calculate_trend(current: float, previous: float) -> tuple[str, float]:
            if not previous:
                return "neutral", 0
            change = ((current - previous) / previous) * 100
            return ("up" if change > 0 else "down", abs(change))

        total_trend, total_change = calculate_trend(
            perf_stats["total_searches"],
            prev_stats["total_searches"],
        )

        metrics_data = {
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

        trigger_event = None
        params = {}

        if cache_stats["cache_hit_rate"] > 90:  # noqa: PLR2004
            trigger_event = "metrics:high-cache-rate"
            params = {"rate": cache_stats["cache_hit_rate"]}
        elif perf_stats["avg_search_time_ms"] > 1000:  # noqa: PLR2004
            trigger_event = "metrics:slow-response"
            params = {"time": perf_stats["avg_search_time_ms"]}

        return HTMXTemplate(
            template_name="partials/_metric_cards.html",
            context={"metrics": metrics_data},
            trigger_event=trigger_event,
            params=params,
            after="settle" if trigger_event else None,
        )

    @get(path="/api/metrics/charts", name="metrics.charts")
    async def get_chart_data(
        self,
        metrics_service: Inject[MetricsService],
    ) -> schemas.ChartDataResponse:
        """Get chart data for dashboard visualizations."""
        time_series = await metrics_service.get_time_series_data(minutes=60)
        scatter_data = await metrics_service.get_scatter_data(hours=1)
        breakdown = await metrics_service.get_performance_breakdown()

        return schemas.ChartDataResponse(
            time_series=schemas.TimeSeriesData(
                labels=time_series["labels"],
                total_latency=time_series["total_latency"],
                oracle_latency=time_series["oracle_latency"],
                vertex_latency=time_series["vertex_latency"],
            ),
            scatter_data=scatter_data,
            breakdown_data=breakdown,
        )

    @get(path="/api/help/query-log/{message_id:str}", name="help.query_log")
    async def get_query_log(
        self,
        message_id: str,
        metrics_service: Inject[MetricsService],
        vertex_ai_service: Inject[VertexAIService],
        request: HTMXRequest,
    ) -> dict:
        """Get query execution details for help tooltips."""
        if not re.match(r"^[a-fA-F0-9\-]+$", message_id):
            return {"error": "Invalid message ID"}

        if not request.htmx and request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return {"error": "Invalid request"}

        try:
            query_metrics = await metrics_service.get_query_details(message_id) or {}
            return {
                "intent_query": query_metrics.get("intent_query", ""),
                "intent_type": query_metrics.get("intent_type", "PRODUCT_RAG"),
                "similarity": query_metrics.get("similarity_score", 0.9),
                "execution_time": query_metrics.get("intent_detection_time", 2.3),
                "vector_search_query": query_metrics.get("vector_search_query", ""),
                "matched_products": query_metrics.get("matched_products", []),
                "vector_search_time": query_metrics.get("oracle_time_ms", 8.7),
                "cache_queries": query_metrics.get("cache_queries", []),
                "execution_times": {
                    "intent_classification": query_metrics.get("intent_time_ms"),
                    "embedding_generation": query_metrics.get("embedding_time_ms"),
                    "vector_search": query_metrics.get("oracle_time_ms"),
                    "ai_generation": query_metrics.get("ai_time_ms"),
                    "total": query_metrics.get("search_time_ms"),
                },
            }

        except Exception:  # noqa: BLE001
            return {
                "error": "Metrics temporarily unavailable",
                "demo": True,
                "intent_type": "PRODUCT_RAG",
                "similarity": 0.9,
                "vector_search_time": 8.7,
            }
