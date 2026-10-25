# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Coffee chat controller for streaming agent conversations and session resets."""

import re
from collections.abc import AsyncIterator
from typing import ClassVar

import structlog
from litestar import post
from litestar.exceptions import ValidationException
from litestar.response import ServerSentEvent
from litestar_htmx import HTMXRequest
from litestar_security import AuthenticationPolicy, PublicController, exclude

from app.domain.ai.services import AgentOrchestrationService
from app.domain.chat._session import chat_session_identity, clear_chat_session_id
from app.domain.chat.controllers._helpers import chat_form_from_request, location_context_from_form
from app.lib.di import Inject
from app.lib.exceptions import AIServiceUnconfigured, is_credential_error, is_expected_service_unavailable
from app.utils.serialization import encode_json

__all__ = ("CoffeeChatController",)

logger = structlog.get_logger()
_STREAM_ERROR_MESSAGE = "Chat failed while streaming. Please try again."
_UNCONFIGURED_STREAM_MESSAGE = "Vertex AI service is not configured."


class CoffeeChatController(PublicController):
    """Coffee chat API controller — JSON for SPA clients, HTML partials for HTMX."""

    auth: ClassVar[AuthenticationPolicy] = exclude()

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

    @post(path="/api/chat/stream", name="chat.api.stream", opt={"exclude_from_csrf": False})
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
        user_id, session_id = chat_session_identity(request)

        async def stream_events() -> AsyncIterator[dict[str, str]]:
            try:
                async for frame in orchestrator.stream_conversation_turn(
                    session_id=session_id,
                    user_id=user_id,
                    message=clean_message,
                    services=request,
                    persona=validated_persona,
                    location_context=location_context,
                ):
                    frame_type = str(frame.get("type", "message"))
                    yield {"event": frame_type, "data": encode_json(frame)}
            except Exception as exc:
                if is_credential_error(exc) or is_expected_service_unavailable(exc):
                    detail = (
                        exc.detail
                        if isinstance(exc, AIServiceUnconfigured) and exc.detail
                        else _UNCONFIGURED_STREAM_MESSAGE
                    )
                    await logger.awarning(
                        "Chat stream unavailable due to AI configuration", error_type=type(exc).__name__, detail=detail
                    )
                    yield {"event": "error", "data": encode_json({"type": "error", "message": detail})}
                else:
                    await logger.aexception(
                        "Chat stream failed after response started", error_type=type(exc).__name__, detail=str(exc)
                    )
                    yield {"event": "error", "data": encode_json({"type": "error", "message": _STREAM_ERROR_MESSAGE})}

        return ServerSentEvent(stream_events(), status_code=200)

    @post(
        path="/api/chat/session/clear", name="chat.api.clear_session", status_code=200, opt={"exclude_from_csrf": False}
    )
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
        clear_chat_session_id(request)
        return {"status": "cleared"}
