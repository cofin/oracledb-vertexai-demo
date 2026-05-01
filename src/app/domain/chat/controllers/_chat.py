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
from app.domain.chat.session import adk_session_identity, clear_adk_session_identity
from app.lib.di import Inject

logger = structlog.get_logger()
_STREAM_ERROR_MESSAGE = "Chat failed while streaming. Please try again."
_MIN_LATITUDE = -90.0
_MAX_LATITUDE = 90.0
_MIN_LONGITUDE = -180.0
_MAX_LONGITUDE = 180.0


@dataclass
class CoffeeChatForm:
    message: str
    persona: str = "enthusiast"
    location_consent: bool = False
    latitude: float | None = None
    longitude: float | None = None
    accuracy: float | None = None
    city: str = ""
    state: str = ""
    zip_code: str = ""
    store_name: str = ""


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


_MISSING = object()


def _payload_raw(payload: Any, *keys: str, default: Any = "") -> Any:
    getter = getattr(payload, "get", None)
    if not callable(getter):
        return default
    value = _MISSING
    for key in keys:
        value = getter(key, _MISSING)
        if value is not _MISSING:
            break
    if value is _MISSING:
        value = default
    if isinstance(value, list | tuple):
        value = value[0] if value else default
    return default if value is None else value


def _payload_value(payload: Any, *keys: str, default: str = "") -> str:
    value = _payload_raw(payload, *keys, default=default)
    return str(value or default)


def _payload_bool(payload: Any, *keys: str, default: bool = False) -> bool:
    value = _payload_raw(payload, *keys, default=default)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "on"}
    return default


def _payload_float(payload: Any, *keys: str) -> float | None:
    value = _payload_raw(payload, *keys, default=None)
    if value is None or (isinstance(value, str) and not value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationException(detail="Location coordinates must be numbers") from exc


def _location_text(value: str) -> str:
    return value.replace("\x00", "").strip()[:100]


def _location_context_from_form(data: CoffeeChatForm) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for key, value in (
        ("city", data.city),
        ("state", data.state),
        ("zip_code", data.zip_code),
        ("store_name", data.store_name),
    ):
        cleaned = _location_text(value)
        if cleaned:
            context[key] = cleaned

    if not data.location_consent:
        return context

    if data.latitude is None and data.longitude is None:
        return context
    if data.latitude is None or data.longitude is None:
        raise ValidationException(detail="Location coordinates require latitude and longitude")
    if not _MIN_LATITUDE <= data.latitude <= _MAX_LATITUDE or not (
        _MIN_LONGITUDE <= data.longitude <= _MAX_LONGITUDE
    ):
        raise ValidationException(detail="Invalid location coordinates")

    coordinates = {"latitude": data.latitude, "longitude": data.longitude}
    if data.accuracy is not None:
        coordinates["accuracy_meters"] = max(data.accuracy, 0.0)
    context["coordinates"] = coordinates
    return context


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
        persona=_payload_value(payload, "persona", default="enthusiast"),
        location_consent=_payload_bool(payload, "locationConsent", "location_consent"),
        latitude=_payload_float(payload, "latitude", "lat"),
        longitude=_payload_float(payload, "longitude", "lng", "lon"),
        accuracy=_payload_float(payload, "accuracy", "accuracyMeters", "accuracy_meters"),
        city=_payload_value(payload, "city"),
        state=_payload_value(payload, "state"),
        zip_code=_payload_value(payload, "zipCode", "zip_code", "zip"),
        store_name=_payload_value(payload, "storeName", "store_name"),
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
            location_context = _location_context_from_form(data)
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
                store_results=result.get("store_results", []),
                inventory_results=result.get("inventory_results", []),
                map_actions=result.get("map_actions", []),
                location_context=result.get("location_context", {}),
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
                location_context = _location_context_from_form(data)
                user_id, session_id = adk_session_identity(request)
                async for event in adk_runner.stream_request(
                    query=clean_message,
                    user_id=user_id,
                    session_id=session_id,
                    persona=validated_persona,
                    tools_service=tools_service,
                    location_context=location_context,
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
