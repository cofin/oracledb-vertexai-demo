# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

import re
import uuid
from dataclasses import dataclass
from typing import Annotated

import structlog
from litestar import Controller, Response, post
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException, ValidationException
from litestar.params import Body
from litestar.plugins.flash import flash
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE


@dataclass
class CoffeeChatForm:
    message: str
    persona: str = "enthusiast"

from app.domain.chat import schemas
from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services import ADKRunner, AgentToolsService
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
        data: Annotated[CoffeeChatForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
        adk_runner: Inject[ADKRunner],
        tools_service: Inject[AgentToolsService],
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
                tools_service=tools_service,
            )
        except AIServiceUnconfigured as exc:
            await logger.awarning("AI service not configured", detail=str(exc))
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

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
