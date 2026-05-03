# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Public logging utilities for Cymbal Coffee."""

from __future__ import annotations

import sys
from contextvars import ContextVar
from functools import lru_cache
from typing import Any

import structlog

from app.lib.log._filters import (
    SuppressADKWarningsFilter,
    SuppressAsyncioTaskExceptionFilter,
    SuppressGranianExcInfoFilter,
)
from app.lib.log._middleware import (
    HTTP_RESPONSE_BODY,
    HTTP_RESPONSE_START,
    REQUEST_BODY_FIELD,
    BeforeSendHandler,
    StructlogMiddleware,
    after_exception_hook_handler,
)
from app.lib.log._processors import (
    EventFilter,
    add_google_cloud_attributes,
    add_logger_name_safe,
    add_logger_source,
    stdlib_json_serializer,
    stdlib_logger_processors,
    structlog_json_serializer,
    structlog_processors,
)
from app.lib.log._security import apply_security_headers, build_security_headers

LOGGER = structlog.getLogger()

_cli_mode: ContextVar[bool] = ContextVar("cli_mode", default=False)


@lru_cache
def is_tty() -> bool:
    return bool(sys.stderr.isatty() or sys.stdout.isatty())


def set_cli_mode(enabled: bool = True) -> None:
    """Set CLI mode to suppress structlog output in favor of rich console."""
    _cli_mode.set(enabled)


def is_cli_mode() -> bool:
    """Check if CLI mode is enabled."""
    return _cli_mode.get()


async def log_info(message: str, *, use_logger: bool = True, **kwargs: Any) -> None:
    """Log an info message, respecting CLI mode."""
    if use_logger and not is_cli_mode():
        await LOGGER.ainfo(message, **kwargs)


async def log_warning(message: str, *, use_logger: bool = True, **kwargs: Any) -> None:
    """Log a warning message, respecting CLI mode."""
    if use_logger and not is_cli_mode():
        await LOGGER.awarning(message, **kwargs)


async def log_error(message: str, *, use_logger: bool = True, **kwargs: Any) -> None:
    """Log an error message, respecting CLI mode."""
    if use_logger and not is_cli_mode():
        await LOGGER.aerror(message, **kwargs)


__all__ = (
    "HTTP_RESPONSE_BODY",
    "HTTP_RESPONSE_START",
    "REQUEST_BODY_FIELD",
    "BeforeSendHandler",
    "EventFilter",
    "StructlogMiddleware",
    "SuppressADKWarningsFilter",
    "SuppressAsyncioTaskExceptionFilter",
    "SuppressGranianExcInfoFilter",
    "add_google_cloud_attributes",
    "add_logger_name_safe",
    "add_logger_source",
    "after_exception_hook_handler",
    "apply_security_headers",
    "build_security_headers",
    "is_cli_mode",
    "is_tty",
    "log_error",
    "log_info",
    "log_warning",
    "set_cli_mode",
    "stdlib_json_serializer",
    "stdlib_logger_processors",
    "structlog_json_serializer",
    "structlog_processors",
)
