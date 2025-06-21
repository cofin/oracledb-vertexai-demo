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

from __future__ import annotations

import re
import secrets
import time
import uuid
from typing import TYPE_CHECKING, Annotated

from litestar import Controller, get, post
from litestar.di import Provide
from litestar.plugins.htmx import (
    HTMXRequest,
    HTMXTemplate,
    HXStopPolling,
)
from litestar.response import File, Stream

from app import schemas
from app.server import deps
from app.server.exception_handlers import HTMXValidationException

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar.enums import RequestEncodingType
    from litestar.params import Body

    from app.services.recommendation import RecommendationService
    from app.services.response_cache import ResponseCacheService
    from app.services.search_metrics import SearchMetricsService
    from app.services.vertex_ai import OracleVectorSearchService, VertexAIService


class CoffeeChatController(Controller):
    """Coffee Chat Controller with enhanced security measures."""

    dependencies = {
        "vertex_ai_service": Provide(deps.provide_vertex_ai_service),
        "vector_search_service": Provide(deps.provide_oracle_vector_search_service),
        "products_service": Provide(deps.provide_product_service),
        "shops_service": Provide(deps.provide_shop_service),
        "session_service": Provide(deps.provide_user_session_service),
        "conversation_service": Provide(deps.provide_chat_conversation_service),
        "embedding_cache": Provide(deps.provide_embedding_cache),
        "cache_service": Provide(deps.provide_response_cache_service),
        "metrics_service": Provide(deps.provide_search_metrics_service),
        "exemplar_service": Provide(deps.provide_intent_exemplar_service),
        "recommendation_service": Provide(deps.provide_recommendation_service),
    }

    @staticmethod
    def generate_csp_nonce() -> str:
        """Generate a  CSP nonce."""
        return secrets.token_urlsafe(16)

    @staticmethod
    def validate_message(message: str) -> str:
        """Validate and sanitize user message input."""
        # Remove any HTML tags
        message = re.sub(r"<[^>]+>", "", message)

        # Limit message length
        max_length = 500
        if len(message) > max_length:
            message = message[:max_length]
        message = message.replace("\x00", "").strip()

        if not message:
            raise HTMXValidationException(detail="Message cannot be empty", field="message")

        return message

    @staticmethod
    def validate_persona(persona: str) -> str:
        """Validate persona input."""
        if persona not in {"novice", "enthusiast", "expert", "barista"}:
            return "enthusiast"
        return persona

    @get(path="/", name="coffee_chat.show")
    async def show_coffee_chat(self) -> HTMXTemplate:
        """Serve site root with CSP nonce."""
        return HTMXTemplate(
            template_name="coffee_chat.html",
            context={"csp_nonce": self.generate_csp_nonce()},
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=()",
            },
        )

    @post(path="/", name="coffee_chat.get")
    async def handle_coffee_chat(
        self,
        data: Annotated[
            schemas.CoffeeChatMessage, Body(title="Discover Coffee", media_type=RequestEncodingType.URL_ENCODED)
        ],
        recommendation_service: RecommendationService,
        request: HTMXRequest,
    ) -> HTMXTemplate:
        """Handle both full page and HTMX partial requests with enhanced security."""

        csp_nonce = self.generate_csp_nonce()
        clean_message = self.validate_message(data.message)
        validated_persona = self.validate_persona(data.persona)

        reply = await recommendation_service.get_recommendation(clean_message, persona=validated_persona)

        if request.htmx:
            return HTMXTemplate(
                template_name="partials/chat_response.html",
                context={
                    "user_message": clean_message,
                    "ai_response": reply.answer,
                    "query_id": reply.query_id,
                    "metrics": reply.search_metrics,
                    "from_cache": getattr(reply, "from_cache", False),
                    "embedding_cache_hit": getattr(reply, "embedding_cache_hit", False),
                    "intent_detected": getattr(reply, "intent_detected", "GENERAL_CONVERSATION"),
                    "csp_nonce": csp_nonce,
                },
                trigger_event="help:process-complete",
                params={
                    "vector_search": "complete",
                    "llm_generation": "complete",
                    "query_id": reply.query_id,
                },
                after="settle",
            )

        return HTMXTemplate(
            template_name="coffee_chat.html",
            context={
                "answer": reply.answer,
                "csp_nonce": csp_nonce,
            },
        )

    @get(path="/chat/stream/{query_id:str}", name="chat.stream")
    async def stream_response(
        self,
        query_id: str,
        recommendation_service: RecommendationService,
    ) -> Stream:
        """Stream AI response using Server-Sent Events with validation."""
        # Validate query_id format (assuming it should be alphanumeric)
        if not re.match(r"^[a-zA-Z0-9_-]+$", query_id):

            async def error_generate() -> AsyncGenerator[str, None]:
                yield "data: {'error': 'Invalid query ID'}\n\n"

            return Stream(error_generate(), media_type="text/event-stream")

        async def generate() -> AsyncGenerator[str, None]:
            try:
                # Get the query from cache or session using query_id
                # For now, use a simple prompt to demonstrate streaming
                prompt = "Tell me about coffee recommendations briefly"

                async for chunk in recommendation_service.vertex_ai.stream_content(prompt):
                    # Escape chunk content for JSON
                    safe_chunk = chunk.replace('"', '\\"').replace("\n", "\\n")
                    yield f"data: {{'chunk': '{safe_chunk}', 'query_id': '{query_id}'}}\n\n"

                # Send completion signal
                yield f"data: {{'done': true, 'query_id': '{query_id}'}}\n\n"

            except Exception:  # noqa: BLE001
                yield f"data: {{'error': 'Service temporarily unavailable', 'query_id': '{query_id}'}}\n\n"

        return Stream(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
                "X-Content-Type-Options": "nosniff",
            },
        )

    @get(path="/dashboard", name="performance_dashboard")
    async def performance_dashboard(self, metrics_service: SearchMetricsService) -> HTMXTemplate:
        """Display performance dashboard."""
        # Get metrics for dashboard
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
    async def get_metrics(self, metrics_service: SearchMetricsService, request: HTMXRequest) -> dict | HXStopPolling:
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
        metrics_service: SearchMetricsService,
        cache_service: ResponseCacheService,
        request: HTMXRequest,
    ) -> HTMXTemplate:
        """Get summary metrics for dashboard cards."""
        # Get performance stats
        perf_stats = await metrics_service.get_performance_stats(hours=1)
        cache_stats = await cache_service.get_cache_stats(hours=1)

        # Calculate trends (compare to previous hour)
        prev_stats = await metrics_service.get_performance_stats(hours=2)

        def calculate_trend(current: float, previous: float) -> tuple[str, float]:
            if not previous:
                return "neutral", 0
            change = ((current - previous) / previous) * 100
            return ("up" if change > 0 else "down", abs(change))

        # Build metric cards data
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

        # Check if cache hit rate is high and trigger notification
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
        metrics_service: SearchMetricsService,
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

    @post(path="/api/vector-demo", name="vector.demo")
    async def vector_search_demo(
        self,
        data: Annotated[schemas.VectorDemoRequest, Body(media_type=RequestEncodingType.URL_ENCODED)],
        vertex_ai_service: VertexAIService,
        vector_search_service: OracleVectorSearchService,
        metrics_service: SearchMetricsService,
        request: HTMXRequest,
    ) -> HTMXTemplate:
        """Interactive vector search demonstration."""
        # Validate and sanitize input
        query = self.validate_message(data.query)

        full_request_start = time.time()
        detailed_timings: dict[str, float] = {}

        # 1. Time the similarity_search call
        similarity_search_start = time.time()
        results, embedding_cache_hit, vector_timings = await vector_search_service.similarity_search(query, k=5)
        detailed_timings["similarity_search_total_ms"] = (time.time() - similarity_search_start) * 1000
        detailed_timings.update(vector_timings)  # Merge internal timings

        # 2. Time the metrics recording
        metrics_record_start = time.time()
        await metrics_service.record_search(
            schemas.SearchMetricsCreate(
                query_id=str(uuid.uuid4()),
                user_id="demo_user",
                search_time_ms=(time.time() - full_request_start) * 1000,  # Current total
                embedding_time_ms=vector_timings["embedding_ms"],
                oracle_time_ms=vector_timings["oracle_ms"],
                similarity_score=1 - results[0]["distance"] if results else 0,
                result_count=len(results),
            )
        )
        detailed_timings["metrics_recording_ms"] = (time.time() - metrics_record_start) * 1000

        # 3. Time results formatting
        format_results_start = time.time()
        demo_results = [
            {
                "name": r["name"],
                "description": r["description"],
                "similarity": f"{(1 - r['distance']) * 100:.1f}%",
                "distance": r["distance"],
            }
            for r in results
        ]
        detailed_timings["results_formatting_ms"] = (time.time() - format_results_start) * 1000

        # 4. Calculate total time before template rendering
        pre_template_total = (time.time() - full_request_start) * 1000

        # Calculate overhead so far
        known_duration = sum([
            detailed_timings.get("similarity_search_total_ms", 0),
            detailed_timings.get("metrics_recording_ms", 0),
            detailed_timings.get("results_formatting_ms", 0),
        ])
        detailed_timings["pre_template_overhead_ms"] = pre_template_total - known_duration

        # Log detailed timings for debugging
        request.logger.info(
            "vector_demo_detailed_timings",
            query=query[:50],
            timings=detailed_timings,
            cache_hit=embedding_cache_hit,
        )

        # Determine performance level and trigger appropriate event
        performance_event = None
        perf_params = {}

        if pre_template_total < 100:  # noqa: PLR2004
            performance_event = "vector:search-fast"
            perf_params = {"level": "excellent"}
        elif pre_template_total < 500:  # noqa: PLR2004
            performance_event = "vector:search-normal"
            perf_params = {"level": "good"}
        else:
            performance_event = "vector:search-slow"
            perf_params = {"level": "needs-optimization"}

        # 5. Create template response (timing template creation separately)
        template_start = time.time()
        response = HTMXTemplate(
            template_name="partials/_vector_results.html",
            context={
                "results": demo_results,
                "search_time": f"{pre_template_total:.0f}ms",
                "embedding_time": f"{vector_timings['embedding_ms']:.1f}ms",
                "oracle_time": f"{vector_timings['oracle_ms']:.1f}ms",
                "cache_hit": embedding_cache_hit,
                # Add detailed timing breakdown for debugging
                "debug_timings": {k: f"{v:.1f}ms" for k, v in detailed_timings.items()},
            },
            # Trigger performance events
            trigger_event=performance_event,
            params={**perf_params, "total_ms": pre_template_total},
            after="settle",
        )
        detailed_timings["template_creation_ms"] = (time.time() - template_start) * 1000

        # Final log with all timings
        detailed_timings["total_endpoint_ms"] = (time.time() - full_request_start) * 1000
        request.logger.info("vector_demo_final_timings", timings=detailed_timings)

        return response

    @get(path="/api/help/query-log/{message_id:str}", name="help.query_log")
    async def get_query_log(
        self,
        message_id: str,
        metrics_service: SearchMetricsService,
        recommendation_service: RecommendationService,
        request: HTMXRequest,
    ) -> dict:
        """Get query execution details for help tooltips."""
        # Validate message_id format
        if not re.match(r"^[a-fA-F0-9\-]+$", message_id):
            return {"error": "Invalid message ID"}

        # Check if this is an XHR request
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
                    "embedding_generation": query_metrics.get("embedding_time_ms"),
                    "vector_search": query_metrics.get("oracle_time_ms"),
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

    @get(
        path="/favicon.ico",
        name="favicon",
        exclude_from_auth=True,
        sync_to_thread=False,
        include_in_schema=False,
    )
    def favicon(self) -> File:
        """Serve favicon with security headers."""
        return File(
            path="app/server/static/favicon.ico",
            headers={"Cache-Control": "public, max-age=31536000", "X-Content-Type-Options": "nosniff"},
        )
