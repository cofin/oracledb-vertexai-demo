# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for IntegrationsProvider's ADK wiring (Ch 2.3)."""

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


def test_integrations_provider_builds_runner_from_injected_session_service(monkeypatch: Any) -> None:
    provider = ioc_module.IntegrationsProvider()
    sentinel_session_service = object()

    class FakeRunner:
        def __init__(self, session_service: object) -> None:
            self.session_service = session_service

    monkeypatch.setattr(ioc_module, "ADKRunner", FakeRunner)

    runner = provider.provide_adk_runner(sentinel_session_service)  # type: ignore[arg-type]

    assert isinstance(runner, FakeRunner)
    assert runner.session_service is sentinel_session_service
