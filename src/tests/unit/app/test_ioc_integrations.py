# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for ``IntegrationsProvider``'s ADK wiring."""

from __future__ import annotations

from typing import Any

import app.ioc as ioc_module


def test_integrations_provider_builds_oracle_adk_store_from_injected_config(monkeypatch: Any) -> None:
    provider = ioc_module.IntegrationsProvider()
    sentinel_config = object()
    captured: dict[str, object] = {}

    class FakeStore:
        def __init__(self, config: object) -> None:
            captured["config"] = config

    monkeypatch.setattr(ioc_module, "OracleAsyncADKStore", FakeStore, raising=False)

    store = provider.provide_adk_store(sentinel_config)  # type: ignore[arg-type]

    assert isinstance(store, FakeStore)
    assert captured["config"] is sentinel_config


def test_integrations_provider_builds_sqlspec_session_service_from_store(monkeypatch: Any) -> None:
    provider = ioc_module.IntegrationsProvider()
    sentinel_store = object()
    captured: dict[str, object] = {}

    class FakeSessionService:
        def __init__(self, store: object) -> None:
            captured["store"] = store

    monkeypatch.setattr(ioc_module, "SQLSpecSessionService", FakeSessionService, raising=False)

    session_service = provider.provide_session_service(sentinel_store)  # type: ignore[arg-type]

    assert isinstance(session_service, FakeSessionService)
    assert captured["store"] is sentinel_store


def test_integrations_provider_builds_runner_from_injected_dependencies(monkeypatch: Any) -> None:
    provider = ioc_module.IntegrationsProvider()
    sentinel_session_service = object()
    sentinel_classifier = object()
    sentinel_persona_manager = object()
    captured: dict[str, object] = {}

    class FakeRunner:
        def __init__(self, session_service: object, classifier: object, persona_manager: object) -> None:
            captured["session_service"] = session_service
            captured["classifier"] = classifier
            captured["persona_manager"] = persona_manager

    monkeypatch.setattr(ioc_module, "ADKRunner", FakeRunner)

    runner = provider.provide_adk_runner(
        sentinel_session_service,  # type: ignore[arg-type]
        sentinel_classifier,  # type: ignore[arg-type]
        sentinel_persona_manager,  # type: ignore[arg-type]
    )

    assert isinstance(runner, FakeRunner)
    assert captured["session_service"] is sentinel_session_service
    assert captured["classifier"] is sentinel_classifier
    assert captured["persona_manager"] is sentinel_persona_manager


def test_integrations_provider_builds_persona_manager() -> None:
    from app.domain.system.services import PersonaManager

    provider = ioc_module.IntegrationsProvider()
    persona_manager = provider.provide_persona_manager()

    assert isinstance(persona_manager, PersonaManager)


def test_integrations_provider_builds_intent_classifier_from_injected_client(monkeypatch: Any) -> None:
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
    assert captured["model"] == "gemini-3.1-flash-lite"
