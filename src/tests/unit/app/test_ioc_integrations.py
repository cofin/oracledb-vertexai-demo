# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for ``IntegrationsProvider`` runtime wiring."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import app.ioc as ioc_module
from app.domain.ai.runtime import AgentRuntime, GeminiModelClient, SpecTree
from app.domain.system.services import PersonaManager


def test_integrations_provider_builds_model_client_from_injected_client(monkeypatch: Any) -> None:
    """Verify IntegrationsProvider constructs a GeminiModelClient from Client."""
    provider = ioc_module.IntegrationsProvider()
    sentinel_client = MagicMock()

    model_client = provider.provide_model_client(sentinel_client)

    assert isinstance(model_client, GeminiModelClient)
    assert model_client._client is sentinel_client


def test_integrations_provider_builds_agent_runtime_from_model_client() -> None:
    """Verify IntegrationsProvider constructs AgentRuntime with the model client."""
    provider = ioc_module.IntegrationsProvider()
    sentinel_model_client = MagicMock(spec=GeminiModelClient)

    runtime = provider.provide_agent_runtime(sentinel_model_client)

    assert isinstance(runtime, AgentRuntime)
    assert runtime._model_client is sentinel_model_client


def test_integrations_provider_builds_spec_tree() -> None:
    """Verify IntegrationsProvider provides a valid SpecTree."""
    provider = ioc_module.IntegrationsProvider()
    spec_tree = provider.provide_spec_tree()

    assert isinstance(spec_tree, SpecTree)
    assert spec_tree.root.name == "coffee_barista"


def test_integrations_provider_builds_persona_manager() -> None:
    """Verify IntegrationsProvider provides PersonaManager."""
    provider = ioc_module.IntegrationsProvider()
    persona_manager = provider.provide_persona_manager()

    assert isinstance(persona_manager, PersonaManager)


def test_integrations_provider_builds_intent_classifier_from_injected_client(monkeypatch: Any) -> None:
    """Verify IntegrationsProvider constructs FlashLiteIntentClassifier."""
    provider = ioc_module.IntegrationsProvider()
    sentinel_client = object()
    captured: dict[str, object] = {}

    class FakeClassifier:
        def __init__(self, client: object, model: str) -> None:
            captured["client"] = client
            captured["model"] = model

    monkeypatch.setattr(ioc_module, "FlashLiteIntentClassifier", FakeClassifier)

    classifier = provider.provide_intent_classifier(sentinel_client)  # type: ignore[arg-type]

    assert isinstance(classifier, FakeClassifier)
    assert captured["client"] is sentinel_client
    assert captured["model"] == "gemini-3.8-flash"
