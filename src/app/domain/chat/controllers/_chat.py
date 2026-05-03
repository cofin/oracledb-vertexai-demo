# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

import re
import uuid
from collections.abc import AsyncIterator

import structlog
from litestar import Controller, Response, post
from litestar.exceptions import ValidationException
from litestar.plugins.flash import flash
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from litestar.response import ServerSentEvent
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE

from app.domain.chat import schemas
from app.domain.chat.controllers._helpers import chat_form_from_request, location_context_from_form, metrics_badges
from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services import ADKRunner, AgentToolsService
from app.domain.chat.session import adk_session_identity, clear_adk_session_identity
from app.lib.di import Inject
from app.utils.serialization import to_json

logger = structlog.get_logger()
_STREAM_ERROR_MESSAGE = "Chat failed while streaming. Please try again."


class CoffeeChatController(Controller):
    """Coffee chat API controller — JSON for SPA clients, HTML partials for HTMX."""

    @staticmethod
    def validate_message(message: str) -> str:
        """Validate and sanitize user message input.

        Returns:
            The cleaned message text.

        Raises:
            ValidationException: If the message is empty after cleaning.
        """
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
        """Validate persona input.

        Returns:
            The requested persona or the default enthusiast persona.
        """
        if persona not in {"novice", "enthusiast", "expert", "barista"}:
            return "enthusiast"
        return persona

    @post(path="/api/chat", name="chat.api.send")
    async def send_chat_message(
        self,
        adk_runner: Inject[ADKRunner],
        tools_service: Inject[AgentToolsService],
        request: HTMXRequest,
    ) -> Response:
        """Handle chat submission. HTMX clients get partial HTML; SPA clients get JSON.

        Returns:
            An HTMX template response or JSON chat reply.

        Raises:
            ValidationException: If a non-HTMX request fails message validation.
        """
        data = await chat_form_from_request(request)
        try:
            clean_message = self.validate_message(data.message)
            location_context = location_context_from_form(data)
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
        user_id, session_id = adk_session_identity(request)

        try:
            result = await adk_runner.process_request(
                query=clean_message,
                user_id=user_id,
                session_id=session_id,
                persona=validated_persona,
                tools_service=tools_service,
                location_context=location_context,
            )
        except AIServiceUnconfigured as exc:
            await logger.awarning("AI service not configured", detail=exc.detail)
            if request.htmx:
                return HTMXTemplate(
                    template_name="partials/chat_error.html.j2",
                    context={"error": exc.detail},
                    re_target="#chat-error",
                    re_swap="innerHTML",
                )
            return Response(
                content={
                    "status": HTTP_503_SERVICE_UNAVAILABLE,
                    "title": exc.detail,
                    "detail": "Service Unavailable",
                },
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
            )

        answer = result.get("answer", "")
        intent = result.get("intent_detected", "GENERAL_CONVERSATION")
        from_cache = bool(result.get("from_cache", False))

        if request.htmx:
            badges = metrics_badges(result, intent, from_cache)
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
                    "embedding_cache_hit": bool(result.get("embedding_cache_hit", False)),
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
                sql_phases=result.get("sql_phases", []),
                from_cache=from_cache,
                embedding_cache_hit=bool(result.get("embedding_cache_hit", False)),
                intent_detected=intent,
                store_results=result.get("store_results", []),
                inventory_results=result.get("inventory_results", []),
                map_actions=result.get("map_actions", []),
                location_context=result.get("location_context", {}),
            ),
        )

    # docs:start-stream-handler
    @post(path="/api/chat/stream", name="chat.api.stream")
    async def stream_chat_message(
        self,
        adk_runner: Inject[ADKRunner],
        tools_service: Inject[AgentToolsService],
        request: HTMXRequest,
    ) -> ServerSentEvent:
        """Stream chat response events for the browser chat UI.

        Returns:
            Server-sent event stream with delta, final, or error events.

        Raises:
            ValidationException: If the user message fails validation (HTTP 400).
            AIServiceUnconfigured: If Vertex AI credentials are missing (HTTP 503).
        """
        data = await chat_form_from_request(request)
        clean_message = self.validate_message(data.message)
        validated_persona = self.validate_persona(data.persona)
        location_context = location_context_from_form(data)
        user_id, session_id = adk_session_identity(request)
        adk_runner.ensure_configured()

        async def stream_events() -> AsyncIterator[dict[str, str]]:
            try:
                async for event in adk_runner.stream_request(
                    query=clean_message,
                    user_id=user_id,
                    session_id=session_id,
                    persona=validated_persona,
                    tools_service=tools_service,
                    location_context=location_context,
                ):
                    event_type = str(event.get("type", "message"))
                    yield {"event": event_type, "data": to_json(event, as_bytes=False)}
            except Exception as exc:  # noqa: BLE001
                await logger.aexception(
                    "Chat stream failed after response started",
                    error_type=type(exc).__name__,
                    detail=str(exc),
                )
                yield {
                    "event": "error",
                    "data": to_json({"type": "error", "message": _STREAM_ERROR_MESSAGE}, as_bytes=False),
                }

        return ServerSentEvent(stream_events(), status_code=200)
    # docs:end-stream-handler

    @post(path="/api/chat/session/clear", name="chat.api.clear_session", status_code=200)
    async def clear_chat_session(self, adk_runner: Inject[ADKRunner], request: HTMXRequest) -> Response:
        """Clear the anonymous browser's ADK chat session.

        Returns:
            JSON confirmation for the frontend reset button.
        """
        user_id, session_id = adk_session_identity(request)
        await adk_runner.clear_session(user_id=user_id, session_id=session_id)
        clear_adk_session_identity(request)
        return Response(content={"status": "cleared"})
