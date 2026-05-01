# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.products.schemas import ProductAvailability, Store, StoreDistance, StoreHours, StoreInventoryItem
from app.domain.products.services import StoreService

pytestmark = pytest.mark.anyio


def _store(store_id: int, name: str, latitude: float, longitude: float, city: str = "Dallas") -> Store:
    now = datetime(2026, 5, 1, tzinfo=UTC)
    return Store(
        id=store_id,
        name=name,
        address=f"{store_id} Test St",
        city=city,
        state="TX",
        zip="75201",
        phone="(214) 555-0100",
        latitude=latitude,
        longitude=longitude,
        timezone="America/Chicago",
        hours={"monday": "6am-8pm"},
        metadata={"wifi": True},
        created_at=now,
        updated_at=now,
    )


async def test_find_stores_by_location_uses_named_sql_and_typed_store_results() -> None:
    driver = MagicMock()
    driver.select = AsyncMock(return_value=[_store(16, "Cymbal Coffee Dallas Arts District", 32.7876, -96.7994)])
    service = StoreService(driver)

    result = await service.find_stores_by_location(city="Dallas", state="TX", zip_code="75201")

    assert result[0].name == "Cymbal Coffee Dallas Arts District"
    statement = driver.select.await_args.args[0]
    assert "LOWER(city)" in str(statement.sql)
    assert driver.select.await_args.kwargs["city"] == "Dallas"
    assert driver.select.await_args.kwargs["state"] == "TX"
    assert driver.select.await_args.kwargs["zip_code"] == "75201"
    assert driver.select.await_args.kwargs["schema_type"] is Store


async def test_get_store_hours_returns_schema_owned_contract() -> None:
    driver = MagicMock()
    driver.select_one_or_none = AsyncMock(return_value=_store(16, "Cymbal Coffee Dallas Arts District", 32.7876, -96.7994))
    service = StoreService(driver)

    result = await service.get_store_hours(16)

    assert isinstance(result, StoreHours)
    assert result.store_id == 16
    assert result.store_name == "Cymbal Coffee Dallas Arts District"
    assert result.timezone == "America/Chicago"
    assert result.hours == {"monday": "6am-8pm"}


async def test_find_nearest_stores_ranks_with_local_seeded_coordinates() -> None:
    driver = MagicMock()
    driver.select = AsyncMock(
        return_value=[
            _store(13, "Cymbal Coffee Seattle", 47.6097, -122.3331, city="Seattle"),
            _store(16, "Cymbal Coffee Dallas Arts District", 32.7876, -96.7994),
        ]
    )
    service = StoreService(driver)

    result = await service.find_nearest_stores(32.78, -96.8, limit=2)

    assert [store.id for store in result] == [16, 13]
    assert all(isinstance(store, StoreDistance) for store in result)
    assert result[0].distance_miles < 1.0
    statement = driver.select.await_args.args[0]
    assert "FROM store" in str(statement.sql)


async def test_inventory_methods_return_typed_rows_and_sort_by_coordinates() -> None:
    driver = MagicMock()
    store_inventory = [
        StoreInventoryItem(
            id=1,
            store_id=16,
            product_id=1,
            quantity_available=4,
            stock_status="LOW_STOCK",
            pickup_available=True,
            product_name="Espresso Romano",
        )
    ]
    availability = [
        ProductAvailability(
            id=2,
            store_id=13,
            product_id=1,
            quantity_available=8,
            stock_status="IN_STOCK",
            pickup_available=True,
            store_name="Cymbal Coffee Seattle",
            store_address="654 Pike St",
            store_city="Seattle",
            store_state="WA",
            store_zip="98101",
            latitude=47.6097,
            longitude=-122.3331,
            product_name="Espresso Romano",
        ),
        ProductAvailability(
            id=1,
            store_id=16,
            product_id=1,
            quantity_available=4,
            stock_status="LOW_STOCK",
            pickup_available=True,
            store_name="Cymbal Coffee Dallas Arts District",
            store_address="1717 N Harwood St",
            store_city="Dallas",
            store_state="TX",
            store_zip="75201",
            latitude=32.7876,
            longitude=-96.7994,
            product_name="Espresso Romano",
        ),
    ]
    driver.select = AsyncMock(side_effect=[store_inventory, availability])
    service = StoreService(driver)

    inventory = await service.get_store_inventory(16)
    stores_with_product = await service.find_stores_with_product(1, latitude=32.78, longitude=-96.8)

    assert inventory == store_inventory
    assert [row.store_id for row in stores_with_product] == [16, 13]
    assert stores_with_product[0].distance_miles is not None
    assert driver.select.await_args_list[0].kwargs["schema_type"] is StoreInventoryItem
    assert driver.select.await_args_list[1].kwargs["schema_type"] is ProductAvailability


async def test_find_product_availability_filters_location_hint() -> None:
    driver = MagicMock()
    driver.select = AsyncMock(
        return_value=[
            ProductAvailability(
                id=1,
                store_id=16,
                product_id=1,
                quantity_available=4,
                stock_status="LOW_STOCK",
                pickup_available=True,
                store_name="Cymbal Coffee Dallas Arts District",
                store_address="1717 N Harwood St",
                store_city="Dallas",
                store_state="TX",
                store_zip="75201",
                product_name="Espresso Romano",
            ),
            ProductAvailability(
                id=2,
                store_id=13,
                product_id=1,
                quantity_available=8,
                stock_status="IN_STOCK",
                pickup_available=True,
                store_name="Cymbal Coffee Seattle",
                store_address="654 Pike St",
                store_city="Seattle",
                store_state="WA",
                store_zip="98101",
                product_name="Espresso Romano",
            ),
        ]
    )
    service = StoreService(driver)

    result = await service.find_product_availability("Espresso Romano", location_hint="Dallas")

    assert [row.store_id for row in result] == [16]
    assert driver.select.await_args.kwargs["product_query"] == "Espresso Romano"
    assert driver.select.await_args.kwargs["schema_type"] is ProductAvailability
