from __future__ import annotations

from typing import Any

import app.domain.chat.services as chat_services


def test_chat_provider_builds_oracle_adk_store_from_injected_config(monkeypatch: Any) -> None:
    provider = chat_services.ChatServiceProvider()
    sentinel_config = object()
    captured: dict[str, object] = {}

    class FakeStore:
        def __init__(self, config: object) -> None:
            captured["config"] = config

    monkeypatch.setattr(chat_services, "OracleAsyncADKStore", FakeStore, raising=False)

    store = provider.get_adk_store(sentinel_config)

    assert isinstance(store, FakeStore)
    assert captured["config"] is sentinel_config


def test_chat_provider_builds_sqlspec_session_service_from_store(monkeypatch: Any) -> None:
    provider = chat_services.ChatServiceProvider()
    sentinel_store = object()
    captured: dict[str, object] = {}

    class FakeSessionService:
        def __init__(self, store: object) -> None:
            captured["store"] = store

    monkeypatch.setattr(chat_services, "SQLSpecSessionService", FakeSessionService, raising=False)

    session_service = provider.get_session_service(sentinel_store)

    assert isinstance(session_service, FakeSessionService)
    assert captured["store"] is sentinel_store


def test_chat_provider_builds_runner_from_injected_session_service(monkeypatch: Any) -> None:
    provider = chat_services.ChatServiceProvider()
    sentinel_session_service = object()

    class FakeRunner:
        def __init__(self, session_service: object) -> None:
            self.session_service = session_service

    monkeypatch.setattr(chat_services, "ADKRunner", FakeRunner)

    runner = provider.get_adk_runner(sentinel_session_service)

    assert isinstance(runner, FakeRunner)
    assert runner.session_service is sentinel_session_service
