"""Store service for managing coffee shop locations."""

from __future__ import annotations

from app.schemas import Store
from app.services.base import SQLSpecService


class StoreService(SQLSpecService):
    """Service for managing store locations."""

    async def get_all_stores(self) -> list[Store]:
        """Get all store locations.

        Returns:
            List of all stores
        """
        return await self.driver.select(
            "SELECT * FROM store ORDER BY name",
            schema_type=Store,
        )

    async def find_stores_by_city(self, city: str) -> list[Store]:
        """Find stores in a specific city.

        Args:
            city: City name to search for

        Returns:
            List of stores in the specified city
        """
        return await self.driver.select(
            "SELECT * FROM store WHERE city = :city ORDER BY name",
            city=city,
            schema_type=Store,
        )

    async def find_stores_by_state(self, state: str) -> list[Store]:
        """Find stores in a specific state.

        Args:
            state: State to search for

        Returns:
            List of stores in the specified state
        """
        return await self.driver.select(
            "SELECT * FROM store WHERE state = :state ORDER BY city, name",
            state=state,
            schema_type=Store,
        )

    async def get_store_by_id(self, store_id: int) -> Store | None:
        """Get a store by ID.

        Args:
            store_id: Store ID

        Returns:
            Store or None if not found
        """
        return await self.driver.select_one_or_none(
            "SELECT * FROM store WHERE id = :store_id",
            store_id=store_id,
            schema_type=Store,
        )

    async def get_store_hours(self, store_id: int) -> dict:
        """Get store hours for a specific store.

        Args:
            store_id: Store ID

        Returns:
            Dictionary of store hours or empty dict if not found
        """
        result = await self.driver.select_one_or_none(
            "SELECT hours FROM store WHERE id = :store_id",
            store_id=store_id,
        )
        return result.get("hours", {}) if result else {}

    async def search_stores_by_zip(self, zip_code: str) -> list[Store]:
        """Find stores by ZIP code.

        Args:
            zip_code: ZIP code to search for

        Returns:
            List of stores in the specified ZIP code
        """
        return await self.driver.select(
            "SELECT * FROM store WHERE zip = :zip_code ORDER BY name",
            zip_code=zip_code,
            schema_type=Store,
        )
