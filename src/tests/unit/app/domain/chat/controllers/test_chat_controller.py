# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for CoffeeChatController validation, streaming, and location privacy."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import MagicMock

import pytest
from litestar.exceptions import ValidationException

from app.domain.chat.controllers._chat import CoffeeChatController
from app.domain.chat.controllers._helpers import CoffeeChatForm, location_context_from_form

pytestmark = pytest.mark.anyio


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
    captured_kwargs: dict[str, Any] = {}

    class _StubOrchestrator:
        async def stream_conversation_turn(self, **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
            captured_kwargs.update(kwargs)
            yield {"type": "session", "session_id": "s1"}
            yield {"type": "final", "session_id": "s1", "answer": "Hello!"}

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

    sse_response = await controller.stream_chat_message.fn(
        controller, orchestrator=_StubOrchestrator(), request=request
    )
    chunks = [chunk async for chunk in sse_response.iterator]
    assert len(chunks) == 2
    assert captured_kwargs["persona"] == "barista"
    assert captured_kwargs["location_context"]["coordinates"]["latitude"] == 32.7478
    assert "32.7478" not in str(captured_kwargs.get("dynamic_context") or "")
