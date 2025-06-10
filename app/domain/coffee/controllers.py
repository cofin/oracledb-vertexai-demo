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

from typing import TYPE_CHECKING, Annotated

import msgspec
from google.api_core import exceptions as google_exceptions
from litestar import Controller, get, post
from litestar.di import Provide
from litestar.response import File, Stream, Template

from app import config
from app.domain.coffee import deps, schemas
from app.lib.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from litestar.connection import Request
    from litestar.enums import RequestEncodingType
    from litestar.params import Body

    from app.domain.coffee.services.recommendation import RecommendationService
    from app.domain.coffee.services.account import SearchMetricsService, UserSessionService, ResponseCacheService
    from app.domain.coffee.services.vertex_ai import OracleVectorSearchService


class CoffeeChatController(Controller):
    dependencies = {
        "vertex_ai_service": Provide(deps.provide_vertex_ai_service),
        "vector_search_service": Provide(deps.provide_oracle_vector_search_service),
        "product_service": Provide(deps.provide_product_service),
        "shop_service": Provide(deps.provide_shop_service),
        "session_service": Provide(deps.provide_user_session_service),
        "conversation_service": Provide(deps.provide_chat_conversation_service),
        "cache_service": Provide(deps.provide_response_cache_service),
        "metrics_service": Provide(deps.provide_search_metrics_service),
        "recommendation_service": Provide(deps.provide_recommendation_service),
    }

    @get(path="/", name="ocw.show")
    async def show_ocw(self) -> Template:
        """Serve site root."""
        settings = get_settings()
        return Template(template_name="ocw.html.j2", context={"google_maps_api_key": settings.app.GOOGLE_API_KEY})

    @post(path="/", name="ocw.get")
    async def get_ocw(
        self,
        data: Annotated[schemas.CoffeeChatMessage, Body(title="Discover Coffee", media_type=RequestEncodingType.URL_ENCODED)],
        recommendation_service: RecommendationService,
        request: "Request",
    ) -> Template:
        """Handle both full page and HTMX partial requests."""
        import secrets
        from html import escape
        
        settings = get_settings()
        
        # Generate CSP nonce for inline scripts
        csp_nonce = secrets.token_urlsafe(16)
        
        # Sanitize user input
        safe_message = escape(data.message)
        
        # Get coffee recommendation
        reply = await recommendation_service.get_recommendation(safe_message)
        
        # Validate points of interest coordinates
        valid_pois = []
        for poi in reply.points_of_interest:
            if -90 <= poi.latitude <= 90 and -180 <= poi.longitude <= 180:
                valid_pois.append(poi)
        
        # Check if this is an HTMX request
        is_htmx = request.headers.get("HX-Request") == "true"
        
        if is_htmx:
            # Return partial template for HTMX - using secure version
            return Template(
                template_name="partials/chat_response_secure.html.j2",
                context={
                    "user_message": safe_message,
                    "ai_response": reply.answer,
                    "points_of_interest": valid_pois,
                    "query_id": reply.query_id,
                    "metrics": reply.search_metrics,
                    "google_maps_api_key": settings.app.GOOGLE_API_KEY,
                    "csp_nonce": csp_nonce,
                },
                headers={
                    "Content-Security-Policy": f"script-src 'self' 'nonce-{csp_nonce}' https://maps.googleapis.com https://maps.gstatic.com; object-src 'none';",
                }
            )
        # Return full page for non-HTMX requests (fallback)
        return Template(
            template_name="ocw.html.j2",
            context={
                "google_maps_api_key": settings.app.GOOGLE_API_KEY,
                "answer": reply.answer,
                "points_of_interest": [msgspec.to_builtins(poi) for poi in valid_pois],
                "csp_nonce": csp_nonce,
            },
            headers={
                "Content-Security-Policy": f"script-src 'self' 'nonce-{csp_nonce}' https://maps.googleapis.com https://maps.gstatic.com https://unpkg.com; object-src 'none';",
            }
        )

    @get(path="/chat/stream/{query_id:str}", name="chat.stream")
    async def stream_response(
        self,
        query_id: str,
        recommendation_service: RecommendationService,
    ) -> Stream:
        """Stream AI response using Server-Sent Events."""
        async def generate() -> AsyncGenerator[str, None]:
            try:
                # Get the query from cache or session using query_id
                # For now, use a simple prompt to demonstrate streaming
                prompt = "Tell me about coffee recommendations briefly"

                async for chunk in recommendation_service.vertex_ai.stream_content(prompt):
                    yield f"data: {{'chunk': '{chunk}', 'query_id': '{query_id}'}}\n\n"

                # Send completion signal
                yield f"data: {{'done': true, 'query_id': '{query_id}'}}\n\n"

            except google_exceptions.GoogleAPIError as e:
                yield f"data: {{'error': '{e!s}', 'query_id': '{query_id}'}}\n\n"

        return Stream(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
            },
        )

    @get(path="/metrics", name="metrics")
    async def get_metrics(
        self,
        metrics_service: "SearchMetricsService",
    ) -> dict:
        """Get performance metrics for dashboard."""
        return await metrics_service.get_performance_stats(hours=24)

    @get(path="/performance", name="performance_dashboard")
    async def performance_dashboard(self) -> Template:
        """Render performance dashboard."""
        return Template(template_name="performance_dashboard.html.j2")

    @get(path="/api/metrics/summary", name="metrics_summary")
    async def get_metrics_summary(
        self,
        metrics_service: "SearchMetricsService",
        session_service: "UserSessionService",
        cache_service: "ResponseCacheService",
    ) -> Template:
        """Get metrics summary for dashboard cards."""
        import random
        
        # Get base metrics
        base_stats = await metrics_service.get_performance_stats(hours=24)
        hour_stats = await metrics_service.get_performance_stats(hours=1)
        
        # Calculate trends (mock for demo)
        searches_trend = random.randint(-20, 50)
        response_time_trend = random.randint(-15, 15)
        cache_trend = random.randint(-10, 20)
        
        # Get active sessions count
        active_sessions = random.randint(50, 200)  # Mock for demo
        unique_users = random.randint(100, 500)  # Mock for demo
        
        # Calculate additional metrics
        metrics = {
            "total_searches": base_stats.get("total_searches", 0),
            "searches_trend": searches_trend,
            "avg_response_time": base_stats.get("avg_search_time_ms", 0),
            "response_time_trend": response_time_trend,
            "avg_oracle_time": base_stats.get("avg_oracle_time_ms", 0),
            "oracle_percentage": (base_stats.get("avg_oracle_time_ms", 0) / max(base_stats.get("avg_search_time_ms", 1), 1)) * 100,
            "cache_hit_rate": random.randint(60, 95),  # Mock for demo
            "cache_trend": cache_trend,
            "active_sessions": active_sessions,
            "unique_users": unique_users,
            "avg_similarity_score": base_stats.get("avg_similarity_score", 0.85),
            "successful_searches": random.randint(85, 98),  # Mock for demo
        }
        
        return Template(
            template_name="partials/metrics_summary.html.j2",
            context={"metrics": metrics}
        )

    @get(path="/api/metrics/charts", name="metrics_charts")
    async def get_metrics_charts(
        self,
        metrics_service: "SearchMetricsService",
    ) -> dict:
        """Get chart data for performance dashboard."""
        import random
        from datetime import datetime, timedelta
        
        # Generate time series data for last 24 hours
        now = datetime.now()
        labels = []
        total_times = []
        oracle_times = []
        
        for i in range(24, 0, -1):
            time_point = now - timedelta(hours=i)
            labels.append(time_point.strftime("%H:00"))
            # Mock data with some variance
            base_time = 100 + random.randint(-30, 30)
            oracle_time = 40 + random.randint(-15, 15)
            total_times.append(base_time)
            oracle_times.append(oracle_time)
        
        # Vector performance scatter data
        vector_performance = []
        for _ in range(50):
            vector_performance.append({
                "x": round(random.uniform(0.6, 0.95), 2),  # Similarity score
                "y": random.randint(30, 150)  # Response time
            })
        
        # Performance breakdown
        embedding_time = random.randint(20, 40)
        vector_search = random.randint(30, 50)
        ai_processing = random.randint(40, 70)
        other = random.randint(10, 20)
        
        return {
            "responseTime": {
                "labels": labels,
                "total": total_times,
                "oracle": oracle_times
            },
            "vectorPerformance": vector_performance,
            "breakdown": [embedding_time, vector_search, ai_processing, other]
        }

    @post(path="/api/vector-demo", name="vector_demo")
    async def vector_demo(
        self,
        data: Annotated[dict, Body(title="Vector Search Demo")],
        vector_search_service: "OracleVectorSearchService",
        metrics_service: "SearchMetricsService",
    ) -> Template:
        """Demonstrate vector search capabilities."""
        import time
        import numpy as np
        
        query = data.get("query", "")
        
        # Time the search
        start_time = time.time()
        
        # Perform vector search
        results = await vector_search_service.similarity_search(query, limit=5)
        
        search_time = (time.time() - start_time) * 1000
        
        # Format results
        formatted_results = []
        for result in results:
            product = result.get("product", {})
            formatted_results.append({
                "name": product.get("name", "Unknown"),
                "description": product.get("description", ""),
                "price": product.get("price", 0),
                "company": product.get("company", {}).get("name", "Unknown"),
                "similarity_score": result.get("similarity", 0)
            })
        
        # Debug info for demo
        debug_info = {
            "embedding_size": 768,
            "vector_norm": round(np.random.uniform(0.9, 1.1), 4),
            "top_components": [round(x, 3) for x in np.random.uniform(-0.5, 0.5, 5)]
        }
        
        # Metrics
        metrics = {
            "search_time_ms": search_time,
            "embedding_time_ms": search_time * 0.3,  # Mock
            "oracle_time_ms": search_time * 0.5,  # Mock
        }
        
        return Template(
            template_name="partials/vector_results.html.j2",
            context={
                "results": formatted_results,
                "query": query,
                "metrics": metrics,
                "debug_info": debug_info
            }
        )

    @get(path="/favicon.ico", name="favicon", exclude_from_auth=True, sync_to_thread=False, include_in_schema=False)
    def favicon(self) -> File:
        """Serve site root."""
        return File(path=f"{config.vite.public_dir}/favicon.ico")
