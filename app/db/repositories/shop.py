from app.schemas import ShopDTO
from .base import BaseRepository

class ShopRepository(BaseRepository[ShopDTO]):
    def __init__(self, connection):
        super().__init__(connection, ShopDTO)

    async def get_all(self) -> list[ShopDTO]:
        query = "SELECT id, name, address, created_at, updated_at FROM shop ORDER BY name"
        return await self.fetch_all(query)

    async def get_by_id(self, shop_id: int) -> ShopDTO | None:
        query = "SELECT id, name, address, created_at, updated_at FROM shop WHERE id = :id"
        return await self.fetch_one(query, {"id": shop_id})

    async def get_by_name(self, name: str) -> ShopDTO | None:
        query = "SELECT id, name, address, created_at, updated_at FROM shop WHERE name = :name"
        return await self.fetch_one(query, {"name": name})

    async def create_shop(self, name: str, address: str) -> ShopDTO | None:
        query = "INSERT INTO shop (name, address) VALUES (:name, :address) RETURNING id INTO :id"
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"name": name, "address": address, "id": cursor.var(int)})
            shop_id = cursor.bindvars["id"].getvalue()
            await self.connection.commit()
            return await self.get_by_id(shop_id)

    async def update_shop(self, shop_id: int, updates: dict[str, any]) -> ShopDTO | None:
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
        sql = f"UPDATE shop SET {', '.join(set_clauses)} WHERE id = :id"
        async with self.connection.cursor() as cursor:
            await cursor.execute(sql, params)
            await self.connection.commit()
            if cursor.rowcount > 0:
                return await self.get_by_id(shop_id)
            return None

    async def delete_shop(self, shop_id: int) -> bool:
        query = "DELETE FROM shop WHERE id = :id"
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"id": shop_id})
            await self.connection.commit()
            return cursor.rowcount > 0
