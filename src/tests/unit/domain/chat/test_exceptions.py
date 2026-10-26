# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for typed AI configuration exceptions and provider guards."""

from __future__ import annotations

import pytest

from app.ioc import AIProvider
from app.lib.exceptions import AIServiceUnconfigured
from app.lib.settings import AISettings, Settings


@pytest.mark.parametrize("placeholder_project", ["", "demo-project", "your-project-id", "placeholder"])
def test_provide_genai_client_raises_on_placeholder_credentials(placeholder_project: str) -> None:
    """Verify AIProvider.provide_genai_client raises AIServiceUnconfigured on placeholder project IDs."""
    Settings.from_env.cache_clear()
    ai_settings = AISettings(project_id=placeholder_project, location="global", gcp_region="us-central1", api_key=None)

    provider = AIProvider()
    with pytest.raises(AIServiceUnconfigured) as exc_info:
        provider.provide_genai_client(ai_settings)
    assert exc_info.value.status_code == 503
