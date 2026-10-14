# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for typed AI configuration exceptions and provider guards."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.domain.chat.exceptions import AIServiceUnconfigured
from app.ioc import IntegrationsProvider


def test_ai_service_unconfigured_is_exception_subclass() -> None:
    """Verify AIServiceUnconfigured is a 503 ServiceUnavailableException subclass."""
    assert issubclass(AIServiceUnconfigured, Exception)
    exc = AIServiceUnconfigured("missing key")
    assert isinstance(exc, Exception)
    assert exc.status_code == 503


def test_ai_service_unconfigured_carries_message() -> None:
    """Verify AIServiceUnconfigured preserves detail message."""
    exc = AIServiceUnconfigured("Set GOOGLE_API_KEY or VERTEX_AI_API_KEY")
    assert "GOOGLE_API_KEY" in str(exc)


@pytest.mark.parametrize("placeholder_project", ["", "demo-project", "your-project-id", "placeholder"])
def test_provide_genai_client_raises_on_placeholder_credentials(
    monkeypatch: pytest.MonkeyPatch, placeholder_project: str
) -> None:
    """Verify IntegrationsProvider.provide_genai_client raises AIServiceUnconfigured on placeholder project IDs."""
    fake_settings = MagicMock()
    fake_settings.ai.project_id = placeholder_project
    fake_settings.ai.location = "global"
    fake_settings.ai.gcp_region = "us-central1"
    fake_settings.ai.resolve_location.return_value = "global"
    fake_settings.ai.api_key = None
    monkeypatch.setattr("app.ioc.get_settings", lambda: fake_settings)

    provider = IntegrationsProvider()
    with pytest.raises(AIServiceUnconfigured) as exc_info:
        provider.provide_genai_client()
    assert exc_info.value.status_code == 503
