# Copyright 2026 Google LLC
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
    assert "Barista chat" in body
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


async def test_explore_page_renders(client: AsyncTestClient) -> None:
    response = await client.get("/explore")
    assert response.status_code == 200, response.text[:500]
    body = response.text
    assert 'data-app-shell="true"' in body
    assert 'data-app-header="true"' in body
    assert "Powered by Oracle 26ai + Google Vertex AI" in body
    for panel_id in (
        "panel-vector-search",
        "panel-explain-plan",
        "panel-metrics-summary",
        "panel-latency-chart",
    ):
        assert f'id="{panel_id}"' in body, f"explore page must render panel {panel_id}"
    assert 'data-ui-panel="vector-search"' in body
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
    assert body.count('name="query"') == 2
    assert 'id="panel-vector-search" data-ui-panel="vector-search" hx-ext="ignore:litestar"' in body
    assert 'hx-post="/api/vector-demo" hx-trigger="load, keyup changed delay:300ms"' in body
    assert 'hx-swap="outerHTML"' in body
    assert 'hx-get="/api/explain-plan" hx-trigger="load, keyup changed delay:500ms"' in body
    assert body.count("text-surface placeholder:text-surface/60") == 2


async def test_explore_page_does_not_autoload_empty_query(client: AsyncTestClient) -> None:
    response = await client.get("/explore")
    assert response.status_code == 200, response.text[:500]
    body = response.text
    assert 'hx-trigger="load,' not in body
    assert 'hx-trigger="keyup changed delay:300ms"' in body
    assert 'hx-trigger="keyup changed delay:500ms"' in body
