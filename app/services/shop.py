"""Shop service using raw Oracle SQL."""

from __future__ import annotations

from typing import Any

from app.services.base import BaseService


class ShopService(BaseService):
    """Handles database operations for shops using raw SQL."""

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all shops."""
        async with self.get_cursor() as cursor:
            await cursor.execute("""
                SELECT
                    id,
                    name,
                    address,
                    created_at,
                    updated_at
                FROM shop
                ORDER BY name
            """)

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "address": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                }
                async for row in cursor
            ]

    async def get_by_id(self, shop_id: int) -> dict[str, Any] | None:
        """Get shop by ID."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT
                    id,
                    name,
                    address,
                    created_at,
                    updated_at
                FROM shop
                WHERE id = :id
                """,
                {"id": shop_id},
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "address": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                }
            return None

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get shop by name."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT
                    id,
                    name,
                    address,
                    created_at,
                    updated_at
                FROM shop
                WHERE name = :name
                """,
                {"name": name},
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "address": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                }
            return None

    async def get_with_inventory(self, shop_id: int) -> dict[str, Any] | None:
        """Get shop with all its inventory."""
        async with self.get_cursor() as cursor:
            # Get shop first
            shop = await self.get_by_id(shop_id)
            if not shop:
                return None

            # Get inventory for this shop
            await cursor.execute(
                """
                SELECT
                    i.shop_id,
                    i.product_id,
                    p.name as product_name,
                    p.current_price,
                    p.description,
                    c.name as company_name,
                    i.created_at,
                    i.updated_at
                FROM inventory i
                JOIN product p ON i.product_id = p.id
                JOIN company c ON p.company_id = c.id
                WHERE i.shop_id = :shop_id
                ORDER BY p.name
                """,
                {"shop_id": shop_id},
            )

            inventory_items = [
                {
                    "shop_id": row[0],
                    "product_id": row[1],
                    "product_name": row[2],
                    "current_price": row[3],
                    "description": row[4],
                    "company_name": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                }
                async for row in cursor
            ]

            shop["inventory"] = inventory_items
            return shop

    async def create_shop(self, name: str, address: str) -> dict[str, Any] | None:
        """Create a new shop."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO shop (name, address)
                VALUES (:name, :address)
                RETURNING id INTO :id
                """,
                {"name": name, "address": address, "id": cursor.var(int)},
            )

            shop_id = cursor.bindvars["id"].getvalue()  # type: ignore[call-overload]
            await self.connection.commit()

            # Return the created shop
            return await self.get_by_id(shop_id)

    async def update_shop(self, shop_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a shop."""
        async with self.get_cursor() as cursor:
            # Build UPDATE statement with safe field mapping
            field_mapping = {
                "name": "name = :name",
                "address": "address = :address",
            }

            set_clauses = []
            params = {"id": shop_id}

            for field, value in updates.items():
                if field in field_mapping:
                    set_clauses.append(field_mapping[field])
                    params[field] = value

            if not set_clauses:
                return await self.get_by_id(shop_id)

            sql = f"UPDATE shop SET {', '.join(set_clauses)} WHERE id = :id"  # noqa: S608

            await cursor.execute(sql, params)
            await self.connection.commit()

            if cursor.rowcount > 0:
                return await self.get_by_id(shop_id)
            return None

    async def delete_shop(self, shop_id: int) -> bool:
        """Delete a shop (cascade deletes inventory due to FK constraint)."""
        async with self.get_cursor() as cursor:
            await cursor.execute("DELETE FROM shop WHERE id = :id", {"id": shop_id})
            await self.connection.commit()
            return cursor.rowcount > 0

    async def upsert_shop(self, name: str, address: str) -> dict[str, Any] | None:
        """Insert or update shop by name using MERGE."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                MERGE INTO shop s
                USING (SELECT :name AS name FROM dual) src
                ON (s.name = src.name)
                WHEN MATCHED THEN
                    UPDATE SET
                        address = :address
                WHEN NOT MATCHED THEN
                    INSERT (name, address)
                    VALUES (:name2, :address2)
                """,
                {
                    "name": name,
                    "name2": name,
                    "address": address,
                    "address2": address,
                },
            )

            await self.connection.commit()

            # Return the shop (either existing or newly created)
            return await self.get_by_name(name)

    async def get_inventory_count(self, shop_id: int) -> int:
        """Get the count of inventory items for a shop."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT COUNT(*) FROM inventory WHERE shop_id = :shop_id
                """,
                {"shop_id": shop_id},
            )
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def search_by_address(self, search_term: str) -> list[dict[str, Any]]:
        """Search shops by address pattern."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT
                    id,
                    name,
                    address,
                    created_at,
                    updated_at
                FROM shop
                WHERE UPPER(address) LIKE UPPER(:search_term)
                ORDER BY name
                """,
                {"search_term": f"%{search_term}%"},
            )

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "address": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                }
                async for row in cursor
            ]

    async def add_inventory(self, shop_id: int, product_id: int) -> bool:
        """Add a product to shop's inventory."""
        async with self.get_cursor() as cursor:
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
            return cursor.rowcount > 0

    async def remove_inventory(self, shop_id: int, product_id: int) -> bool:
        """Remove a product from shop's inventory."""
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
