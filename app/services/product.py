"""Product service using SQLSpec driver patterns."""


from typing import Any

from app.services.base import SQLSpecService


class ProductService(SQLSpecService):
    """Handles database operations for products using SQLSpec patterns."""

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all products with company information."""
        return await self.driver.select(
            """
            SELECT
                p.id,
                p.name,
                p.current_price,
                p.description,
                p.embedding,
                p.embedding_generated_on,
                p.created_at,
                p.updated_at,
                p.company_id,
                c.name as company_name
            FROM product p
            JOIN company c ON p.company_id = c.id
            ORDER BY p.name
            """
        )

    async def get_by_id(self, product_id: int) -> dict[str, Any] | None:
        """Get product by ID with company information."""
        return await self.driver.select_one_or_none(
            """
            SELECT
                p.id,
                p.name,
                p.current_price,
                p.description,
                p.embedding,
                p.embedding_generated_on,
                p.created_at,
                p.updated_at,
                p.company_id,
                c.name as company_name
            FROM product p
            JOIN company c ON p.company_id = c.id
            WHERE p.id = :id
            """,
            id=product_id,
        )

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get product by name."""
        return await self.driver.select_one_or_none(
            """
            SELECT
                p.id,
                p.name,
                p.current_price,
                p.description,
                p.embedding,
                p.embedding_generated_on,
                p.created_at,
                p.updated_at,
                p.company_id,
                c.name as company_name
            FROM product p
            JOIN company c ON p.company_id = c.id
            WHERE p.name = :name
            """,
            name=name,
        )

    async def search_by_description(self, search_term: str) -> list[dict[str, Any]]:
        """Search products by description."""
        return await self.driver.select(
            """
            SELECT
                p.id,
                p.name,
                p.current_price,
                p.description,
                p.embedding,
                p.embedding_generated_on,
                p.created_at,
                p.updated_at,
                p.company_id,
                c.name as company_name
            FROM product p
            JOIN company c ON p.company_id = c.id
            WHERE UPPER(p.description) LIKE UPPER(:search_term)
            ORDER BY p.name
            """,
            search_term=f"%{search_term}%",
        )

    async def get_products_without_embeddings(
        self, limit: int = 100, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Get products that have null embeddings with pagination."""
        # Get total count
        count_result = await self.driver.select_one_or_none(
            """
            SELECT COUNT(*) as total_count
            FROM product
            WHERE embedding IS NULL
            """
        )
        total_count = count_result["total_count"] if count_result else 0

        # Get paginated results
        products = await self.driver.select(
            """
            SELECT
                p.id,
                p.name,
                p.current_price,
                p.description,
                p.embedding,
                p.embedding_generated_on,
                p.created_at,
                p.updated_at,
                p.company_id,
                c.name as company_name
            FROM product p
            JOIN company c ON p.company_id = c.id
            WHERE p.embedding IS NULL
            ORDER BY p.id
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """,
            limit=limit,
            offset=offset,
        )

        return products, total_count

    async def search_by_vector(
        self, query_embedding: list[float], limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[dict[str, Any]]:
        """Search products by vector similarity using Oracle 23AI.

        SQLSpec automatically handles vector conversions - no need for array.array().
        """
        # Oracle 23AI vector similarity search
        results = await self.driver.select(
            """
            SELECT
                p.id,
                p.name,
                p.current_price,
                p.description,
                p.embedding,
                p.embedding_generated_on,
                p.created_at,
                p.updated_at,
                p.company_id,
                c.name as company_name,
                VECTOR_DISTANCE(p.embedding, :query_embedding, COSINE) as similarity_score
            FROM product p
            JOIN company c ON p.company_id = c.id
            WHERE p.embedding IS NOT NULL
            AND VECTOR_DISTANCE(p.embedding, :query_embedding, COSINE) <= :threshold
            ORDER BY similarity_score
            FETCH FIRST :limit ROWS ONLY
            """,
            query_embedding=query_embedding,
            threshold=1 - similarity_threshold,  # Convert similarity to distance
            limit=limit,
        )

        # Convert distance back to similarity score
        for result in results:
            result["similarity_score"] = 1 - result["similarity_score"]

        return results

    async def update_embedding(self, product_id: int, embedding: list[float]) -> bool:
        """Update product embedding.

        SQLSpec automatically handles vector conversions - no need for array.array().
        """
        rowcount = await self.driver.execute(
            """
            UPDATE product
            SET embedding = :embedding,
                embedding_generated_on = SYSTIMESTAMP
            WHERE id = :id
            """,
            id=product_id,
            embedding=embedding,
        )

        return rowcount > 0

    async def create_product(
        self,
        name: str,
        company_id: int,
        current_price: float,
        size: str,
        description: str,
        embedding: list[float] | None = None,
    ) -> dict[str, Any] | None:
        """Create a new product."""
        # Insert and get the generated ID
        result = await self.driver.select_one_or_none(
            """
            INSERT INTO product (
                company_id, name, current_price, description, embedding, embedding_generated_on
            ) VALUES (
                :company_id, :name, :current_price, :description, :embedding,
                CASE WHEN :embedding IS NOT NULL THEN SYSTIMESTAMP ELSE NULL END
            )
            RETURNING id
            """,
            company_id=company_id,
            name=name,
            current_price=current_price,
            description=description,
            embedding=embedding,
        )

        if result:
            product_id = result["id"]
            # Return the created product
            return await self.get_by_id(product_id)

        return None

    async def update_product(self, product_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a product."""
        # Build UPDATE statement with safe field mapping
        field_mapping = {
            "name": "name = :name",
            "current_price": "current_price = :current_price",
            "description": "description = :description",
        }

        set_clauses = []
        params: dict[str, Any] = {"id": product_id}

        for field, value in updates.items():
            if field in field_mapping:
                set_clauses.append(field_mapping[field])
                params[field] = value

        if not set_clauses:
            return await self.get_by_id(product_id)

        sql = f"UPDATE product SET {', '.join(set_clauses)} WHERE id = :id"  # noqa: S608

        rowcount = await self.driver.execute(sql, **params)

        if rowcount > 0:
            return await self.get_by_id(product_id)
        return None

    async def delete_product(self, product_id: int) -> bool:
        """Delete a product."""
        rowcount = await self.driver.execute(
            "DELETE FROM product WHERE id = :id",
            id=product_id,
        )
        return rowcount > 0
