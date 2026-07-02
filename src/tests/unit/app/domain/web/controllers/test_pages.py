# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit coverage for page-level template contexts."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.products.schemas import Store
from app.domain.web.controllers._pages import PageController

pytestmark = pytest.mark.anyio


async def test_explore_page_loads_dynamic_store_inventory_selector() -> None:
    now = datetime(2026, 6, 23, tzinfo=UTC)
    stores = [
        Store(
            id=16,
            name="Cymbal Coffee Dallas Arts District",
            address="1717 N Harwood St",
            city="Dallas",
            state="TX",
            zip="75201",
            created_at=now,
            updated_at=now,
        ),
        Store(
            id=13,
            name="Cymbal Coffee Seattle",
            address="654 Pike St",
            city="Seattle",
            state="WA",
            zip="98101",
            created_at=now,
            updated_at=now,
        ),
    ]
    stores_service = MagicMock()
    stores_service.get_all_stores = AsyncMock(return_value=stores)

    response = await PageController.explore_page.fn(
        PageController(owner=MagicMock()), stores_service=stores_service, search_query="dark roast"
    )

    stores_service.get_all_stores.assert_awaited_once_with()
    assert response.template_name == "pages/explore.html.j2"
    assert response.context == {"query": "dark roast", "stores": stores}


async def test_explore_page_renders_when_store_selector_is_unavailable() -> None:
    stores_service = MagicMock()
    stores_service.get_all_stores = AsyncMock(side_effect=RuntimeError("database unavailable"))

    response = await PageController.explore_page.fn(
        PageController(owner=MagicMock()), stores_service=stores_service, search_query=None
    )

    stores_service.get_all_stores.assert_awaited_once_with()
    assert response.template_name == "pages/explore.html.j2"
    assert response.context == {"query": "", "stores": []}
