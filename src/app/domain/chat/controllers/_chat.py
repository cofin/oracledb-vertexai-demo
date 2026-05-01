# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

import json
import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import structlog
from litestar import Controller, Response, post
from litestar.exceptions import ValidationException
from litestar.plugins.flash import flash
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from litestar.response import ServerSentEvent
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE

from app.domain.chat import schemas
from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.chat.services import ADKRunner, AgentToolsService
from app.lib.di import Inject

logger = structlog.get_logger()
_ADK_SESSION_KEY = "adk_session_id"
_ADK_USER_KEY = "adk_user_id"
_STREAM_ERROR_MESSAGE = "Chat failed while streaming. Please try again."


@dataclass
class CoffeeChatForm:
    message: str
    persona: str = "enthusiast"


def _metrics_badges(result: dict, intent: str, from_cache: bool) -> dict:
    """Shape the metrics OOB-swap context for ``partials/_metrics_badges.html.j2``.

    Returns:
        Template context for the metrics badge partial.
    """
    metrics = result.get("search_metrics") or {}
    return {
        "total_ms": metrics.get("total_ms"),
        "oracle_ms": metrics.get("oracle_ms"),
        "embedding_ms": metrics.get("embedding_ms"),
        "vector_query": metrics.get("vector_query"),
        "from_cache": from_cache,
        "embedding_cache_hit": bool(result.get("embedding_cache_hit")),
        "intent": intent,
    }


def _adk_session_identity(request: HTMXRequest) -> tuple[str, str]:
    """Bridge Litestar's server-side session identity to ADK's session backend.

    Returns:
        The ADK user id and session id derived from the Litestar session.
    """
    session = request.session
    session_id = session.get(_ADK_SESSION_KEY)
    if not isinstance(session_id, str) or not session_id:
        session_id = request.get_session_id() or str(uuid.uuid4())
        session[_ADK_SESSION_KEY] = session_id

    user_id = session.get(_ADK_USER_KEY)
    if not isinstance(user_id, str) or not user_id:
        user_id = f"web:{session_id}"
        session[_ADK_USER_KEY] = user_id

    return user_id, session_id


def _payload_value(payload: Any, key: str, default: str = "") -> str:
    getter = getattr(payload, "get", None)
    value = getter(key, default) if callable(getter) else default
    if isinstance(value, list | tuple):
        value = value[0] if value else default
    return str(value or default)


async def _chat_form_from_request(request: HTMXRequest) -> CoffeeChatForm:
    """Parse either JSON API payloads or HTMX form submissions.

    Returns:
        Normalized chat form data.
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        payload = await request.form()
    return CoffeeChatForm(
        message=_payload_value(payload, "message"),
        persona=_payload_value(payload, "persona", "enthusiast"),
    )


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
        data = await _chat_form_from_request(request)
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
        user_id, session_id = _adk_session_identity(request)

        try:
            result = await adk_runner.process_request(
                query=clean_message,
                user_id=user_id,
                session_id=session_id,
                persona=validated_persona,
                tools_service=tools_service,
            )
        except AIServiceUnconfigured as exc:
            await logger.awarning("AI service not configured", detail=str(exc))
            if request.htmx:
                return HTMXTemplate(
                    template_name="partials/chat_error.html.j2",
                    context={"error": str(exc)},
                    re_target="#chat-error",
                    re_swap="innerHTML",
                )
            return Response(
                content={
                    "status": HTTP_503_SERVICE_UNAVAILABLE,
                    "title": str(exc),
                    "detail": "Service Unavailable",
                },
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
            )

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
            ),
        )

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
        """
        data = await _chat_form_from_request(request)

        async def stream_events() -> AsyncIterator[dict[str, str]]:
            try:
                clean_message = self.validate_message(data.message)
                validated_persona = self.validate_persona(data.persona)
                user_id, session_id = _adk_session_identity(request)
                async for event in adk_runner.stream_request(
                    query=clean_message,
                    user_id=user_id,
                    session_id=session_id,
                    persona=validated_persona,
                    tools_service=tools_service,
                ):
                    event_type = str(event.get("type", "message"))
                    yield {"event": event_type, "data": json.dumps(event)}
            except (AIServiceUnconfigured, ValidationException) as exc:
                yield {
                    "event": "error",
                    "data": json.dumps({"type": "error", "message": str(getattr(exc, "detail", exc))}),
                }
            except Exception as exc:  # noqa: BLE001
                await logger.aexception(
                    "Chat stream failed after response started",
                    error_type=type(exc).__name__,
                    detail=str(exc),
                )
                yield {
                    "event": "error",
                    "data": json.dumps({"type": "error", "message": _STREAM_ERROR_MESSAGE}),
                }

        return ServerSentEvent(stream_events(), status_code=200)
