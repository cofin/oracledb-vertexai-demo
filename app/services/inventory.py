"""Inventory service with Advanced Alchemy patterns."""

from collections.abc import Sequence

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import and_

from app.db import models as m


class InventoryService(SQLAlchemyAsyncRepositoryService[m.Inventory]):
    """Handles database operations for inventory."""

    class Repo(SQLAlchemyAsyncRepository[m.Inventory]):
        """Inventory repository."""

        model_type = m.Inventory

    repository_type = Repo

    async def get_by_shop_and_product(self, shop_id: int, product_id: int) -> m.Inventory | None:
        """Get inventory by shop and product."""

        return await self.get_one_or_none(and_(m.Inventory.shop_id == shop_id, m.Inventory.product_id == product_id))

    async def get_products_in_shop(self, shop_id: int) -> Sequence[m.Inventory]:
        """Get all products available in a shop."""
        return await self.list(m.Inventory.shop_id == shop_id)

    async def get_shops_with_product(self, product_id: int) -> Sequence[m.Inventory]:
        """Get all shops that have a product."""
        return await self.list(m.Inventory.product_id == product_id)

    async def update_stock(self, shop_id: int, product_id: int) -> m.Inventory | None:
        """Update stock for a product in a shop."""
        inventory = await self.get_by_shop_and_product(shop_id, product_id)
        if inventory:
            return inventory
        return None
