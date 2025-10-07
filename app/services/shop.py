"""Shop service using SQLSpec driver patterns."""


from typing import Any

from app.services.base import SQLSpecService


class ShopService(SQLSpecService):
    """Handles database operations for shops using SQLSpec patterns."""

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all shops."""
        return await self.driver.select(
            """
            SELECT
                id,
                name,
                address,
                created_at,
                updated_at
            FROM shop
            ORDER BY name
            """
        )

    async def get_by_id(self, shop_id: int) -> dict[str, Any] | None:
        """Get shop by ID."""
        return await self.driver.select_one_or_none(
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
            id=shop_id,
        )

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get shop by name."""
        return await self.driver.select_one_or_none(
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
            name=name,
        )

    async def get_with_inventory(self, shop_id: int) -> dict[str, Any] | None:
        """Get shop with all its inventory."""
        # Get shop first
        shop = await self.get_by_id(shop_id)
        if not shop:
            return None

        # Get inventory for this shop
        inventory_items = await self.driver.select(
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
            shop_id=shop_id,
        )

        shop["inventory"] = inventory_items
        return shop

    async def create_shop(self, name: str, address: str) -> dict[str, Any] | None:
        """Create a new shop."""
        # Insert and get the generated ID
        result = await self.driver.select_one_or_none(
            """
            INSERT INTO shop (name, address)
            VALUES (:name, :address)
            RETURNING id
            """,
            name=name,
            address=address,
        )

        if result:
            shop_id = result["id"]
            # Return the created shop
            return await self.get_by_id(shop_id)

        return None

    async def update_shop(self, shop_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a shop."""
        # Build UPDATE statement with safe field mapping
        field_mapping = {
            "name": "name = :name",
            "address": "address = :address",
        }

        set_clauses = []
        params: dict[str, Any] = {"id": shop_id}

        for field, value in updates.items():
            if field in field_mapping:
                set_clauses.append(field_mapping[field])
                params[field] = value

        if not set_clauses:
            return await self.get_by_id(shop_id)

        sql = f"UPDATE shop SET {', '.join(set_clauses)} WHERE id = :id"  # noqa: S608

        rowcount = await self.driver.execute(sql, **params)

        if rowcount > 0:
            return await self.get_by_id(shop_id)
        return None

    async def delete_shop(self, shop_id: int) -> bool:
        """Delete a shop (cascade deletes inventory due to FK constraint)."""
        rowcount = await self.driver.execute(
            "DELETE FROM shop WHERE id = :id",
            id=shop_id,
        )
        return rowcount > 0

    async def upsert_shop(self, name: str, address: str) -> dict[str, Any] | None:
        """Insert or update shop by name using MERGE."""
        await self.driver.execute(
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
            name=name,
            name2=name,
            address=address,
            address2=address,
        )

        # Return the shop (either existing or newly created)
        return await self.get_by_name(name)

    async def get_inventory_count(self, shop_id: int) -> int:
        """Get the count of inventory items for a shop."""
        result = await self.driver.select_one_or_none(
            """
            SELECT COUNT(*) as count FROM inventory WHERE shop_id = :shop_id
            """,
            shop_id=shop_id,
        )
        return result["count"] if result else 0

    async def search_by_address(self, search_term: str) -> list[dict[str, Any]]:
        """Search shops by address pattern."""
        return await self.driver.select(
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
            search_term=f"%{search_term}%",
        )

    async def add_inventory(self, shop_id: int, product_id: int) -> bool:
        """Add a product to shop's inventory."""
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
        return rowcount > 0

    async def remove_inventory(self, shop_id: int, product_id: int) -> bool:
        """Remove a product from shop's inventory."""
        rowcount = await self.driver.execute(
            """
            DELETE FROM inventory
            WHERE shop_id = :shop_id AND product_id = :product_id
            """,
            shop_id=shop_id,
            product_id=product_id,
        )
        return rowcount > 0
