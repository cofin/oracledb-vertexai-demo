# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Store location and availability services."""

from __future__ import annotations

from typing import cast

from msgspec.structs import asdict

from app.config import db_manager
from app.domain.products.schemas import ApexInventorySummaryRow, ProductAvailability, Store, StoreDistance, StoreHours
from app.domain.products.services._location import haversine_miles, store_matches_hint
from app.lib.service import FilterTypes, OffsetPagination, OracleAsyncService

__all__ = ("StoreService",)


class StoreService(OracleAsyncService):
    """Service for managing store locations and store-level inventory queries."""

    async def list_with_count(self, *filters: FilterTypes) -> OffsetPagination[Store]:
        """Paginate store records."""
        return cast(
            "OffsetPagination[Store]",
            await self.paginate(db_manager.get_sql("list-stores"), *filters, schema_type=Store),
        )

    async def get_all_stores(self) -> list[Store]:
        """Return all Cymbal Coffee stores."""
        return await self.driver.select(db_manager.get_sql("list-stores"), schema_type=Store)

    async def list_inventory_summary(self) -> list[ApexInventorySummaryRow]:
        """Return per-store inventory summary counts."""
        return await self.driver.select(
            db_manager.get_sql("list-inventory-summary"), schema_type=ApexInventorySummaryRow
        )

    async def search_store_inventory(self, *, store_id: int, q: str, limit: int = 5) -> list[ProductAvailability]:
        """Search product availability within a single store."""
        return await self.driver.select(
            db_manager.get_sql("search-store-inventory"),
            store_id=store_id,
            q=q,
            limit=max(1, min(limit, 100)),
            schema_type=ProductAvailability,
        )

    async def find_stores_by_location(
        self, *, city: str | None = None, state: str | None = None, zip_code: str | None = None
    ) -> list[Store]:
        """Find stores matching city, state, or ZIP code."""
        return await self.driver.select(
            db_manager.get_sql("find-stores-by-location"), city=city, state=state, zip_code=zip_code, schema_type=Store
        )

    async def get_store_by_id(self, store_id: int) -> Store | None:
        """Return a single store by primary key."""
        return await self.driver.select_one_or_none(
            db_manager.get_sql("get-store-by-id"), id=store_id, schema_type=Store
        )

    async def get_store_hours(self, store_id: int) -> StoreHours | None:
        """Return operating hours for a store."""
        store = await self.get_store_by_id(store_id)
        if store is None:
            return None
        return StoreHours(store_id=store.id, store_name=store.name, timezone=store.timezone, hours=store.hours or {})

    async def find_nearest_stores(self, latitude: float, longitude: float, limit: int = 5) -> list[StoreDistance]:
        """Rank stores by great-circle haversine distance in miles."""
        stores = await self.get_all_stores()
        ranked = [
            StoreDistance(**asdict(store), distance_miles=round(haversine_miles(latitude, longitude, store), 2))
            for store in stores
            if store.latitude is not None and store.longitude is not None
        ]
        ranked.sort(key=lambda store: store.distance_miles)
        return ranked[:limit]

    async def resolve_store(
        self, *, location_hint: str | None = None, coordinates: tuple[float, float] | None = None
    ) -> Store | None:
        """Resolve a single store by location hint (priority) or nearest to coordinates."""
        if location_hint:
            stores = await self.get_all_stores()
            for store in stores:
                if store_matches_hint(store, location_hint):
                    return store
        if coordinates:
            lat, lon = coordinates
            nearest = await self.find_nearest_stores(lat, lon, limit=1)
            if nearest:
                return nearest[0]
        return None

    async def find_stores_with_product(
        self, product_id: int, *, latitude: float | None = None, longitude: float | None = None
    ) -> list[ProductAvailability]:
        """List stores carrying a given product ID, optionally ranked by distance."""
        rows = await self.driver.select(
            db_manager.get_sql("find-stores-with-product-inventory"),
            product_id=product_id,
            schema_type=ProductAvailability,
        )
        return self._rank_availability(rows, latitude=latitude, longitude=longitude)

    async def list_store_inventory(self, store_id: int) -> list[ProductAvailability]:
        """List all inventory rows for a specific store."""
        return await self.driver.select(
            db_manager.get_sql("list-store-inventory"), store_id=store_id, schema_type=ProductAvailability
        )

    async def find_product_availability(
        self, query: str, *, location_hint: str | None = None, coordinates: tuple[float, float] | None = None
    ) -> list[ProductAvailability]:
        """Find product availability across stores matching a query string."""
        del location_hint
        rows = await self.driver.select(
            db_manager.get_sql("find-product-availability-by-query"),
            product_query=query,
            schema_type=ProductAvailability,
        )
        latitude, longitude = coordinates or (None, None)
        return self._rank_availability(rows, latitude=latitude, longitude=longitude)

    @staticmethod
    def _rank_availability(
        rows: list[ProductAvailability], *, latitude: float | None = None, longitude: float | None = None
    ) -> list[ProductAvailability]:
        if latitude is None or longitude is None:
            return rows
        ranked: list[ProductAvailability] = []
        for row in rows:
            data = asdict(row)
            data["distance_miles"] = round(haversine_miles(latitude, longitude, row), 2)
            ranked.append(ProductAvailability(**data))
        ranked.sort(key=lambda row: row.distance_miles if row.distance_miles is not None else float("inf"))
        return ranked
