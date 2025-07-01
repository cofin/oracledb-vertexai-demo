from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.repositories.inventory import InventoryRepository
    from app.schemas import InventoryDTO


class InventoryService:
    """Handles database operations for inventory using a repository."""

    def __init__(self, inventory_repository: InventoryRepository):
        """Initialize with inventory repository."""
        self.repository = inventory_repository

    async def get_all(self) -> list[InventoryDTO]:
        """Get all inventory entries with shop and product information."""
        return await self.repository.get_all()

    async def get_by_shop_and_product(self, shop_id: int, product_id: int) -> InventoryDTO | None:
        """Get inventory by shop and product."""
        return await self.repository.get_by_shop_and_product(shop_id, product_id)

    async def add_product_to_shop(self, shop_id: int, product_id: int) -> InventoryDTO | None:
        """Add a product to a shop's inventory."""
        return await self.repository.add_product_to_shop(shop_id, product_id)

    async def remove_product_from_shop(self, shop_id: int, product_id: int) -> bool:
        """Remove a product from a shop's inventory."""
        return await self.repository.remove_product_from_shop(shop_id, product_id)
