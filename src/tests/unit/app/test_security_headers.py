# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from types import SimpleNamespace


def test_security_headers_default_to_geolocation_self_without_csp() -> None:
    from app.lib.log import build_security_headers

    headers = build_security_headers(SimpleNamespace(embed_enabled=False))

    assert headers["Permissions-Policy"] == "geolocation=(self)"
    assert "Content-Security-Policy" not in headers


def test_security_headers_allow_google_maps_frames_only_when_embed_enabled() -> None:
    from app.lib.log import build_security_headers

    headers = build_security_headers(SimpleNamespace(embed_enabled=True))

    assert headers["Permissions-Policy"] == "geolocation=(self)"
    assert headers["Content-Security-Policy"] == "frame-src 'self' https://www.google.com https://www.google.com/maps/;"
    assert "geolocation" not in headers["Content-Security-Policy"]
