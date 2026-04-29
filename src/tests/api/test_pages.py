# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Phase 4.7/4.8 contract: ``GET /`` renders the chat page with HTMX wiring."""

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
    assert 'hx-ext="litestar"' in body
    assert 'id="messages"' in body
    assert 'id="metrics-badges"' in body
    assert '<meta name="csrf-token"' in body


async def test_explore_page_renders(client: AsyncTestClient) -> None:
    """Phase 5.4 contract: ``/explore`` renders all 5 panel hosts."""
    response = await client.get("/explore")
    assert response.status_code == 200, response.text[:500]
    body = response.text
    for panel_id in (
        "panel-vector-search",
        "panel-explain-plan",
        "panel-metrics-summary",
        "panel-latency-chart",
        "panel-classify-compare",
    ):
        assert f'id="{panel_id}"' in body, f"explore page must render panel {panel_id}"
