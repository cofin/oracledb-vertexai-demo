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
from typing import TYPE_CHECKING, Annotated

from google.api_core import exceptions as google_exceptions
from litestar import Controller, get, post
from litestar.di import Provide
from litestar.exceptions import ValidationException
from litestar.response import File, Stream
from litestar_htmx import HTMXRequest, HTMXTemplate

from app import schemas
from app.server import deps

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar.enums import RequestEncodingType
    from litestar.params import Body

    from app.services.account import SearchMetricsService
    from app.services.recommendation import RecommendationService


class CoffeeChatController(Controller):
    """Coffee Chat Controller with enhanced security measures."""

    dependencies = {
        "vertex_ai_service": Provide(deps.provide_vertex_ai_service),
        "vector_search_service": Provide(deps.provide_oracle_vector_search_service),
        "products_service": Provide(deps.provide_product_service),
        "shops_service": Provide(deps.provide_shop_service),
        "session_service": Provide(deps.provide_user_session_service),
        "conversation_service": Provide(deps.provide_chat_conversation_service),
        "cache_service": Provide(deps.provide_response_cache_service),
        "metrics_service": Provide(deps.provide_search_metrics_service),
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
            msg = "Message cannot be empty"
            raise ValidationException(msg)

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
            template_name="coffee_chat.html.j2",
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
        # Generate CSP nonce for this response
        csp_nonce = self.generate_csp_nonce()

        # Validate and sanitize inputs
        try:
            clean_message = self.validate_message(data.message)
        except ValidationException as e:
            return HTMXTemplate(
                template_name="partials/chat_response.html.j2",
                context={
                    "user_message": "Invalid input",
                    "ai_response": str(e),
                    "query_id": "",
                    "csp_nonce": csp_nonce,
                },
            )

        # Get coffee recommendation
        try:
            reply = await recommendation_service.get_recommendation(clean_message)
        except (google_exceptions.GoogleAPIError, ValueError):
            # Log the error ly (don't expose internal details to user)
            return HTMXTemplate(
                template_name="partials/chat_response.html.j2",
                context={
                    "user_message": clean_message,
                    "ai_response": "Sorry, I encountered an error processing your request. Please try again.",
                    "query_id": "",
                    "csp_nonce": csp_nonce,
                },
            )

        # Check if this is an HTMX request using the HTMXRequest
        if request.htmx:
            # Return partial template for HTMX
            return HTMXTemplate(
                template_name="partials/chat_response.html.j2",
                context={
                    "user_message": clean_message,
                    "ai_response": reply.answer,
                    "query_id": reply.query_id,
                    "metrics": reply.search_metrics,
                    "csp_nonce": csp_nonce,
                },
            )

        # Return full page for non-HTMX requests (fallback)
        return HTMXTemplate(
            template_name="coffee_chat.html.j2",
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

            except google_exceptions.GoogleAPIError:
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

    @get(path="/metrics", name="metrics")
    async def get_metrics(self, metrics_service: SearchMetricsService, request: HTMXRequest) -> dict:
        """Get performance metrics with validation."""
        # Validate request is XHR or HTMX
        if request.headers.get("X-Requested-With") != "XMLHttpRequest" and not request.htmx:
            return {"error": "Invalid request"}

        try:
            metrics = await metrics_service.get_performance_stats(hours=24)

            # Sanitize metrics data
            return {
                "total_searches": int(metrics.get("total_searches", 0)),
                "avg_search_time_ms": float(metrics.get("avg_search_time_ms", 0)),
                "avg_oracle_time_ms": float(metrics.get("avg_oracle_time_ms", 0)),
                "avg_similarity_score": float(metrics.get("avg_similarity_score", 0)),
            }
        except (ValueError, TypeError):
            return {"total_searches": 0, "avg_search_time_ms": 0, "avg_oracle_time_ms": 0, "avg_similarity_score": 0}

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
            path="app/static/favicon.ico",
            headers={"Cache-Control": "public, max-age=31536000", "X-Content-Type-Options": "nosniff"},
        )
