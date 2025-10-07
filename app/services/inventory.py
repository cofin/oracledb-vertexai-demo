"""Inventory service using SQLSpec driver patterns."""


from typing import Any

from app.services.base import SQLSpecService


class InventoryService(SQLSpecService):
    """Handles database operations for inventory using SQLSpec patterns."""

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all inventory entries with shop and product information."""
        return await self.driver.select(
            """
            SELECT
                i.id,
                i.shop_id,
                s.name as shop_name,
                s.address as shop_address,
                i.product_id,
                p.name as product_name,
                p.current_price,
                p.description,
                c.name as company_name,
                i.created_at,
                i.updated_at
            FROM inventory i
            JOIN shop s ON i.shop_id = s.id
            JOIN product p ON i.product_id = p.id
            JOIN company c ON p.company_id = c.id
            ORDER BY s.name, p.name
            """
        )

    async def get_by_shop_and_product(self, shop_id: int, product_id: int) -> dict[str, Any] | None:
        """Get inventory by shop and product."""
        return await self.driver.select_one_or_none(
            """
            SELECT
                i.id,
                i.shop_id,
                s.name as shop_name,
                s.address as shop_address,
                i.product_id,
                p.name as product_name,
                p.current_price,
                p.description,
                c.name as company_name,
                i.created_at,
                i.updated_at
            FROM inventory i
            JOIN shop s ON i.shop_id = s.id
            JOIN product p ON i.product_id = p.id
            JOIN company c ON p.company_id = c.id
            WHERE i.shop_id = :shop_id AND i.product_id = :product_id
            """,
            shop_id=shop_id,
            product_id=product_id,
        )

    async def get_products_in_shop(self, shop_id: int) -> list[dict[str, Any]]:
        """Get all products available in a shop."""
        return await self.driver.select(
            """
            SELECT
                i.id,
                i.shop_id,
                s.name as shop_name,
                s.address as shop_address,
                i.product_id,
                p.name as product_name,
                p.current_price,
                p.description,
                c.name as company_name,
                i.created_at,
                i.updated_at
            FROM inventory i
            JOIN shop s ON i.shop_id = s.id
            JOIN product p ON i.product_id = p.id
            JOIN company c ON p.company_id = c.id
            WHERE i.shop_id = :shop_id
            ORDER BY p.name
            """,
            shop_id=shop_id,
        )

    async def get_shops_with_product(self, product_id: int) -> list[dict[str, Any]]:
        """Get all shops that have a product."""
        return await self.driver.select(
            """
            SELECT
                i.id,
                i.shop_id,
                s.name as shop_name,
                s.address as shop_address,
                i.product_id,
                p.name as product_name,
                p.current_price,
                p.description,
                c.name as company_name,
                i.created_at,
                i.updated_at
            FROM inventory i
            JOIN shop s ON i.shop_id = s.id
            JOIN product p ON i.product_id = p.id
            JOIN company c ON p.company_id = c.id
            WHERE i.product_id = :product_id
            ORDER BY s.name
            """,
            product_id=product_id,
        )

    async def add_product_to_shop(self, shop_id: int, product_id: int) -> dict[str, Any] | None:
        """Add a product to a shop's inventory."""
        # Use MERGE to handle duplicate key scenario
        await self.driver.execute(
            """
            MERGE INTO inventory i
            USING (SELECT :shop_id AS shop_id, :product_id AS product_id FROM dual) src
            ON (i.shop_id = src.shop_id AND i.product_id = src.product_id)
            WHEN NOT MATCHED THEN
                INSERT (shop_id, product_id)
                VALUES (:shop_id2, :product_id2)
            """,
            shop_id=shop_id,
            shop_id2=shop_id,
            product_id=product_id,
            product_id2=product_id,
        )

        # Return the inventory entry
        return await self.get_by_shop_and_product(shop_id, product_id)

    async def remove_product_from_shop(self, shop_id: int, product_id: int) -> bool:
        """Remove a product from a shop's inventory."""
        rowcount = await self.driver.execute(
            """
            DELETE FROM inventory
            WHERE shop_id = :shop_id AND product_id = :product_id
            """,
            shop_id=shop_id,
            product_id=product_id,
        )
        return rowcount > 0

    async def delete_by_id(self, inventory_id: str) -> bool:
        """Delete an inventory entry by ID."""
        rowcount = await self.driver.execute(
            """
            DELETE FROM inventory WHERE id = :id
            """,
            id=inventory_id,
        )
        return rowcount > 0

    async def update_inventory(self, inventory_id: str, shop_id: int, product_id: int) -> dict[str, Any] | None:
        """Update an inventory entry (change shop or product)."""
        rowcount = await self.driver.execute(
            """
            UPDATE inventory
            SET shop_id = :shop_id,
                product_id = :product_id
            WHERE id = :id
            """,
            id=inventory_id,
            shop_id=shop_id,
            product_id=product_id,
        )

        if rowcount > 0:
            return await self.get_by_shop_and_product(shop_id, product_id)
        return None

    async def get_product_availability_count(self, product_id: int) -> int:
        """Get the count of shops that have a specific product."""
        result = await self.driver.select_one_or_none(
            """
            SELECT COUNT(*) as count FROM inventory WHERE product_id = :product_id
            """,
            product_id=product_id,
        )
        return result["count"] if result else 0

    async def get_shop_product_count(self, shop_id: int) -> int:
        """Get the count of products in a specific shop."""
        result = await self.driver.select_one_or_none(
            """
            SELECT COUNT(*) as count FROM inventory WHERE shop_id = :shop_id
            """,
            shop_id=shop_id,
        )
        return result["count"] if result else 0

    async def bulk_add_products(self, shop_id: int, product_ids: list[int]) -> int:
        """Add multiple products to a shop's inventory."""
        added_count = 0
        for product_id in product_ids:
            rowcount = await self.driver.execute(
                """
                MERGE INTO inventory i
                USING (SELECT :shop_id AS shop_id, :product_id AS product_id FROM dual) src
                ON (i.shop_id = src.shop_id AND i.product_id = src.product_id)
                WHEN NOT MATCHED THEN
                    INSERT (shop_id, product_id)
                    VALUES (:shop_id2, :product_id2)
                """,
                shop_id=shop_id,
                shop_id2=shop_id,
                product_id=product_id,
                product_id2=product_id,
            )
            added_count += rowcount

        return added_count

    async def bulk_remove_products(self, shop_id: int, product_ids: list[int]) -> int:
        """Remove multiple products from a shop's inventory."""
        removed_count = 0
        for product_id in product_ids:
            rowcount = await self.driver.execute(
                """
                DELETE FROM inventory
                WHERE shop_id = :shop_id AND product_id = :product_id
                """,
                shop_id=shop_id,
                product_id=product_id,
            )
            removed_count += rowcount

        return removed_count
