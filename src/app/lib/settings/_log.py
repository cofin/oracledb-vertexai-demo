# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Structured logging configuration settings."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.lib.settings._env import _env_int

if TYPE_CHECKING:
    from litestar.data_extractors import RequestExtractorField, ResponseExtractorField

__all__ = ("LogSettings",)


@dataclass(frozen=True, slots=True)
class LogSettings:
    """Logger configuration."""

    EXCLUDE_PATHS: str = (
        r"^/health|^/static/|^/assets/|^/favicon\.ico|^/@vite|^/@fs|^/node_modules|"
        r"\.(?:js|css|ico|png|jpg|svg|woff2?)$"
    )
    """Regex to exclude paths from logging."""
    INCLUDE_COMPRESSED_BODY: bool = False
    """Include 'body' of compressed responses in log output."""
    LEVEL: int = field(
        default_factory=lambda: (
            int(os.getenv("LOG_LEVEL", "0"))
            if os.getenv("LOG_LEVEL", "").isdigit()
            else logging.getLevelNamesMapping().get(os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
        )
    )
    """Stdlib log level as int. Accepts numeric (e.g. '20') or named (e.g. 'INFO') via LOG_LEVEL env var."""
    SQLSPEC_LEVEL: int = field(default_factory=lambda: _env_int("SQLSPEC_LOG_LEVEL", 20))
    """SQLSpec driver log level (default: INFO=20)."""
    OBFUSCATE_COOKIES: set[str] = field(default_factory=lambda: {"session", "XSRF-TOKEN"})
    """Request cookie keys to obfuscate."""
    OBFUSCATE_HEADERS: set[str] = field(default_factory=lambda: {"Authorization", "X-API-KEY", "X-XSRF-TOKEN"})
    """Request header keys to obfuscate."""
    REQUEST_FIELDS: list[RequestExtractorField] = field(
        default_factory=lambda: ["path", "method", "query", "path_params"]
    )
    """Attributes of the Request to be logged."""
    RESPONSE_FIELDS: list[ResponseExtractorField] = field(default_factory=lambda: ["status_code"])
    """Attributes of the Response to be logged."""
    GRANIAN_ACCESS_LEVEL: int = 30
    """Level to log ASGI access logs."""
    GRANIAN_ERROR_LEVEL: int = 20
    """Level to log ASGI error logs."""
