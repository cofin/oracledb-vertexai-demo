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
from typing import TYPE_CHECKING, Annotated

from litestar import Controller, get, post
from litestar.params import Parameter
from litestar.plugins.htmx import (
    HTMXRequest,
    HTMXTemplate,
)
from litestar.response import File
from litestar_htmx import HXStopPolling

from app import schemas
from app.server.exception_handlers import HTMXValidationException

if TYPE_CHECKING:
    from litestar.enums import RequestEncodingType
    from litestar.params import Body

    from app.services import (
        ChatConversationService,
        RecommendationService,
        ResponseCacheService,
        SearchMetricsService,
        UserSessionService,
        VectorDemoService,
    )

FAST_THRESHOLD = 100
NORMAL_THRESHOLD = 500


class CoffeeChatController(Controller):
    """Coffee Chat Controller with enhanced security measures."""

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
    async def show_coffee_chat(
        self,
        session_service: UserSessionService,
        conversation_service: ChatConversationService,
        request: HTMXRequest,
        session_id: str | None = Parameter(cookie="session_id", default=None),
    ) -> HTMXTemplate:
        """Serve site root with CSP nonce and conversation history."""
        conversation_history: list[schemas.ChatConversationDTO] = []
        if session_id:
            active_session = await session_service.get_active_session(session_id)
            if active_session:
                history = await conversation_service.get_conversation_history(
                    user_id=active_session.user_id,
                    session_id=active_session.id,
                    limit=50,
                )
                conversation_history = list(reversed(history))

        return HTMXTemplate(
            template_name="coffee_chat.html",
            context={
                "csp_nonce": self.generate_csp_nonce(),
                "conversation_history": conversation_history,
            },
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=()",
            },
        )

    @get(path="/chat/{session_id:str}", name="chat.session")
    async def get_chat_session(
        self,
        session_service: UserSessionService,
        conversation_service: ChatConversationService,
        request: HTMXRequest,
        session_id: str,
    ) -> HTMXTemplate:
        """Serve chat history for a specific session."""
        conversation_history: list[schemas.ChatConversationDTO] = []
        active_session = await session_service.get_active_session(session_id)
        if active_session:
            history = await conversation_service.get_conversation_history(
                user_id=active_session.user_id,
                session_id=active_session.id,
                limit=50,
            )
            conversation_history = list(reversed(history))

        return HTMXTemplate(
            template_name="coffee_chat.html",
            context={
                "csp_nonce": self.generate_csp_nonce(),
                "conversation_history": conversation_history,
            },
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
        session_id: str | None = Parameter(cookie="session_id", default=None),
    ) -> HTMXTemplate:
        """Handle both full page and HTMX partial requests with enhanced security."""

        csp_nonce = self.generate_csp_nonce()
        clean_message = self.validate_message(data.message)
        validated_persona = self.validate_persona(data.persona)

        reply = await recommendation_service.get_recommendation(
            clean_message, persona=validated_persona, session_id=session_id
        )

        if request.htmx:
            response = HTMXTemplate(
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
                trigger_event="newMessage",
                after="settle",
            )
            response.set_cookie(
                key="session_id",
                value=reply.session_id,
                httponly=True,
                secure=request.url.scheme == "https",
                samesite="lax",
            )
            response.headers["HX-Push-Url"] = f"/chat/{reply.session_id}"
            return response

        response = HTMXTemplate(
            template_name="coffee_chat.html",
            context={
                "answer": reply.answer,
                "csp_nonce": csp_nonce,
            },
        )
        response.set_cookie(
            key="session_id",
            value=reply.session_id,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
        )
        return response

    @get(path="/chat/history", name="chat.history")
    async def get_chat_history(
        self,
        session_service: UserSessionService,
        conversation_service: ChatConversationService,
        request: HTMXRequest,
        session_id: str | None = Parameter(cookie="session_id", default=None),
    ) -> HTMXTemplate:
        """Get chat history."""
        conversation_history: list[schemas.ChatConversationDTO] = []
        if session_id:
            active_session = await session_service.get_active_session(session_id)
            if active_session:
                history = await conversation_service.get_conversation_history(
                    user_id=active_session.user_id,
                    session_id=active_session.id,
                    limit=50,
                )
                conversation_history = list(reversed(history))

        return HTMXTemplate(
            template_name="partials/chat_history.html",
            context={
                "conversation_history": conversation_history,
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
    ) -> str:
        """Get summary metrics for dashboard cards."""
        # Get performance stats
        perf_stats = await metrics_service.get_performance_stats(hours=1)

        avg_search_time = perf_stats.get("avg_search_time_ms")
        avg_search_time_str = f"{round(avg_search_time)}ms" if avg_search_time is not None else "N/A"

        avg_oracle_time = perf_stats.get("avg_oracle_time_ms")
        avg_oracle_time_str = f"{round(avg_oracle_time)}ms" if avg_oracle_time is not None else "N/A"

        avg_similarity_score = perf_stats.get("avg_similarity_score")
        avg_similarity_score_str = f"{avg_similarity_score:.2f}" if avg_similarity_score is not None else "N/A"

        return f"""
<div class="metric-item">
    <div class="metric-value">{perf_stats.get("total_searches", 0)}</div>
    <div class="metric-label">Total Searches</div>
</div>
<div class="metric-item">
    <div class="metric-value">{avg_search_time_str}</div>
    <div class="metric-label">Avg Response Time</div>
</div>
<div class="metric-item">
    <div class="metric-value">{avg_oracle_time_str}</div>
    <div class="metric-label">Oracle Vector Time</div>
</div>
<div class="metric-item">
    <div class="metric-value">{avg_similarity_score_str}</div>
    <div class="metric-label">Avg Similarity</div>
</div>
        """

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
        vector_demo_service: VectorDemoService,
        request: HTMXRequest,
    ) -> HTMXTemplate:
        """Interactive vector search demonstration."""
        query = self.validate_message(data.query)
        full_request_start = time.time()
        demo_results, detailed_timings, embedding_cache_hit = await vector_demo_service.search(query)

        pre_template_total = (
            detailed_timings["pre_template_overhead_ms"]
            + detailed_timings["similarity_search_total_ms"]
            + detailed_timings["metrics_recording_ms"]
            + detailed_timings["results_formatting_ms"]
        )

        performance_event = None
        perf_params = {}

        if pre_template_total < FAST_THRESHOLD:
            performance_event = "vector:search-fast"
            perf_params = {"level": "excellent"}
        elif pre_template_total < NORMAL_THRESHOLD:
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
                "embedding_time": f"{detailed_timings['embedding_ms']:.1f}ms",
                "oracle_time": f"{detailed_timings['oracle_ms']:.1f}ms",
                "cache_hit": embedding_cache_hit,
                "debug_timings": {k: f"{v:.1f}ms" for k, v in detailed_timings.items()},
            },
            trigger_event=performance_event,
            params={**perf_params, "total_ms": pre_template_total},
            after="settle",
        )
        detailed_timings["template_creation_ms"] = (time.time() - template_start) * 1000

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
            if not query_metrics:
                return {"error": "Performance metrics not available for this query."}

            total_time = query_metrics.get("search_time_ms", 0)
            embedding_time = query_metrics.get("embedding_time_ms", 0)
            oracle_time = query_metrics.get("oracle_time_ms", 0)
            ai_time = query_metrics.get("ai_time_ms", 0)
            intent_time = query_metrics.get("intent_time_ms", 0)
            other_time = total_time - embedding_time - oracle_time - ai_time - intent_time

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
                    "embedding_generation": embedding_time,
                    "vector_search": oracle_time,
                    "ai_processing": ai_time,
                    "intent_routing": intent_time,
                    "other": other_time,
                    "total": total_time,
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

    @get(path="/logout", name="logout", sync_to_thread=False)
    def logout(self, request: HTMXRequest) -> HTMXTemplate:
        """Log out the user and refresh the page."""
        response = HTMXTemplate(template_name="coffee_chat.html")
        response.delete_cookie("session_id")
        response.headers["HX-Refresh"] = "true"
        return response

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
