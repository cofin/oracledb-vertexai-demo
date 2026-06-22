# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Shared MagicMock graph builders for ADKRunner streaming-chat tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

from app.domain.chat.services.classifier import IntentLabel

if TYPE_CHECKING:
    from app.domain.chat.services.adk import ADKRunner


def make_session(session_id: str = "sess-test", state: dict[str, Any] | None = None) -> MagicMock:
    """Build a MagicMock ADK session with a mutable state dict."""
    session = MagicMock()
    session.id = session_id
    session.state = {} if state is None else state
    return session


def make_session_service(session: MagicMock | None = None) -> MagicMock:
    """Build a session service whose get/create both return the same session."""
    session = session or make_session()
    service = MagicMock()
    service.get_session = AsyncMock(return_value=session)
    service.create_session = AsyncMock(return_value=session)
    service.store.update_session_state = MagicMock()
    return service


def make_persona_manager(*, prompt: str = "composed instruction", temperature: float = 0.7) -> MagicMock:
    """Build a persona manager returning a fixed prompt and temperature."""
    persona_manager = MagicMock()
    persona_manager.get_system_prompt = MagicMock(return_value=prompt)
    persona_manager.get_temperature = MagicMock(return_value=temperature)
    return persona_manager


def make_runner(
    *,
    session_service: Any | None = None,
    classifier: Any | None = None,
    persona_manager: Any | None = None,
    intent: IntentLabel = IntentLabel.PRODUCT_RAG,
) -> ADKRunner:
    """Build a fully-wired ADKRunner with sensible MagicMock defaults."""
    from app.domain.chat.services.adk import ADKRunner

    if classifier is None:
        classifier = MagicMock()
        classifier.classify = AsyncMock(return_value=intent)
    return ADKRunner(
        session_service=session_service or make_session_service(),
        classifier=classifier,
        persona_manager=persona_manager or make_persona_manager(),
    )


def make_tools_service(*, products: list[dict[str, Any]] | None = None, vector_query: str = "hey") -> MagicMock:
    """Build a tools service double for stream_request, no cache hit by default."""
    tools_service = MagicMock()
    tools_service.make_response_cache_key = MagicMock(return_value="cache-key")
    tools_service.get_cached_chat_response = AsyncMock(return_value=None)
    tools_service.set_cached_chat_response = AsyncMock()
    if products is not None:
        tools_service.search_products_by_vector = AsyncMock(
            return_value={
                "products": products,
                "embedding_cache_hit": False,
                "results_count": len(products),
                "vector_query": vector_query,
                "search_metrics": {"embedding_ms": 10.0, "oracle_ms": 5.0, "tool_ms": 15.0},
                "sql_phases": [{"sql_key": "vector-search-products", "row_count": len(products)}],
            }
        )
    return tools_service


def allow_vertex_config(monkeypatch: Any, adk_module: Any) -> None:
    """Patch get_settings so the Vertex credential guard treats the runner as configured."""
    settings = MagicMock()
    settings.ai.project_id = "test-project"
    settings.ai.api_key = None
    settings.ai.chat_model = "gemini-2.5-flash-lite"
    settings.chat.session_app_name = "coffee_assistant"
    settings.chat.response_cache_version = "menu-grounded-v2"
    settings.chat.response_cache_ttl_minutes = 60
    settings.chat.product_search_limit = 5
    settings.chat.product_search_threshold = 0.7
    settings.chat.display_history_limit = 40
    settings.chat.grounded_answer_timeout_seconds = 2.5
    monkeypatch.setattr(adk_module, "get_settings", lambda: settings)
