# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Coffee chat controller for streaming agent conversations and session resets."""

import re
from collections.abc import AsyncIterator

import structlog
from litestar import post
from litestar.exceptions import ValidationException
from litestar.response import ServerSentEvent
from litestar_htmx import HTMXRequest
from litestar_security import PublicController

from app.domain.ai.services import AgentOrchestrationService
from app.domain.chat.controllers._helpers import chat_form_from_request, location_context_from_form
from app.domain.chat.services._telemetry import safe_location_context
from app.domain.chat.session import chat_session_identity, clear_chat_session_identity
from app.lib.di import Inject
from app.utils.serialization import to_json

logger = structlog.get_logger()
_STREAM_ERROR_MESSAGE = "Chat failed while streaming. Please try again."


class CoffeeChatController(PublicController):
    """Coffee chat API controller — JSON for SPA clients, HTML partials for HTMX."""

    @staticmethod
    def validate_message(message: str) -> str:
        """Validate and sanitize user message input.

        Args:
            message: Raw user input text.

        Returns:
            The cleaned and bounded message string.

        Raises:
            ValidationException: If the sanitized message is empty.
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

        Args:
            persona: Requested barista persona identifier.

        Returns:
            The validated persona or the default barista persona.
        """
        if persona not in {"barista", "snob", "scientist", "wellness"}:
            return "barista"
        return persona

    @post(path="/api/chat/stream", name="chat.api.stream")
    async def stream_chat_message(
        self, orchestrator: Inject[AgentOrchestrationService], request: HTMXRequest
    ) -> ServerSentEvent:
        """Stream chat response events for the browser chat UI.

        Args:
            orchestrator: Injected agent orchestration service.
            request: Active HTMX request with form data and session context.

        Returns:
            ServerSentEvent instance streaming JSON event frames.
        """
        data = await chat_form_from_request(request)
        clean_message = self.validate_message(data.message)
        validated_persona = self.validate_persona(data.persona)
        location_context = location_context_from_form(data)
        safe_loc = safe_location_context(location_context)
        user_id, session_id = chat_session_identity(request)

        dynamic_context = (
            f"Persona: {validated_persona}\nLocation Context: {safe_loc}"
            if safe_loc
            else f"Persona: {validated_persona}"
        )

        async def stream_events() -> AsyncIterator[dict[str, str]]:
            try:
                async for frame in orchestrator.stream_conversation_turn(
                    session_id=session_id,
                    user_id=user_id,
                    message=clean_message,
                    services=request,
                    dynamic_context=dynamic_context,
                    persona=validated_persona,
                    location_context=location_context,
                ):
                    frame_type = str(frame.get("type", "message"))
                    yield {"event": frame_type, "data": to_json(frame, as_bytes=False)}
            except Exception as exc:
                await logger.aexception(
                    "Chat stream failed after response started", error_type=type(exc).__name__, detail=str(exc)
                )
                yield {
                    "event": "error",
                    "data": to_json({"type": "error", "message": _STREAM_ERROR_MESSAGE}, as_bytes=False),
                }

        return ServerSentEvent(stream_events(), status_code=200)

    @post(path="/api/chat/session/clear", name="chat.api.clear_session", status_code=200)
    async def clear_chat_session(
        self, orchestrator: Inject[AgentOrchestrationService], request: HTMXRequest
    ) -> dict[str, str]:
        """Clear the anonymous browser's agent chat session.

        Args:
            orchestrator: Injected agent orchestration service.
            request: Active HTMX request.

        Returns:
            JSON confirmation response.
        """
        user_id, session_id = chat_session_identity(request)
        await orchestrator.clear_session(session_id=session_id, user_id=user_id)
        clear_chat_session_identity(request)
        return {"status": "cleared"}
