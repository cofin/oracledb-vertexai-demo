# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit coverage for page-level template contexts."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.lib.schema as schema_module
from app.domain.products.schemas import Store
from app.domain.web.controllers._pages import PageController
from tests.support.paths import APP_ROOT

pytestmark = pytest.mark.anyio


async def test_explore_page_loads_dynamic_store_inventory_selector() -> None:
    """Verify `PageController.explore_page` populates the store selector from `StoreService`."""
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
    assert response.context["query"] == "dark roast"
    assert response.context["stores"] == stores
    assert response.context["search_mode"] == "hybrid"
    assert response.context["rrf_k"] == 60
    assert response.context["oracle_text_query"] == "{dark} ACCUM {roast}"
    assert "hybrid-search-products" in response.context["hybrid_detail_json"]
    assert "vector-search-products" in response.context["vector_detail_json"]


async def test_explore_page_renders_when_store_selector_is_unavailable() -> None:
    """Verify `PageController.explore_page` degrades gracefully to an empty store list on error."""
    stores_service = MagicMock()
    stores_service.get_all_stores = AsyncMock(side_effect=RuntimeError("database unavailable"))

    response = await PageController.explore_page.fn(
        PageController(owner=MagicMock()), stores_service=stores_service, search_query=None
    )

    stores_service.get_all_stores.assert_awaited_once_with()
    assert response.template_name == "pages/explore.html.j2"
    assert not response.context["query"]
    assert response.context["stores"] == []
    assert response.context["search_mode"] == "hybrid"
    assert response.context["rrf_k"] == 60
    assert "hybrid-search-products" in response.context["hybrid_detail_json"]
    assert "vector-search-products" in response.context["vector_detail_json"]


def test_schema_and_legacy_module_cleanup_contracts() -> None:
    """Verify legacy mutable structs and removed compatibility modules do not exist."""
    assert tuple(schema_module.__all__) == ("CamelizedFrozenStruct", "FrozenBaseStruct", "Message")
    assert not hasattr(schema_module, "BaseStruct")
    assert not hasattr(schema_module, "CamelizedBaseStruct")
    assert not (APP_ROOT / "domain" / "chat" / "exceptions.py").exists()
    assert not (APP_ROOT / "domain" / "chat" / "session.py").exists()
    assert not (APP_ROOT / "domain" / "products" / "services" / "_inventory.py").exists()
    assert not (APP_ROOT / "domain" / "products" / "controllers" / "_vector_helpers.py").exists()
