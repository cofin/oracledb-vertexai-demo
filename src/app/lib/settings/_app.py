# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Application-level configuration settings."""

from __future__ import annotations

import binascii
import os
from dataclasses import dataclass, field

from app.lib.settings._env import _env_bool, _env_cors

__all__ = ("AppSettings",)


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Application configuration."""

    DEBUG: bool = field(default_factory=lambda: _env_bool("LITESTAR_DEBUG", False))
    """Run ``Litestar`` with ``debug=True``."""
    SECRET_KEY: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY", binascii.hexlify(os.urandom(32)).decode(encoding="utf-8"))
    )
    """Application secret key."""
    NAME: str = field(default_factory=lambda: "app")
    """Application name."""
    URL: str = field(default_factory=lambda: os.getenv("APP_URL", "http://localhost:8000"))
    """Public base URL of the application."""
    ALLOWED_CORS_ORIGINS: list[str] = field(default_factory=lambda: _env_cors("ALLOWED_CORS_ORIGINS", '["*"]'))
    """Allowed CORS Origins."""
    CSRF_COOKIE_NAME: str = field(default_factory=lambda: "XSRF-TOKEN")
    """CSRF Cookie Name."""
    CSRF_HEADER_NAME: str = field(default_factory=lambda: "X-CSRFToken")
    """CSRF header name forwarded by HTMX requests; must match the JS helper default."""
    CSRF_COOKIE_SECURE: bool = field(default_factory=lambda: False)
    """CSRF Secure Cookie."""
    MCP_API_KEY: str | None = field(default_factory=lambda: (os.getenv("MCP_API_KEY") or "").strip() or None)
    """Optional shared secret for authenticating machine requests to ``/mcp`` and ``/a2a``."""
