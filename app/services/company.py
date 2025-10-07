"""Company service using SQLSpec driver patterns."""


from typing import Any

from app.services.base import SQLSpecService


class CompanyService(SQLSpecService):
    """Handles database operations for companies using SQLSpec patterns."""

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all companies."""
        return await self.driver.select(
            """
            SELECT
                id,
                name,
                created_at,
                updated_at
            FROM company
            ORDER BY name
            """
        )

    async def get_by_id(self, company_id: int) -> dict[str, Any] | None:
        """Get company by ID."""
        return await self.driver.select_one_or_none(
            """
            SELECT
                id,
                name,
                created_at,
                updated_at
            FROM company
            WHERE id = :id
            """,
            id=company_id,
        )

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get company by name."""
        return await self.driver.select_one_or_none(
            """
            SELECT
                id,
                name,
                created_at,
                updated_at
            FROM company
            WHERE name = :name
            """,
            name=name,
        )

    async def get_with_products(self, company_id: int) -> dict[str, Any] | None:
        """Get company with all its products."""
        # Get company first
        company = await self.get_by_id(company_id)
        if not company:
            return None

        # Get products for this company
        products = await self.driver.select(
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
            company_id=company_id,
        )

        company["products"] = products
        return company

    async def exists_by_name(self, name: str) -> bool:
        """Check if company exists by name."""
        result = await self.driver.select_one_or_none(
            """
            SELECT COUNT(*) as count FROM company WHERE name = :name
            """,
            name=name,
        )
        count = result["count"] if result else 0
        return count > 0

    async def create_company(self, name: str) -> dict[str, Any] | None:
        """Create a new company."""
        # Insert and get the generated ID
        result = await self.driver.select_one_or_none(
            """
            INSERT INTO company (name)
            VALUES (:name)
            RETURNING id
            """,
            name=name,
        )

        if result:
            company_id = result["id"]
            # Return the created company
            return await self.get_by_id(company_id)

        return None

    async def update_company(self, company_id: int, name: str) -> dict[str, Any] | None:
        """Update a company."""
        rowcount = await self.driver.execute(
            """
            UPDATE company
            SET name = :name
            WHERE id = :id
            """,
            id=company_id,
            name=name,
        )

        if rowcount > 0:
            return await self.get_by_id(company_id)
        return None

    async def delete_company(self, company_id: int) -> bool:
        """Delete a company (cascade deletes products due to FK constraint)."""
        rowcount = await self.driver.execute(
            "DELETE FROM company WHERE id = :id",
            id=company_id,
        )
        return rowcount > 0

    async def upsert_company(self, name: str) -> dict[str, Any] | None:
        """Insert or update company by name using MERGE."""
        await self.driver.execute(
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
            name=name,
            name2=name,
        )

        # Return the company (either existing or newly created)
        return await self.get_by_name(name)

    async def get_product_count(self, company_id: int) -> int:
        """Get the count of products for a company."""
        result = await self.driver.select_one_or_none(
            """
            SELECT COUNT(*) as count FROM product WHERE company_id = :company_id
            """,
            company_id=company_id,
        )
        return result["count"] if result else 0

    async def search_by_name(self, search_term: str) -> list[dict[str, Any]]:
        """Search companies by name pattern."""
        return await self.driver.select(
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
            search_term=f"%{search_term}%",
        )
