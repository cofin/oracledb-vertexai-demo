"""Inventory service with both SQLAlchemy and raw SQL implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import and_

from app.db import models as m

if TYPE_CHECKING:
    from collections.abc import Sequence

    import oracledb


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


class RawInventoryService:
    """Handles database operations for inventory using raw SQL."""

    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        """Initialize with Oracle connection."""
        self.connection = connection

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all inventory entries with shop and product information."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute("""
                SELECT
                    i.id,
                    i.shop_id,
                    s.name as shop_name,
                    s.address as shop_address,
                    i.product_id,
                    p.name as product_name,
                    p.current_price,
                    p."SIZE" as size,
                    p.description,
                    c.name as company_name,
                    i.created_at,
                    i.updated_at
                FROM inventory i
                INNER JOIN shop s ON i.shop_id = s.id
                INNER JOIN product p ON i.product_id = p.id
                INNER JOIN company c ON p.company_id = c.id
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
                    "size": row[7],
                    "description": row[8],
                    "company_name": row[9],
                    "created_at": row[10],
                    "updated_at": row[11],
                }
                async for row in cursor
            ]
        finally:
            cursor.close()

    async def get_by_shop_and_product(self, shop_id: int, product_id: int) -> dict[str, Any] | None:
        """Get inventory by shop and product."""
        cursor = self.connection.cursor()
        try:
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
                    p."SIZE" as size,
                    p.description,
                    c.name as company_name,
                    i.created_at,
                    i.updated_at
                FROM inventory i
                INNER JOIN shop s ON i.shop_id = s.id
                INNER JOIN product p ON i.product_id = p.id
                INNER JOIN company c ON p.company_id = c.id
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
                    "size": row[7],
                    "description": row[8],
                    "company_name": row[9],
                    "created_at": row[10],
                    "updated_at": row[11],
                }
            return None
        finally:
            cursor.close()

    async def get_products_in_shop(self, shop_id: int) -> list[dict[str, Any]]:
        """Get all products available in a shop."""
        cursor = self.connection.cursor()
        try:
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
                    p."SIZE" as size,
                    p.description,
                    c.name as company_name,
                    i.created_at,
                    i.updated_at
                FROM inventory i
                INNER JOIN shop s ON i.shop_id = s.id
                INNER JOIN product p ON i.product_id = p.id
                INNER JOIN company c ON p.company_id = c.id
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
                    "size": row[7],
                    "description": row[8],
                    "company_name": row[9],
                    "created_at": row[10],
                    "updated_at": row[11],
                }
                async for row in cursor
            ]
        finally:
            cursor.close()

    async def get_shops_with_product(self, product_id: int) -> list[dict[str, Any]]:
        """Get all shops that have a product."""
        cursor = self.connection.cursor()
        try:
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
                    p."SIZE" as size,
                    p.description,
                    c.name as company_name,
                    i.created_at,
                    i.updated_at
                FROM inventory i
                INNER JOIN shop s ON i.shop_id = s.id
                INNER JOIN product p ON i.product_id = p.id
                INNER JOIN company c ON p.company_id = c.id
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
                    "size": row[7],
                    "description": row[8],
                    "company_name": row[9],
                    "created_at": row[10],
                    "updated_at": row[11],
                }
                async for row in cursor
            ]
        finally:
            cursor.close()

    async def add_product_to_shop(self, shop_id: int, product_id: int) -> dict[str, Any] | None:
        """Add a product to a shop's inventory."""
        cursor = self.connection.cursor()
        try:
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
        finally:
            cursor.close()

    async def remove_product_from_shop(self, shop_id: int, product_id: int) -> bool:
        """Remove a product from a shop's inventory."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                DELETE FROM inventory
                WHERE shop_id = :shop_id AND product_id = :product_id
                """,
                {"shop_id": shop_id, "product_id": product_id},
            )

            await self.connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()

    async def delete_by_id(self, inventory_id: str) -> bool:
        """Delete an inventory entry by ID."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                DELETE FROM inventory WHERE id = :id
                """,
                {"id": inventory_id},
            )

            await self.connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()

    async def update_inventory(self, inventory_id: str, shop_id: int, product_id: int) -> dict[str, Any] | None:
        """Update an inventory entry (change shop or product)."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                UPDATE inventory
                SET shop_id = :shop_id,
                    product_id = :product_id,
                    updated_at = SYSTIMESTAMP
                WHERE id = :id
                """,
                {"id": inventory_id, "shop_id": shop_id, "product_id": product_id},
            )

            await self.connection.commit()

            if cursor.rowcount > 0:
                return await self.get_by_shop_and_product(shop_id, product_id)
            return None
        finally:
            cursor.close()

    async def get_product_availability_count(self, product_id: int) -> int:
        """Get the count of shops that have a specific product."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT COUNT(*) FROM inventory WHERE product_id = :product_id
                """,
                {"product_id": product_id},
            )
            result = await cursor.fetchone()
            return result[0] if result else 0
        finally:
            cursor.close()

    async def get_shop_product_count(self, shop_id: int) -> int:
        """Get the count of products in a specific shop."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT COUNT(*) FROM inventory WHERE shop_id = :shop_id
                """,
                {"shop_id": shop_id},
            )
            result = await cursor.fetchone()
            return result[0] if result else 0
        finally:
            cursor.close()

    async def bulk_add_products(self, shop_id: int, product_ids: list[int]) -> int:
        """Add multiple products to a shop's inventory."""
        cursor = self.connection.cursor()
        added_count = 0
        try:
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
        finally:
            cursor.close()

    async def bulk_remove_products(self, shop_id: int, product_ids: list[int]) -> int:
        """Remove multiple products from a shop's inventory."""
        cursor = self.connection.cursor()
        removed_count = 0
        try:
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
        finally:
            cursor.close()
