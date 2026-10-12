# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""OpenTelemetry tracing configuration settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.lib.settings._env import _env_bool

__all__ = ("OpenTelemetrySettings",)


@dataclass(frozen=True)
class OpenTelemetrySettings:
    """OpenTelemetry configuration settings."""

    ENABLED: bool = field(default_factory=lambda: _env_bool("OTEL_ENABLED", True))
    """Enable OpenTelemetry instrumentation middleware by default."""
    SERVICE_NAME: str = field(default_factory=lambda: os.getenv("OTEL_SERVICE_NAME", "cymbal-coffee"))
    """OpenTelemetry service name attribute."""
    EXCLUDE_PATHS: list[str] = field(default_factory=lambda: [r"^/static", r"^/favicon\.ico", r"^/health"])
    """Path regex patterns to exclude from tracing."""
