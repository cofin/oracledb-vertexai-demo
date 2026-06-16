# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

import re
from collections.abc import AsyncIterator

import structlog
from litestar import Controller, Response, post
from litestar.exceptions import ValidationException
from litestar.plugins.htmx import HTMXRequest
from litestar.response import ServerSentEvent

from app.domain.chat.controllers._helpers import chat_form_from_request, location_context_from_form
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
