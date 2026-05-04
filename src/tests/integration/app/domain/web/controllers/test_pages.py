# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Page-rendering smoke tests for chat and explore."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

pytestmark = pytest.mark.anyio


async def test_chat_page_renders(client: AsyncTestClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    body = response.text
    assert 'data-app-shell="true"' in body
    assert 'data-app-header="true"' in body
    assert "Powered by Oracle 26ai + Google Vertex AI" in body
    assert 'hx-ext="litestar"' in body
    assert 'id="messages"' in body
    assert 'id="metrics-badges"' in body
    assert 'data-chat-form="true"' in body
    assert 'data-ui-panel="chat-sidebar"' in body
    assert 'data-ui-panel="chat-thread"' in body
    assert 'data-ui-popover-root="chat"' in body
    assert 'data-chat-avatar="ai"' in body
    assert "Barista chat" in body
    assert "Tell me what sounds good and I'll check the Cymbal Coffee menu." in body
    assert "Welcome back. Tell me what sounds good" not in body
    assert '<meta name="csrf-token"' in body


async def test_chat_page_renders_persisted_session_history(
    client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain.chat.schemas import ChatMessage
    from app.domain.chat.services import ADKRunner

    def _noop_init(self: object, *args: object, **kwargs: object) -> None:
        del self, args, kwargs

    async def _history(self: object, *args: object, **kwargs: object) -> list[ChatMessage]:
        del self, args, kwargs
        return [
            ChatMessage(source="human", message="old question"),
            ChatMessage(source="ai", message="old answer"),
        ]

    monkeypatch.setattr(ADKRunner, "__init__", _noop_init)
    monkeypatch.setattr(ADKRunner, "get_history", _history, raising=False)

    response = await client.get("/")

    assert response.status_code == 200, response.text[:500]
    body = response.text
    assert "old question" in body
    assert "old answer" in body
    assert "Welcome back. Tell me what sounds good" not in body


async def test_chat_page_renders_fallback_history(
    client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain.chat.services import ADKRunner

    def _noop_init(self: object, *args: object, **kwargs: object) -> None:
        del self, args, kwargs

    async def _history_fail(self: object, *args: object, **kwargs: object) -> list:
        del self, args, kwargs
        raise Exception("History failure simulated")

    monkeypatch.setattr(ADKRunner, "__init__", _noop_init)
    monkeypatch.setattr(ADKRunner, "get_history", _history_fail, raising=False)

    response = await client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "Tell me what sounds good and I'll check the Cymbal Coffee menu." in body


async def test_explore_page_renders(client: AsyncTestClient) -> None:
    response = await client.get("/explore")
    assert response.status_code == 200, response.text[:500]
    body = response.text
    assert 'data-app-shell="true"' in body
    assert 'data-app-header="true"' in body
    assert "Powered by Oracle 26ai + Google Vertex AI" in body
    assert "Vector lab" in body
    assert "Performance dashboard" not in body
    for panel_id in (
        "panel-vector-search",
        "panel-explain-plan",
        "panel-metrics-summary",
        "panel-latency-chart",
        "panel-vector-calculator",
    ):
        assert f'id="{panel_id}"' in body, f"explore page must render panel {panel_id}"
    assert 'data-ui-panel="vector-search"' in body
    assert 'data-ui-panel="explain-plan"' in body
    assert 'data-ui-panel="vector-calculator"' in body
    assert "Vector storage calculator" in body
    assert "1 ·" not in body
    assert "2 ·" not in body
    assert "3 ·" not in body
    assert "4 ·" not in body
    assert "5 ·" not in body
    assert "data-metric-card" in body
    assert 'data-chart-host="response-trends"' in body
    assert 'data-chart-host="vector-performance"' in body
    assert 'data-chart-host="system-breakdown"' in body
    assert "classify-compare" not in body
    assert 'data-ui-popover-root="explore"' in body


async def test_explore_page_prefills_shared_query(client: AsyncTestClient) -> None:
    response = await client.get("/explore?q=dark%20roast")
    assert response.status_code == 200, response.text[:500]
    body = response.text
    assert 'value="dark roast"' in body
    assert body.count('name="query"') == 1
    assert 'placeholder="Search for a drink, roast, flavor, or breakfast item"' in body
    assert 'id="panel-vector-search" data-ui-panel="vector-search" hx-ext="ignore:litestar"' in body
    assert 'hx-post="/api/vector-demo" hx-trigger="load, keyup changed delay:300ms"' in body
    assert 'hx-swap="outerHTML"' in body
    assert "Search results and SQL plan update from the same query." in body
    assert 'hx-get="/api/explain-plan"' not in body
    assert body.count("text-surface placeholder:text-surface/60") == 1
    assert "Table + Vector Pool" in body
    assert "Vector pool estimate" in body
    assert "HNSW M" not in body


async def test_explore_page_does_not_autoload_empty_query(client: AsyncTestClient) -> None:
    response = await client.get("/explore")
    assert response.status_code == 200, response.text[:500]
    body = response.text
    assert 'hx-post="/api/vector-demo" hx-trigger="load,' not in body
    assert 'hx-trigger="keyup changed delay:300ms"' in body
