"""Inventory service using raw Oracle SQL."""

from __future__ import annotations

from typing import Any

from app.services.base import BaseService


class InventoryService(BaseService):
    """Handles database operations for inventory using raw SQL."""

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all inventory entries with shop and product information."""
        async with self.get_cursor() as cursor:
            await cursor.execute("""
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
            """)

            return [
                {
                    "id": row[0],
                    "shop_id": row[1],
                    "shop_name": row[2],
                    "shop_address": row[3],
                    "product_id": row[4],
                    "product_name": row[5],
                    "current_price": row[6],
                    "description": row[7],
                    "company_name": row[8],
                    "created_at": row[9],
                    "updated_at": row[10],
                }
                async for row in cursor
            ]

    async def get_by_shop_and_product(self, shop_id: int, product_id: int) -> dict[str, Any] | None:
        """Get inventory by shop and product."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
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
                {"shop_id": shop_id, "product_id": product_id},
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "shop_id": row[1],
                    "shop_name": row[2],
                    "shop_address": row[3],
                    "product_id": row[4],
                    "product_name": row[5],
                    "current_price": row[6],
                    "description": row[7],
                    "company_name": row[8],
                    "created_at": row[9],
                    "updated_at": row[10],
                }
            return None

    async def get_products_in_shop(self, shop_id: int) -> list[dict[str, Any]]:
        """Get all products available in a shop."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
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
                {"shop_id": shop_id},
            )

            return [
                {
                    "id": row[0],
                    "shop_id": row[1],
                    "shop_name": row[2],
                    "shop_address": row[3],
                    "product_id": row[4],
                    "product_name": row[5],
                    "current_price": row[6],
                    "description": row[7],
                    "company_name": row[8],
                    "created_at": row[9],
                    "updated_at": row[10],
                }
                async for row in cursor
            ]

    async def get_shops_with_product(self, product_id: int) -> list[dict[str, Any]]:
        """Get all shops that have a product."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
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
                {"product_id": product_id},
            )

            return [
                {
                    "id": row[0],
                    "shop_id": row[1],
                    "shop_name": row[2],
                    "shop_address": row[3],
                    "product_id": row[4],
                    "product_name": row[5],
                    "current_price": row[6],
                    "description": row[7],
                    "company_name": row[8],
                    "created_at": row[9],
                    "updated_at": row[10],
                }
                async for row in cursor
            ]

    async def add_product_to_shop(self, shop_id: int, product_id: int) -> dict[str, Any] | None:
        """Add a product to a shop's inventory."""
        async with self.get_cursor() as cursor:
            # Use MERGE to handle duplicate key scenario
            await cursor.execute(
                """
                MERGE INTO inventory i
                USING (SELECT :shop_id AS shop_id, :product_id AS product_id FROM dual) src
                ON (i.shop_id = src.shop_id AND i.product_id = src.product_id)
                WHEN NOT MATCHED THEN
                    INSERT (shop_id, product_id)
                    VALUES (:shop_id2, :product_id2)
                """,
                {
                    "shop_id": shop_id,
                    "shop_id2": shop_id,
                    "product_id": product_id,
                    "product_id2": product_id,
                },
            )

            await self.connection.commit()

            # Return the inventory entry
            return await self.get_by_shop_and_product(shop_id, product_id)

    async def remove_product_from_shop(self, shop_id: int, product_id: int) -> bool:
        """Remove a product from a shop's inventory."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                DELETE FROM inventory
                WHERE shop_id = :shop_id AND product_id = :product_id
                """,
                {"shop_id": shop_id, "product_id": product_id},
            )

            await self.connection.commit()
            return cursor.rowcount > 0

    async def delete_by_id(self, inventory_id: str) -> bool:
        """Delete an inventory entry by ID."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                DELETE FROM inventory WHERE id = :id
                """,
                {"id": inventory_id},
            )

            await self.connection.commit()
            return cursor.rowcount > 0

    async def update_inventory(self, inventory_id: str, shop_id: int, product_id: int) -> dict[str, Any] | None:
        """Update an inventory entry (change shop or product)."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                UPDATE inventory
                SET shop_id = :shop_id,
                    product_id = :product_id
                WHERE id = :id
                """,
                {"id": inventory_id, "shop_id": shop_id, "product_id": product_id},
            )

            await self.connection.commit()

            if cursor.rowcount > 0:
                return await self.get_by_shop_and_product(shop_id, product_id)
            return None

    async def get_product_availability_count(self, product_id: int) -> int:
        """Get the count of shops that have a specific product."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT COUNT(*) FROM inventory WHERE product_id = :product_id
                """,
                {"product_id": product_id},
            )
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def get_shop_product_count(self, shop_id: int) -> int:
        """Get the count of products in a specific shop."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT COUNT(*) FROM inventory WHERE shop_id = :shop_id
                """,
                {"shop_id": shop_id},
            )
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def bulk_add_products(self, shop_id: int, product_ids: list[int]) -> int:
        """Add multiple products to a shop's inventory."""
        added_count = 0
        async with self.get_cursor() as cursor:
            for product_id in product_ids:
                await cursor.execute(
                    """
                    MERGE INTO inventory i
                    USING (SELECT :shop_id AS shop_id, :product_id AS product_id FROM dual) src
                    ON (i.shop_id = src.shop_id AND i.product_id = src.product_id)
                    WHEN NOT MATCHED THEN
                        INSERT (shop_id, product_id)
                        VALUES (:shop_id2, :product_id2)
                    """,
                    {
                        "shop_id": shop_id,
                        "shop_id2": shop_id,
                        "product_id": product_id,
                        "product_id2": product_id,
                    },
                )
                added_count += cursor.rowcount

            await self.connection.commit()
            return added_count

    async def bulk_remove_products(self, shop_id: int, product_ids: list[int]) -> int:
        """Remove multiple products from a shop's inventory."""
        removed_count = 0
        async with self.get_cursor() as cursor:
            for product_id in product_ids:
                await cursor.execute(
                    """
                    DELETE FROM inventory
                    WHERE shop_id = :shop_id AND product_id = :product_id
                    """,
                    {"shop_id": shop_id, "product_id": product_id},
                )
                removed_count += cursor.rowcount

            await self.connection.commit()
            return removed_count
