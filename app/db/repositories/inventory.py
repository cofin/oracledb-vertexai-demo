from app.schemas import InventoryDTO
from .base import BaseRepository

class InventoryRepository(BaseRepository[InventoryDTO]):
    def __init__(self, connection):
        super().__init__(connection, InventoryDTO)

    async def get_all(self) -> list[InventoryDTO]:
        query = """
            SELECT
                i.id, i.shop_id, s.name as shop_name, s.address as shop_address,
                i.product_id, p.name as product_name, p.current_price, p.description,
                c.name as company_name, i.created_at, i.updated_at
            FROM inventory i
            JOIN shop s ON i.shop_id = s.id
            JOIN product p ON i.product_id = p.id
            JOIN company c ON p.company_id = c.id
            ORDER BY s.name, p.name
        """
        return await self.fetch_all(query)

    async def get_by_shop_and_product(self, shop_id: int, product_id: int) -> InventoryDTO | None:
        query = """
            SELECT
                i.id, i.shop_id, s.name as shop_name, s.address as shop_address,
                i.product_id, p.name as product_name, p.current_price, p.description,
                c.name as company_name, i.created_at, i.updated_at
            FROM inventory i
            JOIN shop s ON i.shop_id = s.id
            JOIN product p ON i.product_id = p.id
            JOIN company c ON p.company_id = c.id
            WHERE i.shop_id = :shop_id AND i.product_id = :product_id
        """
        return await self.fetch_one(query, {"shop_id": shop_id, "product_id": product_id})

    async def add_product_to_shop(self, shop_id: int, product_id: int) -> InventoryDTO | None:
        query = """
            MERGE INTO inventory i
            USING (SELECT :shop_id AS shop_id, :product_id AS product_id FROM dual) src
            ON (i.shop_id = src.shop_id AND i.product_id = src.product_id)
            WHEN NOT MATCHED THEN
                INSERT (shop_id, product_id)
                VALUES (:shop_id2, :product_id2)
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                {
                    "shop_id": shop_id,
                    "shop_id2": shop_id,
                    "product_id": product_id,
                    "product_id2": product_id,
                },
            )
            await self.connection.commit()
        return await self.get_by_shop_and_product(shop_id, product_id)

    async def remove_product_from_shop(self, shop_id: int, product_id: int) -> bool:
        query = "DELETE FROM inventory WHERE shop_id = :shop_id AND product_id = :product_id"
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"shop_id": shop_id, "product_id": product_id})
            await self.connection.commit()
            return cursor.rowcount > 0
