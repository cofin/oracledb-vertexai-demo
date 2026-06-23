# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.domain.products.schemas import ProductAvailability, Store, StoreDistance, StoreHours
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


async def test_find_stores_by_location_uses_named_sql_and_typed_store_results(mock_driver) -> None:
    mock_driver.select = AsyncMock(return_value=[_store(16, "Cymbal Coffee Dallas Arts District", 32.7876, -96.7994)])
    service = StoreService(mock_driver)

    result = await service.find_stores_by_location(city="Dallas", state="TX", zip_code="75201")

    assert result[0].name == "Cymbal Coffee Dallas Arts District"
    statement = mock_driver.select.await_args.args[0]
    assert "LOWER(city)" in str(statement.sql)
    assert mock_driver.select.await_args.kwargs["city"] == "Dallas"
    assert mock_driver.select.await_args.kwargs["state"] == "TX"
    assert mock_driver.select.await_args.kwargs["zip_code"] == "75201"
    assert mock_driver.select.await_args.kwargs["schema_type"] is Store


async def test_get_store_hours_returns_schema_owned_contract(mock_driver) -> None:
    mock_driver.select_one_or_none = AsyncMock(
        return_value=_store(16, "Cymbal Coffee Dallas Arts District", 32.7876, -96.7994)
    )
    service = StoreService(mock_driver)

    result = await service.get_store_hours(16)

    assert isinstance(result, StoreHours)
    assert result.store_id == 16
    assert result.store_name == "Cymbal Coffee Dallas Arts District"
    assert result.timezone == "America/Chicago"
    assert result.hours == {"monday": "6am-8pm"}


async def test_find_nearest_stores_ranks_with_local_seeded_coordinates(mock_driver) -> None:
    mock_driver.select = AsyncMock(
        return_value=[
            _store(13, "Cymbal Coffee Seattle", 47.6097, -122.3331, city="Seattle"),
            _store(16, "Cymbal Coffee Dallas Arts District", 32.7876, -96.7994),
        ]
    )
    service = StoreService(mock_driver)

    result = await service.find_nearest_stores(32.78, -96.8, limit=2)

    assert [store.id for store in result] == [16, 13]
    assert all(isinstance(store, StoreDistance) for store in result)
    assert result[0].distance_miles < 1.0
    statement = mock_driver.select.await_args.args[0]
    assert "FROM store" in str(statement.sql)


async def test_find_stores_with_product_returns_typed_rows_and_sorts_by_coordinates(mock_driver) -> None:
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
    mock_driver.select = AsyncMock(return_value=availability)
    service = StoreService(mock_driver)

    stores_with_product = await service.find_stores_with_product(1, latitude=32.78, longitude=-96.8)

    assert [row.store_id for row in stores_with_product] == [16, 13]
    assert stores_with_product[0].distance_miles is not None
    assert mock_driver.select.await_args.kwargs["schema_type"] is ProductAvailability


async def test_list_store_inventory_uses_named_query_and_typed_rows(mock_driver) -> None:
    mock_driver.select = AsyncMock(return_value=[])
    service = StoreService(mock_driver)

    rows = await service.list_store_inventory(16)

    assert rows == []
    statement = mock_driver.select.await_args.args[0]
    assert "WHERE spi.store_id = :store_id" in str(statement.sql)
    assert mock_driver.select.await_args.kwargs["store_id"] == 16
    assert mock_driver.select.await_args.kwargs["schema_type"] is ProductAvailability


async def test_find_product_availability_does_not_filter_location_hint(mock_driver) -> None:
    mock_driver.select = AsyncMock(
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
    service = StoreService(mock_driver)

    result = await service.find_product_availability("Espresso Romano", location_hint="Dallas")

    assert len(result) == 2
    assert [row.store_id for row in result] == [16, 13]
    assert mock_driver.select.await_args.kwargs["product_query"] == "Espresso Romano"
    assert mock_driver.select.await_args.kwargs["schema_type"] is ProductAvailability


async def test_resolve_store_by_location_hint(mock_driver) -> None:
    mock_driver.select = AsyncMock(
        return_value=[
            _store(13, "Cymbal Coffee Seattle", 47.6097, -122.3331, city="Seattle"),
            _store(16, "Cymbal Coffee Dallas Arts District", 32.7876, -96.7994),
        ]
    )
    service = StoreService(mock_driver)

    # 1. Direct match
    resolved = await service.resolve_store(location_hint="Dallas Arts District")
    assert resolved is not None
    assert resolved.id == 16

    # 2. Case-insensitive substring match
    resolved = await service.resolve_store(location_hint="seattle")
    assert resolved is not None
    assert resolved.id == 13

    # 3. Reverse match (store name is inside hint)
    resolved = await service.resolve_store(location_hint="Is it in stock at Cymbal Coffee Seattle?")
    assert resolved is not None
    assert resolved.id == 13

    # 4. No match
    resolved = await service.resolve_store(location_hint="Chicago")
    assert resolved is None


async def test_resolve_store_by_coordinates(mock_driver) -> None:
    mock_driver.select = AsyncMock(
        return_value=[
            _store(13, "Cymbal Coffee Seattle", 47.6097, -122.3331, city="Seattle"),
            _store(16, "Cymbal Coffee Dallas Arts District", 32.7876, -96.7994),
        ]
    )
    service = StoreService(mock_driver)

    # Near Dallas coords
    resolved = await service.resolve_store(coordinates=(32.78, -96.8))
    assert resolved is not None
    assert resolved.id == 16
