# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for BeforeSendHandler and StructlogMiddleware ASGI behavior."""

from __future__ import annotations

from typing import Any

import pytest
from litestar.enums import ScopeType

from app.lib.log import _middleware
from app.lib.log._middleware import BeforeSendHandler, StructlogMiddleware

pytestmark = pytest.mark.anyio


def test_middleware_module_does_not_freeze_settings_singleton() -> None:
    """Verify _middleware does not bind a module-level settings singleton at import time."""
    assert not hasattr(_middleware, "settings")


async def test_before_send_handler_handles_response_start_without_headers() -> None:
    """Verify BeforeSendHandler safely mutates http.response.start messages omitting headers."""
    handler = BeforeSendHandler()
    message: dict[str, Any] = {"type": "http.response.start", "status": 204}
    scope: dict[str, Any] = {
        "type": ScopeType.HTTP,
        "path": "/api/chat/",
        "method": "POST",
        "state": {},
    }

    await handler(message, scope)  # type: ignore[arg-type]

    assert isinstance(message.get("headers"), list)
    header_names = {name.lower() for name, _value in message["headers"]}
    assert b"permissions-policy" in header_names
    assert scope["state"]["http.response.start"] is message


async def test_structlog_middleware_clears_contextvars_and_calls_app() -> None:
    """Verify StructlogMiddleware clears structlog contextvars before invoking inner ASGI app."""
    called = False

    async def fake_app(scope: Any, receive: Any, send: Any) -> None:
        nonlocal called
        del scope, receive, send
        called = True

    wrapped = StructlogMiddleware(fake_app)
    await wrapped({"type": "http"}, None, None)  # type: ignore[arg-type]
    assert called is True
