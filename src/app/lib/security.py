# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Application security policy, headers, and optional MCP/A2A API key authentication."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from litestar.openapi.spec import SecurityScheme
from litestar_security import (
    Authenticated,
    AuthenticationEvidence,
    AuthenticationMechanism,
    AuthenticationOutcome,
    CredentialExtraction,
    IdentityResolution,
    InvalidCredentials,
    NoCredentials,
    PresentedCredential,
    Principal,
    SecurityConfig,
    SecurityHeadersConfig,
)

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

    from app.lib.settings import Settings

__all__ = ("build_security_config",)


def build_security_config(settings: Settings) -> SecurityConfig[Any]:
    """Build the application SecurityConfig with hardened headers and optional API-key auth.

    Args:
        settings: Resolved application settings instance.

    Returns:
        Configured SecurityConfig instance for SecurityPlugin.
    """
    hardened = SecurityHeadersConfig.hardened()
    static_headers: dict[str, str] = {**hardened.static, "Permissions-Policy": "geolocation=(self)"}
    if settings.maps.embed_enabled:
        static_headers["Content-Security-Policy"] = (
            "frame-src 'self' https://www.google.com https://www.google.com/maps/;"
        )
    headers = SecurityHeadersConfig(static=static_headers)

    expected_key = (settings.app.MCP_API_KEY or "").strip()
    if not expected_key:
        return SecurityConfig(headers=headers, exclude=[r"^/static"])

    return SecurityConfig(
        headers=headers,
        slots=(_ApiKeySlot(),),
        mechanisms=(
            AuthenticationMechanism(
                authenticator=_ApiKeyVerifier(expected_key=expected_key),
                resolver=_ApiKeyResolver(),
                scheme_name="ApiKeyAuth",
                security_scheme=SecurityScheme(
                    type="apiKey",
                    name="X-API-Key",
                    security_scheme_in="header",
                    description="Shared API key for MCP and A2A endpoints.",
                ),
            ),
        ),
        exclude=[r"^/static"],
    )


@dataclass(slots=True)
class _ApiKeySlot:
    """CredentialSlot extracting an API key from X-API-Key or Authorization Bearer header."""

    name: str = "header.x-api-key"

    def extract(self, connection: ASGIConnection[Any, Any, Any, Any]) -> CredentialExtraction[str]:
        """Extract presented API key credential from request headers."""
        raw_key = connection.headers.get("x-api-key")
        if raw_key is None:
            auth_header = connection.headers.get("authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                raw_key = auth_header[7:]
        if raw_key is None:
            return NoCredentials()
        token = raw_key.strip()
        if not token:
            return InvalidCredentials()
        return PresentedCredential(value=token)


@dataclass(slots=True)
class _ApiKeyVerifier:
    """CredentialVerifier comparing presented API key against configured MCP_API_KEY."""

    expected_key: str
    name: str = "api-key"
    slot: str = "header.x-api-key"
    participates_by_default: bool = False

    async def authenticate(
        self, credential: str, connection: ASGIConnection[Any, Any, Any, Any]
    ) -> AuthenticationOutcome[str]:
        """Verify the presented API key in constant time."""
        del connection
        if secrets.compare_digest(credential, self.expected_key):
            return Authenticated(
                claims="mcp-client",
                evidence=AuthenticationEvidence(
                    mechanism=self.name,
                    slot=self.slot,
                    authenticated_at=datetime.now(UTC),
                    methods=frozenset({self.name}),
                ),
            )
        return InvalidCredentials()


@dataclass(frozen=True, slots=True)
class _ApiKeyResolver:
    """IdentityResolver mapping verified API key claims into an authenticated Principal."""

    async def resolve(self, claims: str) -> IdentityResolution[dict[str, object]]:
        """Resolve verified API key claims into a Principal."""
        user_payload: dict[str, object] = {"id": claims, "is_authenticated": True}
        return Principal(id=claims, user=user_payload)
