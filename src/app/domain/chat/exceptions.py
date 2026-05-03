# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Typed exceptions raised by the chat domain."""

from litestar.exceptions import ServiceUnavailableException


class AIServiceUnconfigured(ServiceUnavailableException):
    """Raised when Vertex AI / google-genai credentials are missing or invalid."""


__all__ = ("AIServiceUnconfigured",)
