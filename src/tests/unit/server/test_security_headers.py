# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for `build_security_headers` geolocation and Google Maps frame policies."""

from __future__ import annotations

from types import SimpleNamespace

from app.lib.log import build_security_headers


def test_security_headers_default_to_geolocation_self_without_csp() -> None:
    """Verify `build_security_headers` sets `Permissions-Policy: geolocation=(self)` without CSP when embed is disabled."""
    headers = build_security_headers(SimpleNamespace(embed_enabled=False))

    assert headers["Permissions-Policy"] == "geolocation=(self)"
    assert "Content-Security-Policy" not in headers


def test_security_headers_allow_google_maps_frames_only_when_embed_enabled() -> None:
    """Verify `build_security_headers` adds Google Maps `frame-src` CSP when embed is enabled."""
    headers = build_security_headers(SimpleNamespace(embed_enabled=True))

    assert headers["Permissions-Policy"] == "geolocation=(self)"
    assert headers["Content-Security-Policy"] == "frame-src 'self' https://www.google.com https://www.google.com/maps/;"
    assert "geolocation" not in headers["Content-Security-Policy"]
