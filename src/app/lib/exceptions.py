# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Shared application exceptions, HTTP handlers, and credential error classifiers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from google.auth.exceptions import DefaultCredentialsError
from google.genai import errors as genai_errors
from litestar.exceptions import ServiceUnavailableException
from litestar.response import Response
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE

if TYPE_CHECKING:
    from litestar.connection import Request

__all__ = (
    "AIServiceUnconfigured",
    "ApplicationError",
    "ai_service_unconfigured_handler",
    "is_credential_error",
    "is_expected_service_unavailable",
)

_CREDENTIAL_MARKERS: tuple[str, ...] = (
    "api key",
    "credentials",
    "default credentials",
    "could not automatically determine credentials",
    "permission_denied",
    "unauthenticated",
    "unauthorized",
)

_SERVICE_UNAVAILABLE_MARKERS: tuple[str, ...] = (
    *_CREDENTIAL_MARKERS,
    "forbidden",
    "service_disabled",
    "vertex ai api has not been used",
)


class ApplicationError(Exception):
    """Base exception for application-level domain and infrastructure errors."""


class AIServiceUnconfigured(ServiceUnavailableException, ApplicationError):
    """Raised when Vertex AI or Google GenAI credentials are missing or invalid."""


def ai_service_unconfigured_handler(
    request: Request[Any, Any, Any], exc: AIServiceUnconfigured
) -> Response[dict[str, Any]]:
    """Render an HTTP 503 JSON response when AI credentials are unconfigured."""
    del request
    detail = exc.detail or str(exc) or "Vertex AI service is not configured."
    return Response(
        content={"detail": detail, "status_code": HTTP_503_SERVICE_UNAVAILABLE},
        status_code=HTTP_503_SERVICE_UNAVAILABLE,
    )


def is_credential_error(exc: BaseException) -> bool:
    """Return True when an exception indicates missing or invalid Google Cloud/GenAI credentials."""
    if isinstance(exc, AIServiceUnconfigured | DefaultCredentialsError):
        return True
    text = str(exc).lower()
    if isinstance(exc, genai_errors.ClientError):
        return any(marker in text for marker in _CREDENTIAL_MARKERS)
    return any(marker in text for marker in _CREDENTIAL_MARKERS)


def is_expected_service_unavailable(exc: BaseException) -> bool:
    """Return True when an exception represents an expected external AI/credential unavailability."""
    if is_credential_error(exc):
        return True
    text = str(exc).lower()
    if isinstance(exc, genai_errors.ClientError):
        return any(marker in text for marker in _SERVICE_UNAVAILABLE_MARKERS)
    return any(marker in text for marker in ("service_disabled", "vertex ai api has not been used"))
