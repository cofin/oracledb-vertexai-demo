# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Typed exceptions raised by the chat domain."""

from __future__ import annotations


def test_ai_service_unconfigured_is_exception_subclass() -> None:
    from app.domain.chat.exceptions import AIServiceUnconfigured

    assert issubclass(AIServiceUnconfigured, Exception)
    assert isinstance(AIServiceUnconfigured("missing key"), Exception)


def test_ai_service_unconfigured_carries_message() -> None:
    from app.domain.chat.exceptions import AIServiceUnconfigured

    exc = AIServiceUnconfigured("Set GOOGLE_API_KEY or VERTEX_AI_API_KEY")
    assert "GOOGLE_API_KEY" in str(exc)
