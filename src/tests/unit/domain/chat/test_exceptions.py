# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for typed AI configuration exceptions and provider guards."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.ioc import AIProvider
from app.lib.exceptions import AIServiceUnconfigured, ApplicationError, ai_service_unconfigured_handler
from app.lib.settings import AISettings, Settings


def test_ai_service_unconfigured_is_exception_subclass() -> None:
    """Verify AIServiceUnconfigured inherits from ServiceUnavailableException and ApplicationError."""
    assert issubclass(AIServiceUnconfigured, Exception)
    assert issubclass(AIServiceUnconfigured, ApplicationError)
    exc = AIServiceUnconfigured("missing key")
    assert isinstance(exc, ApplicationError)
    assert exc.status_code == 503


def test_ai_service_unconfigured_handler_returns_503_payload() -> None:
    """Verify ai_service_unconfigured_handler preserves detail message and 503 status."""
    exc = AIServiceUnconfigured("Set GOOGLE_API_KEY or VERTEX_AI_API_KEY")
    response = ai_service_unconfigured_handler(MagicMock(), exc)
    assert response.status_code == 503
    assert "GOOGLE_API_KEY" in response.content["detail"]


@pytest.mark.parametrize("placeholder_project", ["", "demo-project", "your-project-id", "placeholder"])
def test_provide_genai_client_raises_on_placeholder_credentials(placeholder_project: str) -> None:
    """Verify AIProvider.provide_genai_client raises AIServiceUnconfigured on placeholder project IDs."""
    Settings.from_env.cache_clear()
    ai_settings = AISettings(project_id=placeholder_project, location="global", gcp_region="us-central1", api_key=None)

    provider = AIProvider()
    with pytest.raises(AIServiceUnconfigured) as exc_info:
        provider.provide_genai_client(ai_settings)
    assert exc_info.value.status_code == 503
