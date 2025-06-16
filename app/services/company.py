"""Company service using raw Oracle SQL."""

from __future__ import annotations

from typing import Any

from app.services.base import BaseService


class CompanyService(BaseService):
    """Handles database operations for companies using raw SQL."""

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all companies."""
        async with self.get_cursor() as cursor:
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

    async def get_by_id(self, company_id: int) -> dict[str, Any] | None:
        """Get company by ID."""
        async with self.get_cursor() as cursor:
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

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get company by name."""
        async with self.get_cursor() as cursor:
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

    async def get_with_products(self, company_id: int) -> dict[str, Any] | None:
        """Get company with all its products."""
        async with self.get_cursor() as cursor:
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
                    "description": row[3],
                    "embedding": list(row[4]) if row[4] else None,
                    "embedding_generated_on": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                }
                async for row in cursor
            ]

            company["products"] = products
            return company

    async def exists_by_name(self, name: str) -> bool:
        """Check if company exists by name."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT COUNT(*) FROM company WHERE name = :name
                """,
                {"name": name},
            )
            result = await cursor.fetchone()
            count = result[0] if result else 0
            return count > 0

    async def create_company(self, name: str) -> dict[str, Any] | None:
        """Create a new company."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO company (name)
                VALUES (:name)
                RETURNING id INTO :id
                """,
                {"name": name, "id": cursor.var(int)},
            )

            company_id = cursor.bindvars["id"].getvalue()  # type: ignore[call-overload]
            await self.connection.commit()

            # Return the created company
            return await self.get_by_id(company_id)

    async def update_company(self, company_id: int, name: str) -> dict[str, Any] | None:
        """Update a company."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                UPDATE company
                SET name = :name
                WHERE id = :id
                """,
                {"id": company_id, "name": name},
            )

            await self.connection.commit()

            if cursor.rowcount > 0:
                return await self.get_by_id(company_id)
            return None

    async def delete_company(self, company_id: int) -> bool:
        """Delete a company (cascade deletes products due to FK constraint)."""
        async with self.get_cursor() as cursor:
            await cursor.execute("DELETE FROM company WHERE id = :id", {"id": company_id})
            await self.connection.commit()
            return cursor.rowcount > 0

    async def upsert_company(self, name: str) -> dict[str, Any] | None:
        """Insert or update company by name using MERGE."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                MERGE INTO company c
                USING (SELECT :name AS name FROM dual) src
                ON (c.name = src.name)
                WHEN MATCHED THEN
                    UPDATE SET name = src.name  -- Triggers updated_at
                WHEN NOT MATCHED THEN
                    INSERT (name)
                    VALUES (:name2)
                """,
                {"name": name, "name2": name},
            )

            await self.connection.commit()

            # Return the company (either existing or newly created)
            return await self.get_by_name(name)

    async def get_product_count(self, company_id: int) -> int:
        """Get the count of products for a company."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT COUNT(*) FROM product WHERE company_id = :company_id
                """,
                {"company_id": company_id},
            )
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def search_by_name(self, search_term: str) -> list[dict[str, Any]]:
        """Search companies by name pattern."""
        async with self.get_cursor() as cursor:
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
