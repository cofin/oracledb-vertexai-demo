# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the public logging facade."""

from __future__ import annotations

from app.lib.log import (
    BeforeSendHandler,
    EventFilter,
    StructlogMiddleware,
    SuppressADKWarningsFilter,
    SuppressAsyncioTaskExceptionFilter,
    SuppressGranianExcInfoFilter,
    after_exception_hook_handler,
    build_security_headers,
    stdlib_json_serializer,
    structlog_json_serializer,
)


def test_log_public_surface_reexports_focused_private_implementations() -> None:
    """The public log module should read as an API facade over focused helpers."""
    assert SuppressADKWarningsFilter.__module__ == "app.lib._log_filters"
    assert SuppressAsyncioTaskExceptionFilter.__module__ == "app.lib._log_filters"
    assert SuppressGranianExcInfoFilter.__module__ == "app.lib._log_filters"
    assert build_security_headers.__module__ == "app.lib._log_security"
    assert EventFilter.__module__ == "app.lib._log_processors"
    assert structlog_json_serializer.__module__ == "app.lib._log_processors"
    assert stdlib_json_serializer.__module__ == "app.lib._log_processors"
    assert StructlogMiddleware.__module__ == "app.lib._log_middleware"
    assert BeforeSendHandler.__module__ == "app.lib._log_middleware"
    assert after_exception_hook_handler.__module__ == "app.lib._log_middleware"
