"""Company service with both SQLAlchemy and raw SQL implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from app.db import models as m

if TYPE_CHECKING:
    import oracledb


class CompanyService(SQLAlchemyAsyncRepositoryService[m.Company]):
    """Handles database operations for companies using SQLAlchemy."""

    class Repo(SQLAlchemyAsyncRepository[m.Company]):
        """Company repository."""

        model_type = m.Company

    repository_type = Repo
    match_fields = ["name"]

    async def get_by_name(self, name: str) -> m.Company | None:
        """Get company by name."""
        return await self.get_one_or_none(name=name)

    async def exists_by_name(self, name: str) -> bool:
        """Check if company exists by name."""
        return await self.exists(name=name)


class RawCompanyService:
    """Handles database operations for companies using raw SQL."""

    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        """Initialize with Oracle connection."""
        self.connection = connection

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all companies."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute("""
                SELECT
                    id,
                    name,
                    created_at,
                    updated_at
                FROM company
                ORDER BY name
            """)

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                }
                async for row in cursor
            ]
        finally:
            cursor.close()

    async def get_by_id(self, company_id: int) -> dict[str, Any] | None:
        """Get company by ID."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    id,
                    name,
                    created_at,
                    updated_at
                FROM company
                WHERE id = :id
                """,
                {"id": company_id},
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                }
            return None
        finally:
            cursor.close()

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get company by name."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    id,
                    name,
                    created_at,
                    updated_at
                FROM company
                WHERE name = :name
                """,
                {"name": name},
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                }
            return None
        finally:
            cursor.close()

    async def get_with_products(self, company_id: int) -> dict[str, Any] | None:
        """Get company with all its products."""
        cursor = self.connection.cursor()
        try:
            # Get company first
            company = await self.get_by_id(company_id)
            if not company:
                return None

            # Get products for this company
            await cursor.execute(
                """
                SELECT
                    id,
                    name,
                    current_price,
                    "SIZE" as size,
                    description,
                    embedding,
                    embedding_generated_on,
                    created_at,
                    updated_at
                FROM product
                WHERE company_id = :company_id
                ORDER BY name
                """,
                {"company_id": company_id},
            )

            products = [
                {
                    "id": row[0],
                    "name": row[1],
                    "current_price": row[2],
                    "size": row[3],
                    "description": row[4],
                    "embedding": list(row[5]) if row[5] else None,
                    "embedding_generated_on": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                }
                async for row in cursor
            ]

            company["products"] = products
            return company
        finally:
            cursor.close()

    async def exists_by_name(self, name: str) -> bool:
        """Check if company exists by name."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT COUNT(*) FROM company WHERE name = :name
                """,
                {"name": name},
            )
            result = await cursor.fetchone()
            count = result[0] if result else 0
            return count > 0
        finally:
            cursor.close()

    async def create_company(self, name: str) -> dict[str, Any] | None:
        """Create a new company."""
        cursor = self.connection.cursor()
        try:
            # Get next ID from sequence
            await cursor.execute("SELECT company_id_seq.NEXTVAL FROM dual")
            company_id = (await cursor.fetchone())[0]

            await cursor.execute(
                """
                INSERT INTO company (id, name)
                VALUES (:id, :name)
                """,
                {"id": company_id, "name": name},
            )

            await self.connection.commit()

            # Return the created company
            return await self.get_by_id(company_id)
        finally:
            cursor.close()

    async def update_company(self, company_id: int, name: str) -> dict[str, Any] | None:
        """Update a company."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                UPDATE company
                SET name = :name,
                    updated_at = SYSTIMESTAMP
                WHERE id = :id
                """,
                {"id": company_id, "name": name},
            )

            await self.connection.commit()

            if cursor.rowcount > 0:
                return await self.get_by_id(company_id)
            return None
        finally:
            cursor.close()

    async def delete_company(self, company_id: int) -> bool:
        """Delete a company (cascade deletes products due to FK constraint)."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute("DELETE FROM company WHERE id = :id", {"id": company_id})
            await self.connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()

    async def upsert_company(self, name: str) -> dict[str, Any] | None:
        """Insert or update company by name using MERGE."""
        cursor = self.connection.cursor()
        try:
            # Get next ID in case we need to insert
            await cursor.execute("SELECT company_id_seq.NEXTVAL FROM dual")
            next_id = (await cursor.fetchone())[0]

            await cursor.execute(
                """
                MERGE INTO company c
                USING (SELECT :name AS name FROM dual) src
                ON (c.name = src.name)
                WHEN MATCHED THEN
                    UPDATE SET updated_at = SYSTIMESTAMP
                WHEN NOT MATCHED THEN
                    INSERT (id, name)
                    VALUES (:id, :name2)
                """,
                {"name": name, "name2": name, "id": next_id},
            )

            await self.connection.commit()

            # Return the company (either existing or newly created)
            return await self.get_by_name(name)
        finally:
            cursor.close()

    async def get_product_count(self, company_id: int) -> int:
        """Get the count of products for a company."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT COUNT(*) FROM product WHERE company_id = :company_id
                """,
                {"company_id": company_id},
            )
            result = await cursor.fetchone()
            return result[0] if result else 0
        finally:
            cursor.close()

    async def search_by_name(self, search_term: str) -> list[dict[str, Any]]:
        """Search companies by name pattern."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    id,
                    name,
                    created_at,
                    updated_at
                FROM company
                WHERE UPPER(name) LIKE UPPER(:search_term)
                ORDER BY name
                """,
                {"search_term": f"%{search_term}%"},
            )

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                }
                async for row in cursor
            ]
        finally:
            cursor.close()
