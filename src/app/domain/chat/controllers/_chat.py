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
import uuid

import structlog
from litestar import Controller, Response, post
from litestar.exceptions import HTTPException, ValidationException
from litestar.plugins.flash import flash
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE

from app.domain.chat import schemas
from app.domain.chat.services import ADKRunner
from app.domain.system.services import CacheService
from app.lib.di import Inject

logger = structlog.get_logger()


def _metrics_badges(result: dict, intent: str, from_cache: bool) -> dict:
    """Shape the metrics OOB-swap context for ``partials/_metrics_badges.html.j2``."""
    metrics = result.get("search_metrics") or {}
    return {
        "total_ms": metrics.get("total_ms"),
        "oracle_ms": metrics.get("oracle_ms"),
        "embedding_ms": metrics.get("embedding_ms"),
        "from_cache": from_cache,
        "intent": intent,
    }


class CoffeeChatController(Controller):
    """Coffee chat API controller — JSON for SPA clients, HTML partials for HTMX."""

    @staticmethod
    def validate_message(message: str) -> str:
        """Validate and sanitize user message input."""
        message = re.sub(r"<[^>]+>", "", message)
        max_length = 500
        if len(message) > max_length:
            message = message[:max_length]
        message = message.replace("\x00", "").strip()

        if not message:
            raise ValidationException(detail="Message cannot be empty")

        return message

    @staticmethod
    def validate_persona(persona: str) -> str:
        """Validate persona input."""
        if persona not in {"novice", "enthusiast", "expert", "barista"}:
            return "enthusiast"
        return persona

    @post(path="/api/chat", name="chat.api.send")
    async def send_chat_message(
        self,
        data: schemas.CoffeeChatMessage,
        adk_runner: Inject[ADKRunner],
        cache_service: Inject[CacheService],
        request: HTMXRequest,
    ) -> Response:
        """Handle chat submission. HTMX clients get partial HTML; SPA clients get JSON."""
        try:
            clean_message = self.validate_message(data.message)
        except ValidationException as exc:
            if request.htmx:
                return HTMXTemplate(
                    template_name="partials/chat_error.html.j2",
                    context={"error": str(exc.detail)},
                    re_target="#chat-error",
                    re_swap="innerHTML",
                )
            raise

        validated_persona = self.validate_persona(data.persona)
        session_id = request.headers.get("x-session-id", str(uuid.uuid4()))

        try:
            result = await adk_runner.process_request(
                query=clean_message,
                user_id="web_user",
                session_id=session_id,
                persona=validated_persona,
                cache_service=cache_service,
            )
        except ValueError as exc:
            if "API key" in str(exc) or "credentials" in str(exc).lower():
                await logger.awarning("AI service not configured", detail=str(exc))
                raise HTTPException(
                    status_code=HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI service is not configured. Set GOOGLE_API_KEY or VERTEX_AI_API_KEY in your .env file.",
                ) from exc
            raise

        answer = result.get("answer", "")
        intent = result.get("intent_detected", "GENERAL_CONVERSATION")
        from_cache = bool(result.get("from_cache", False))

        if request.htmx:
            badges = _metrics_badges(result, intent, from_cache)
            latency = badges["total_ms"]
            flash(
                request,
                f"Reply in {latency} ms" + (" (cache hit)" if from_cache else ""),
                "success" if from_cache else "info",
            )
            return HTMXTemplate(
                template_name="partials/_chat_response.html.j2",
                context={
                    "message": schemas.ChatMessage(message=answer, source="ai"),
                    "intent_detected": intent,
                    "latency_ms": latency,
                    "from_cache": from_cache,
                    "metrics_badges": badges,
                },
                trigger_event="chat:reply-rendered",
                after="swap",
            )

        return Response(
            content=schemas.CoffeeChatReply(
                message=clean_message,
                messages=[
                    schemas.ChatMessage(message=clean_message, source="human"),
                    schemas.ChatMessage(message=answer, source="ai"),
                ],
                answer=answer,
                query_id=str(uuid.uuid4()),
                search_metrics=result.get("search_metrics", {}),
                from_cache=from_cache,
                embedding_cache_hit=bool(result.get("embedding_cache_hit", False)),
                intent_detected=intent,
            ),
        )
