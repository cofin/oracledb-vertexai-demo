from app.schemas import CompanyDTO
from .base import BaseRepository

class CompanyRepository(BaseRepository[CompanyDTO]):
    def __init__(self, connection):
        super().__init__(connection, CompanyDTO)

    async def get_all(self) -> list[CompanyDTO]:
        query = "SELECT id, name, created_at, updated_at FROM company ORDER BY name"
        return await self.fetch_all(query)

    async def get_by_id(self, company_id: int) -> CompanyDTO | None:
        query = "SELECT id, name, created_at, updated_at FROM company WHERE id = :id"
        return await self.fetch_one(query, {"id": company_id})

    async def get_by_name(self, name: str) -> CompanyDTO | None:
        query = "SELECT id, name, created_at, updated_at FROM company WHERE name = :name"
        return await self.fetch_one(query, {"name": name})

    async def create_company(self, name: str) -> CompanyDTO | None:
        query = "INSERT INTO company (name) VALUES (:name) RETURNING id INTO :id"
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"name": name, "id": cursor.var(int)})
            company_id = cursor.bindvars["id"].getvalue()
            await self.connection.commit()
            return await self.get_by_id(company_id)

    async def update_company(self, company_id: int, name: str) -> CompanyDTO | None:
        query = "UPDATE company SET name = :name WHERE id = :id"
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"id": company_id, "name": name})
            await self.connection.commit()
            if cursor.rowcount > 0:
                return await self.get_by_id(company_id)
            return None

    async def delete_company(self, company_id: int) -> bool:
        query = "DELETE FROM company WHERE id = :id"
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"id": company_id})
            await self.connection.commit()
            return cursor.rowcount > 0
