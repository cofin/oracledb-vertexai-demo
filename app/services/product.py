"""Product service using raw Oracle SQL."""

from __future__ import annotations

import array
from typing import Any

from app.services.base import BaseService


class ProductService(BaseService):
    """Handles database operations for products using raw SQL."""

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all products with company information."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """SELECT p.id, p.name, p.current_price, p.description, p.embedding, p.embedding_generated_on, p.created_at, p.updated_at, p.company_id, c.name as company_name FROM product p JOIN company c ON p.company_id = c.id ORDER BY p.name"""
            )

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "current_price": row[2],
                    "description": row[3],
                    "embedding": list(row[4]) if row[4] else None,
                    "embedding_generated_on": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "company_id": row[8],
                    "company_name": row[9],
                }
                async for row in cursor
            ]

    async def get_by_id(self, product_id: int) -> dict[str, Any] | None:
        """Get product by ID with company information."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
                """SELECT p.id, p.name, p.current_price, p.description, p.embedding, p.embedding_generated_on, p.created_at, p.updated_at, p.company_id, c.name as company_name FROM product p JOIN company c ON p.company_id = c.id WHERE p.id = :id""",
                {"id": product_id},
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "current_price": row[2],
                    "description": row[3],
                    "embedding": list(row[4]) if row[4] else None,
                    "embedding_generated_on": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "company_id": row[8],
                    "company_name": row[9],
                }
            return None

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get product by name."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
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
                {"name": name},
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "current_price": row[2],
                    "description": row[3],
                    "embedding": list(row[4]) if row[4] else None,
                    "embedding_generated_on": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "company_id": row[8],
                    "company_name": row[9],
                }
            return None

    async def search_by_description(self, search_term: str) -> list[dict[str, Any]]:
        """Search products by description."""
        async with self.get_cursor() as cursor:
            await cursor.execute(
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
                {"search_term": f"%{search_term}%"},
            )

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "current_price": row[2],
                    "description": row[3],
                    "embedding": list(row[4]) if row[4] else None,
                    "embedding_generated_on": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "company_id": row[8],
                    "company_name": row[9],
                }
                async for row in cursor
            ]

    async def get_products_without_embeddings(
        self, limit: int = 100, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Get products that have null embeddings with pagination."""
        async with self.get_cursor() as cursor:
            # Get total count
            await cursor.execute("""
                SELECT COUNT(*) FROM product WHERE embedding IS NULL
            """)
            total_count = (await cursor.fetchone())[0]

            # Get paginated results
            await cursor.execute(
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
                {"limit": limit, "offset": offset},
            )

            products = [
                {
                    "id": row[0],
                    "name": row[1],
                    "current_price": row[2],
                    "description": row[4],
                    "embedding": None,
                    "embedding_generated_on": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                    "company_id": row[9],
                    "company_name": row[10],
                }
                async for row in cursor
            ]

            return products, total_count

    async def search_by_vector(
        self, query_embedding: list[float], limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[dict[str, Any]]:
        """Search products by vector similarity using Oracle 23AI."""
        async with self.get_cursor() as cursor:
            # Convert Python list to Oracle VECTOR format
            oracle_vector = array.array("f", query_embedding)

            # Oracle 23AI vector similarity search
            await cursor.execute(
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
                {
                    "query_embedding": oracle_vector,
                    "threshold": 1 - similarity_threshold,  # Convert similarity to distance
                    "limit": limit,
                },
            )

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "current_price": row[2],
                    "description": row[4],
                    "embedding": list(row[5]) if row[5] else None,
                    "embedding_generated_on": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                    "company_id": row[9],
                    "company_name": row[10],
                    "similarity_score": 1 - row[11],  # Convert distance back to similarity
                }
                async for row in cursor
            ]

    async def update_embedding(self, product_id: int, embedding: list[float]) -> bool:
        """Update product embedding."""
        async with self.get_cursor() as cursor:
            # Convert Python list to Oracle VECTOR format
            oracle_vector = array.array("f", embedding)

            await cursor.execute(
                """
                UPDATE product
                SET embedding = :embedding,
                    embedding_generated_on = SYSTIMESTAMP
                WHERE id = :id
            """,
                {"id": product_id, "embedding": oracle_vector},
            )

            await self.connection.commit()
            return cursor.rowcount > 0

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
        async with self.get_cursor() as cursor:
            # Convert Python list to Oracle VECTOR format if provided
            oracle_vector = array.array("f", embedding) if embedding else None

            await cursor.execute(
                """
                INSERT INTO product (
                    company_id, name, current_price, description, embedding, embedding_generated_on
                ) VALUES (
                    :company_id, :name, :current_price, :description, :embedding,
                    CASE WHEN :embedding2 IS NOT NULL THEN SYSTIMESTAMP ELSE NULL END
                )
                RETURNING id INTO :id
            """,
                {
                    "company_id": company_id,
                    "name": name,
                    "current_price": current_price,
                    "description": description,
                    "embedding": oracle_vector,
                    "embedding2": oracle_vector,
                    "id": cursor.var(int),
                },
            )

            product_id = cursor.bindvars["id"].getvalue()  # type: ignore[call-overload]
            await self.connection.commit()

            # Return the created product
            return await self.get_by_id(product_id)

    async def update_product(self, product_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a product."""
        async with self.get_cursor() as cursor:
            # Build UPDATE statement with safe field mapping
            field_mapping = {
                "name": "name = :name",
                "current_price": "current_price = :current_price",
                "description": "description = :description",
            }

            set_clauses = []
            params = {"id": product_id}

            for field, value in updates.items():
                if field in field_mapping:
                    set_clauses.append(field_mapping[field])
                    params[field] = value

            if not set_clauses:
                return await self.get_by_id(product_id)

            sql = f"UPDATE product SET {', '.join(set_clauses)} WHERE id = :id"  # noqa: S608

            await cursor.execute(sql, params)
            await self.connection.commit()

            if cursor.rowcount > 0:
                return await self.get_by_id(product_id)
            return None

    async def delete_product(self, product_id: int) -> bool:
        """Delete a product."""
        async with self.get_cursor() as cursor:
            await cursor.execute("DELETE FROM product WHERE id = :id", {"id": product_id})
            await self.connection.commit()
            return cursor.rowcount > 0
