# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for CoffeeChatController validation, streaming, and location privacy."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import MagicMock

import pytest
from litestar.exceptions import ValidationException

from app.domain.chat import _session as chat_session_module
from app.domain.chat._session import (
    CHAT_SESSION_KEY,
    CHAT_USER_KEY,
    chat_session_identity,
    clear_chat_session_id,
    get_chat_owner_id,
    get_or_create_chat_session_id,
)
from app.domain.chat.controllers._chat import CoffeeChatController
from app.domain.chat.controllers._helpers import location_context_from_form
from app.domain.chat.schemas import CoffeeChatForm
from app.lib.exceptions import AIServiceUnconfigured
from app.lib.schema import FrozenBaseStruct

pytestmark = pytest.mark.anyio


class _StubOrchestrator:
    """Stub orchestrator recording stream_conversation_turn arguments."""

    def __init__(self) -> None:
        self.captured_kwargs: dict[str, Any] = {}

    async def stream_conversation_turn(self, **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        self.captured_kwargs.update(kwargs)
        yield {"type": "session", "session_id": "s1"}
        yield {"type": "final", "session_id": "s1", "answer": "Hello!"}


class _UnconfiguredOrchestrator:
    """Stub orchestrator raising AIServiceUnconfigured during stream iteration."""

    async def stream_conversation_turn(self, **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        del kwargs
        empty: tuple[dict[str, Any], ...] = ()
        for frame in empty:
            yield frame
        raise AIServiceUnconfigured("Configure VERTEX_AI_PROJECT_ID")


def test_validate_message_strips_html_and_rejects_empty() -> None:
    """Verify validate_message strips HTML tags and raises ValidationException when empty."""
    assert CoffeeChatController.validate_message("<b>Hello</b> coffee") == "Hello coffee"
    with pytest.raises(ValidationException):
        CoffeeChatController.validate_message("   <script></script>  ")


def test_validate_persona_defaults_unknown_to_barista() -> None:
    """Verify validate_persona keeps valid personas and defaults unknown ones to barista."""
    assert CoffeeChatController.validate_persona("snob") == "snob"
    assert CoffeeChatController.validate_persona("unknown-persona") == "barista"


def test_location_context_from_form_requires_consent_for_coordinates() -> None:
    """Verify browser coordinates are ignored unless location_consent is True."""
    without_consent = CoffeeChatForm(
        message="closest store", city="Dallas", location_consent=False, latitude=32.75, longitude=-96.83
    )
    ctx_no_consent = location_context_from_form(without_consent)
    assert ctx_no_consent == {"city": "Dallas"}
    assert "coordinates" not in ctx_no_consent

    with_consent = CoffeeChatForm(
        message="closest store", city="Dallas", location_consent=True, latitude=32.75, longitude=-96.83, accuracy=10.0
    )
    ctx_consent = location_context_from_form(with_consent)
    assert ctx_consent["coordinates"] == {"latitude": 32.75, "longitude": -96.83, "accuracy_meters": 10.0}


async def test_stream_chat_message_passes_masked_dynamic_context() -> None:
    """Verify CoffeeChatController passes location_context separately and masks dynamic_context."""
    controller = CoffeeChatController(owner=MagicMock())
    stub_orchestrator = _StubOrchestrator()

    request = MagicMock()
    request.headers = {"content-type": "application/json"}
    request.session = {"chat_user_id": "u1", "chat_session_id": "s1"}

    async def _json() -> dict[str, Any]:
        return {
            "message": "Where is Bishop Arts?",
            "persona": "barista",
            "locationConsent": True,
            "latitude": 32.7478,
            "longitude": -96.8289,
            "city": "Dallas",
        }

    request.json = _json

    sse_response = await controller.stream_chat_message.fn(controller, orchestrator=stub_orchestrator, request=request)
    chunks = [chunk async for chunk in sse_response.iterator]
    assert len(chunks) == 2
    assert stub_orchestrator.captured_kwargs["persona"] == "barista"
    assert stub_orchestrator.captured_kwargs["location_context"]["coordinates"]["latitude"] == 32.7478
    assert "32.7478" not in str(stub_orchestrator.captured_kwargs.get("dynamic_context") or "")


def test_coffee_chat_form_is_frozen_struct_and_session_module_drops_adk_constants() -> None:
    """Verify CoffeeChatForm inherits from FrozenBaseStruct and chat._session exposes zero ADK constants."""
    assert issubclass(CoffeeChatForm, FrozenBaseStruct)
    form = CoffeeChatForm(message="hello")
    with pytest.raises(AttributeError):
        setattr(form, "message", "mutated")

    for legacy_name in (
        "ADK_SESSION_KEY",
        "ADK_USER_KEY",
        "ADK_USER_ID",
        "adk_session_identity",
        "clear_adk_session_identity",
    ):
        assert not hasattr(chat_session_module, legacy_name)

    request = MagicMock()
    request.session = {}
    request.get_session_id.return_value = "sid-42"

    session_id = get_or_create_chat_session_id(request)
    owner_id = get_chat_owner_id(request)
    assert session_id == "sid-42"
    assert owner_id == "web:sid-42"
    assert request.session[CHAT_SESSION_KEY] == "sid-42"
    assert request.session[CHAT_USER_KEY] == "web:sid-42"
    assert chat_session_identity(request) == ("web:sid-42", "sid-42")

    clear_chat_session_id(request)
    assert CHAT_SESSION_KEY not in request.session
    assert CHAT_USER_KEY not in request.session


async def test_stream_chat_message_emits_error_frame_on_ai_service_unconfigured() -> None:
    """Verify AIServiceUnconfigured raised during stream iteration emits a clean SSE error frame."""
    controller = CoffeeChatController(owner=MagicMock())
    request = MagicMock()
    request.headers = {"content-type": "application/json"}
    request.session = {"chat_user_id": "u1", "chat_session_id": "s1"}

    async def _json() -> dict[str, Any]:
        return {"message": "Recommend an espresso", "persona": "barista"}

    request.json = _json
    sse_response = await controller.stream_chat_message.fn(
        controller, orchestrator=_UnconfiguredOrchestrator(), request=request
    )
    chunks = [chunk async for chunk in sse_response.iterator]
    assert len(chunks) == 1
    assert "event: error" in str(chunks[0])
    assert "Configure VERTEX_AI_PROJECT_ID" in str(chunks[0])
