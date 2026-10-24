# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for `build_security_config` geolocation and Google Maps frame policies."""

from __future__ import annotations

from app.lib.security import build_security_config
from app.lib.settings import MapsSettings, Settings


def test_security_headers_default_to_geolocation_self_without_csp() -> None:
    """Verify `build_security_config` sets `Permissions-Policy: geolocation=(self)` without CSP when embed is disabled."""
    security_config = build_security_config(Settings(maps=MapsSettings(ENABLE_EMBED=False, EMBED_API_KEY="")))
    assert security_config.headers is not None
    headers = security_config.headers.static

    assert headers["Permissions-Policy"] == "geolocation=(self)"
    assert "Content-Security-Policy" not in headers


def test_security_headers_allow_google_maps_frames_only_when_embed_enabled() -> None:
    """Verify `build_security_config` adds Google Maps `frame-src` CSP when embed is enabled."""
    security_config = build_security_config(
        Settings(maps=MapsSettings(ENABLE_EMBED=True, EMBED_API_KEY="test-maps-embed-key"))
    )
    assert security_config.headers is not None
    headers = security_config.headers.static

    assert headers["Permissions-Policy"] == "geolocation=(self)"
    assert headers["Content-Security-Policy"] == "frame-src 'self' https://www.google.com https://www.google.com/maps/;"
    assert "geolocation" not in headers["Content-Security-Policy"]
