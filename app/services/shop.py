"""Shop service with both SQLAlchemy and raw SQL implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from advanced_alchemy.filters import LimitOffset
from advanced_alchemy.repository import SQLAlchemyAsyncSlugRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy.orm import selectinload

from app.db import models as m

if TYPE_CHECKING:
    from collections.abc import Sequence

    import oracledb


class ShopService(SQLAlchemyAsyncRepositoryService[m.Shop]):
    """Handles database operations for shops."""

    class Repo(SQLAlchemyAsyncSlugRepository[m.Shop]):
        """Shop repository with slug support."""

        model_type = m.Shop

    repository_type = Repo
    match_fields = ["name"]

    async def get_by_slug(self, slug: str) -> m.Shop | None:
        """Get shop by slug."""
        return await self.get_one_or_none(slug=slug)

    async def get_with_inventory(self, shop_id: int) -> m.Shop | None:
        """Get shop with inventory loaded."""
        return await self.get_one_or_none(m.Shop.id == shop_id, load=[selectinload(m.Shop.inventory)])

    async def find_by_location(self, latitude: float, longitude: float, radius_km: float = 10) -> Sequence[m.Shop]:
        """Find shops within radius of location."""
        # Simple implementation - in production you'd use spatial queries
        return await self.list(LimitOffset(limit=10, offset=0))


class RawShopService:
    """Handles database operations for shops using raw SQL."""

    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        """Initialize with Oracle connection."""
        self.connection = connection

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all shops."""
        cursor = self.connection.cursor()
        try:
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
        finally:
            cursor.close()

    async def get_by_id(self, shop_id: int) -> dict[str, Any] | None:
        """Get shop by ID."""
        cursor = self.connection.cursor()
        try:
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
        finally:
            cursor.close()

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get shop by name."""
        cursor = self.connection.cursor()
        try:
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
        finally:
            cursor.close()

    async def get_with_inventory(self, shop_id: int) -> dict[str, Any] | None:
        """Get shop with all its inventory."""
        cursor = self.connection.cursor()
        try:
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
                    p."SIZE" as size,
                    p.description,
                    c.name as company_name,
                    i.created_at,
                    i.updated_at
                FROM inventory i
                INNER JOIN product p ON i.product_id = p.id
                INNER JOIN company c ON p.company_id = c.id
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
                    "size": row[4],
                    "description": row[5],
                    "company_name": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                }
                async for row in cursor
            ]

            shop["inventory"] = inventory_items
            return shop
        finally:
            cursor.close()

    async def create_shop(self, name: str, address: str) -> dict[str, Any] | None:
        """Create a new shop."""
        cursor = self.connection.cursor()
        try:
            # Get next ID from sequence
            await cursor.execute("SELECT shop_id_seq.NEXTVAL FROM dual")
            shop_id = (await cursor.fetchone())[0]

            await cursor.execute(
                """
                INSERT INTO shop (id, name, address)
                VALUES (:id, :name, :address)
                """,
                {"id": shop_id, "name": name, "address": address},
            )

            await self.connection.commit()

            # Return the created shop
            return await self.get_by_id(shop_id)
        finally:
            cursor.close()

    async def update_shop(self, shop_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a shop."""
        cursor = self.connection.cursor()
        try:
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

            set_clauses.append("updated_at = SYSTIMESTAMP")
            sql = f"UPDATE shop SET {', '.join(set_clauses)} WHERE id = :id"  # noqa: S608

            await cursor.execute(sql, params)
            await self.connection.commit()

            if cursor.rowcount > 0:
                return await self.get_by_id(shop_id)
            return None
        finally:
            cursor.close()

    async def delete_shop(self, shop_id: int) -> bool:
        """Delete a shop (cascade deletes inventory due to FK constraint)."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute("DELETE FROM shop WHERE id = :id", {"id": shop_id})
            await self.connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()

    async def upsert_shop(self, name: str, address: str) -> dict[str, Any] | None:
        """Insert or update shop by name using MERGE."""
        cursor = self.connection.cursor()
        try:
            # Get next ID in case we need to insert
            await cursor.execute("SELECT shop_id_seq.NEXTVAL FROM dual")
            next_id = (await cursor.fetchone())[0]

            await cursor.execute(
                """
                MERGE INTO shop s
                USING (SELECT :name AS name FROM dual) src
                ON (s.name = src.name)
                WHEN MATCHED THEN
                    UPDATE SET
                        address = :address,
                        updated_at = SYSTIMESTAMP
                WHEN NOT MATCHED THEN
                    INSERT (id, name, address)
                    VALUES (:id, :name2, :address2)
                """,
                {
                    "name": name,
                    "name2": name,
                    "address": address,
                    "address2": address,
                    "id": next_id,
                },
            )

            await self.connection.commit()

            # Return the shop (either existing or newly created)
            return await self.get_by_name(name)
        finally:
            cursor.close()

    async def get_inventory_count(self, shop_id: int) -> int:
        """Get the count of inventory items for a shop."""
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

    async def search_by_address(self, search_term: str) -> list[dict[str, Any]]:
        """Search shops by address pattern."""
        cursor = self.connection.cursor()
        try:
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
        finally:
            cursor.close()

    async def add_inventory(self, shop_id: int, product_id: int) -> bool:
        """Add a product to shop's inventory."""
        cursor = self.connection.cursor()
        try:
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
        finally:
            cursor.close()

    async def remove_inventory(self, shop_id: int, product_id: int) -> bool:
        """Remove a product from shop's inventory."""
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
