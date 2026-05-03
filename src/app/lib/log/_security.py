# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Security header helpers for ASGI response logging hooks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from app.lib.settings import get_settings

if TYPE_CHECKING:
    from litestar.types.asgi_types import Message


def build_security_headers(maps_settings: Any | None = None) -> dict[str, str]:
    """Build browser security headers for location and optional Maps Embed."""
    maps = maps_settings or get_settings().maps
    headers = {"Permissions-Policy": "geolocation=(self)"}
    if maps.embed_enabled:
        headers["Content-Security-Policy"] = "frame-src 'self' https://www.google.com https://www.google.com/maps/;"
    return headers


def _set_response_header(message: Message, name: str, value: str) -> None:
    message_dict = cast("dict[str, Any]", message)
    headers = cast("list[tuple[bytes, bytes]] | None", message_dict.get("headers"))
    if headers is None:
        headers = []
        message_dict["headers"] = headers
    encoded_name = name.lower().encode()
    encoded_value = value.encode()
    for index, (header_name, _header_value) in enumerate(headers):
        if header_name.lower() == encoded_name:
            headers[index] = (header_name, encoded_value)
            return
    headers.append((encoded_name, encoded_value))


def apply_security_headers(message: Message) -> None:
    """Mutate an ASGI response-start message with app security headers."""
    existing_csp = False
    message_dict = cast("dict[str, Any]", message)
    headers = cast("list[tuple[bytes, bytes]]", message_dict.get("headers", []))
    for header_name, _header_value in headers:
        if header_name.lower() == b"content-security-policy":
            existing_csp = True
            break
    for name, value in build_security_headers().items():
        if name == "Content-Security-Policy" and existing_csp:
            continue
        _set_response_header(message, name, value)
