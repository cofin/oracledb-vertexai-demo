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
        "panel-classify-compare",
    ):
        assert f'id="{panel_id}"' in body, f"explore page must render panel {panel_id}"
    assert 'data-ui-panel="vector-search"' in body
    assert "data-metric-card" in body
    assert 'data-chart-host="latency"' in body
    assert 'data-ui-popover-root="explore"' in body


async def test_explore_page_prefills_shared_query(client: AsyncTestClient) -> None:
    response = await client.get("/explore?q=dark%20roast")
    assert response.status_code == 200, response.text[:500]
    body = response.text
    assert 'value="dark roast"' in body
    assert body.count('name="query"') == 2
