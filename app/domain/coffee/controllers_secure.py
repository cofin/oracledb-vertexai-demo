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

import secrets
import re
from typing import TYPE_CHECKING, Annotated

from google.api_core import exceptions as google_exceptions
from litestar import Controller, get, post
from litestar.di import Provide
from litestar.response import File, Stream, Template
from litestar.exceptions import ValidationException

from app import config
from app.domain.coffee import deps, schemas
from app.lib.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from litestar.connection import Request
    from litestar.enums import RequestEncodingType
    from litestar.params import Body

    from app.domain.coffee.services.recommendation import RecommendationService
    from app.domain.coffee.services.account import SearchMetricsService


class SecureCoffeeChatController(Controller):
    """Secure version of the Coffee Chat Controller with enhanced security measures."""
    
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

    @staticmethod
    def generate_csp_nonce() -> str:
        """Generate a secure CSP nonce."""
        return secrets.token_urlsafe(16)

    @staticmethod
    def validate_message(message: str) -> str:
        """Validate and sanitize user message input."""
        # Remove any HTML tags
        message = re.sub(r'<[^>]+>', '', message)
        
        # Limit message length
        max_length = 500
        if len(message) > max_length:
            message = message[:max_length]
        
        # Remove any null bytes
        message = message.replace('\x00', '')
        
        # Trim whitespace
        message = message.strip()
        
        if not message:
            raise ValidationException("Message cannot be empty")
        
        return message

    @staticmethod
    def validate_persona(persona: str) -> str:
        """Validate persona input."""
        valid_personas = {'novice', 'enthusiast', 'expert', 'barista'}
        if persona not in valid_personas:
            return 'enthusiast'  # Default to enthusiast if invalid
        return persona

    @staticmethod
    def get_api_key_for_client(api_key: str, request: "Request") -> str:
        """Get a restricted version of the API key for client use."""
        # In production, you should:
        # 1. Use a separate, restricted API key for client-side use
        # 2. Implement domain restrictions on the Google Cloud Console
        # 3. Enable only the necessary APIs (Maps JavaScript API)
        # 4. Set up HTTP referrer restrictions
        # 5. Consider using a proxy endpoint instead of exposing the key
        
        # For now, we'll return the key but recommend implementing the above
        return api_key

    @get(path="/secure", name="ocw_secure.show")
    async def show_ocw_secure(self, request: "Request") -> Template:
        """Serve secure site root with CSP nonce."""
        settings = get_settings()
        csp_nonce = self.generate_csp_nonce()
        
        # Set security headers
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(self), camera=(), microphone=()"
        }
        
        # Get restricted API key for client use
        client_api_key = self.get_api_key_for_client(settings.app.GOOGLE_API_KEY, request)
        
        return Template(
            template_name="ocw_secure.html.j2", 
            context={
                "google_maps_api_key": client_api_key,
                "csp_nonce": csp_nonce
            },
            headers=headers
        )

    @post(path="/secure", name="ocw_secure.get")
    async def get_ocw_secure(
        self,
        data: Annotated[schemas.CoffeeChatMessage, Body(title="Discover Coffee", media_type=RequestEncodingType.URL_ENCODED)],
        recommendation_service: RecommendationService,
        request: "Request",
    ) -> Template:
        """Handle both full page and HTMX partial requests with enhanced security."""
        settings = get_settings()
        
        # Generate CSP nonce for this response
        csp_nonce = self.generate_csp_nonce()
        
        # Get CSP nonce from request headers (for HTMX requests)
        request_nonce = request.headers.get("X-CSP-Nonce", "")
        
        # Validate and sanitize inputs
        try:
            clean_message = self.validate_message(data.message)
            clean_persona = self.validate_persona(data.persona) if hasattr(data, 'persona') else 'enthusiast'
        except ValidationException as e:
            return Template(
                template_name="partials/chat_response_secure.html.j2",
                context={
                    "user_message": "Invalid input",
                    "ai_response": str(e),
                    "points_of_interest": [],
                    "query_id": "",
                    "csp_nonce": csp_nonce
                }
            )

        # Get coffee recommendation
        try:
            reply = await recommendation_service.get_recommendation(clean_message)
        except Exception as e:
            # Log the error securely (don't expose internal details to user)
            return Template(
                template_name="partials/chat_response_secure.html.j2",
                context={
                    "user_message": clean_message,
                    "ai_response": "Sorry, I encountered an error processing your request. Please try again.",
                    "points_of_interest": [],
                    "query_id": "",
                    "csp_nonce": csp_nonce
                }
            )

        # Validate points of interest data
        validated_pois = []
        if reply.points_of_interest:
            for poi in reply.points_of_interest:
                try:
                    # Validate coordinates
                    lat = float(poi.latitude)
                    lng = float(poi.longitude)
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        validated_pois.append({
                            "latitude": lat,
                            "longitude": lng,
                            "name": str(poi.name)[:100],  # Limit name length
                            "address": str(poi.address)[:200]  # Limit address length
                        })
                except (ValueError, TypeError, AttributeError):
                    # Skip invalid POIs
                    continue

        # Check if this is an HTMX request
        is_htmx = request.headers.get("HX-Request") == "true"

        if is_htmx:
            # Return partial template for HTMX
            return Template(
                template_name="partials/chat_response_secure.html.j2",
                context={
                    "user_message": clean_message,
                    "ai_response": reply.answer,
                    "points_of_interest": validated_pois,
                    "query_id": reply.query_id,
                    "metrics": reply.search_metrics,
                    "csp_nonce": csp_nonce
                }
            )
        
        # Return full page for non-HTMX requests (fallback)
        client_api_key = self.get_api_key_for_client(settings.app.GOOGLE_API_KEY, request)
        
        return Template(
            template_name="ocw_secure.html.j2",
            context={
                "google_maps_api_key": client_api_key,
                "answer": reply.answer,
                "points_of_interest": validated_pois,
                "csp_nonce": csp_nonce
            }
        )

    @get(path="/chat/stream/{query_id:str}", name="chat_secure.stream")
    async def stream_response_secure(
        self,
        query_id: str,
        recommendation_service: RecommendationService,
    ) -> Stream:
        """Stream AI response using Server-Sent Events with validation."""
        # Validate query_id format (assuming it should be alphanumeric)
        if not re.match(r'^[a-zA-Z0-9_-]+$', query_id):
            async def error_generate():
                yield "data: {'error': 'Invalid query ID'}\n\n"
            return Stream(
                error_generate(),
                media_type="text/event-stream"
            )
        
        async def generate() -> AsyncGenerator[str, None]:
            try:
                # Get the query from cache or session using query_id
                # For now, use a simple prompt to demonstrate streaming
                prompt = "Tell me about coffee recommendations briefly"

                async for chunk in recommendation_service.vertex_ai.stream_content(prompt):
                    # Escape chunk content for JSON
                    safe_chunk = chunk.replace('"', '\\"').replace('\n', '\\n')
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
                "X-Content-Type-Options": "nosniff"
            },
        )

    @get(path="/metrics", name="metrics_secure")
    async def get_metrics_secure(
        self,
        metrics_service: "SearchMetricsService",
        request: "Request"
    ) -> dict:
        """Get performance metrics with validation."""
        # Validate request is XHR
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return {"error": "Invalid request"}
        
        try:
            metrics = await metrics_service.get_performance_stats(hours=24)
            
            # Sanitize metrics data
            return {
                "total_searches": int(metrics.get("total_searches", 0)),
                "avg_search_time_ms": float(metrics.get("avg_search_time_ms", 0)),
                "avg_oracle_time_ms": float(metrics.get("avg_oracle_time_ms", 0)),
                "avg_similarity_score": float(metrics.get("avg_similarity_score", 0))
            }
        except Exception:
            return {
                "total_searches": 0,
                "avg_search_time_ms": 0,
                "avg_oracle_time_ms": 0,
                "avg_similarity_score": 0
            }

    @get(path="/favicon.ico", name="favicon_secure", exclude_from_auth=True, sync_to_thread=False, include_in_schema=False)
    def favicon(self) -> File:
        """Serve favicon with security headers."""
        return File(
            path=f"{config.vite.public_dir}/favicon.ico",
            headers={
                "Cache-Control": "public, max-age=31536000",
                "X-Content-Type-Options": "nosniff"
            }
        )