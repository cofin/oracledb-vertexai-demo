# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Store inventory HTMX controller tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.products.controllers import StoreController
from app.domain.products.schemas import ProductAvailability

pytestmark = pytest.mark.anyio


async def test_store_inventory_returns_htmx_partial() -> None:
    stores_service = MagicMock()
    stores_service.list_store_inventory = AsyncMock(
        return_value=[
            ProductAvailability(
                id=1,
                store_id=16,
                product_id=10,
                quantity_available=4,
                stock_status="LOW_STOCK",
                pickup_available=True,
                updated_at=datetime(2026, 6, 23, tzinfo=UTC),
                store_name="Cymbal Coffee Dallas Arts District",
                store_address="1717 N Harwood St",
                product_name="Cold Brew Nitro",
                product_price=5.25,
            )
        ]
    )

    response = await StoreController.store_inventory.fn(
        StoreController(owner=MagicMock()),
        stores_service=stores_service,
        store_id=16,
    )

    stores_service.list_store_inventory.assert_awaited_once_with(16)
    assert response.template_name == "partials/_inventory_list.html.j2"
    assert response.context["store_id"] == 16
    assert response.context["inventory"][0].product_name == "Cold Brew Nitro"
