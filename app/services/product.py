"""Product service with both SQLAlchemy and raw SQL implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from advanced_alchemy.filters import LimitOffset
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from app.db import models as m

if TYPE_CHECKING:
    from collections.abc import Sequence

    import oracledb


class ProductService(SQLAlchemyAsyncRepositoryService[m.Product]):
    """Handles database operations for products using SQLAlchemy."""

    class Repo(SQLAlchemyAsyncRepository[m.Product]):
        """Product repository."""

        model_type = m.Product

    repository_type = Repo
    match_fields = ["name"]

    async def get_by_name(self, name: str) -> m.Product | None:
        """Get product by name."""
        return await self.get_one_or_none(name=name)

    async def get_with_embeddings(self, product_id: int) -> m.Product | None:
        """Get product with embeddings loaded."""
        return await self.get_one_or_none(m.Product.id == product_id)

    async def search_by_description(self, search_term: str) -> Sequence[m.Product]:
        """Search products by description."""
        return await self.list(m.Product.description.ilike(f"%{search_term}%"))

    async def get_products_without_embeddings(
        self, limit: int = 100, offset: int = 0
    ) -> tuple[Sequence[m.Product], int]:
        """Get products that have null embeddings with pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            Tuple of (products, total_count)
        """
        limit_offset = LimitOffset(limit=limit, offset=offset)
        return await self.list_and_count(m.Product.embedding.is_(None), limit_offset)


class RawProductService:
    """Handles database operations for products using raw SQL."""

    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        """Initialize with Oracle connection."""
        self.connection = connection

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all products with company information."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute("""
                SELECT
                    p.id,
                    p.name,
                    p.current_price,
                    p."SIZE" as size,
                    p.description,
                    p.embedding,
                    p.embedding_generated_on,
                    p.created_at,
                    p.updated_at,
                    p.company_id,
                    c.name as company_name
                FROM product p
                INNER JOIN company c ON p.company_id = c.id
                ORDER BY p.name
            """)

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
                    "company_id": row[9],
                    "company_name": row[10],
                }
                async for row in cursor
            ]

        finally:
            cursor.close()
        return products

    async def get_by_id(self, product_id: int) -> dict[str, Any] | None:
        """Get product by ID with company information."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.current_price,
                    p."SIZE" as size,
                    p.description,
                    p.embedding,
                    p.embedding_generated_on,
                    p.created_at,
                    p.updated_at,
                    p.company_id,
                    c.name as company_name
                FROM product p
                INNER JOIN company c ON p.company_id = c.id
                WHERE p.id = :id
            """,
                {"id": product_id},
            )

            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "current_price": row[2],
                    "size": row[3],
                    "description": row[4],
                    "embedding": list(row[5]) if row[5] else None,
                    "embedding_generated_on": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                    "company_id": row[9],
                    "company_name": row[10],
                }
            return None
        finally:
            cursor.close()

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get product by name."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.current_price,
                    p."SIZE" as size,
                    p.description,
                    p.embedding,
                    p.embedding_generated_on,
                    p.created_at,
                    p.updated_at,
                    p.company_id,
                    c.name as company_name
                FROM product p
                INNER JOIN company c ON p.company_id = c.id
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
                    "size": row[3],
                    "description": row[4],
                    "embedding": list(row[5]) if row[5] else None,
                    "embedding_generated_on": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                    "company_id": row[9],
                    "company_name": row[10],
                }
            return None
        finally:
            cursor.close()

    async def search_by_description(self, search_term: str) -> list[dict[str, Any]]:
        """Search products by description."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.current_price,
                    p."SIZE" as size,
                    p.description,
                    p.embedding,
                    p.embedding_generated_on,
                    p.created_at,
                    p.updated_at,
                    p.company_id,
                    c.name as company_name
                FROM product p
                INNER JOIN company c ON p.company_id = c.id
                WHERE UPPER(p.description) LIKE UPPER(:search_term)
                ORDER BY p.name
            """,
                {"search_term": f"%{search_term}%"},
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
                    "company_id": row[9],
                    "company_name": row[10],
                }
                async for row in cursor
            ]
        finally:
            cursor.close()
        return products

    async def get_products_without_embeddings(
        self, limit: int = 100, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Get products that have null embeddings with pagination."""
        cursor = self.connection.cursor()
        try:
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
                    p."SIZE" as size,
                    p.description,
                    p.embedding,
                    p.embedding_generated_on,
                    p.created_at,
                    p.updated_at,
                    p.company_id,
                    c.name as company_name
                FROM product p
                INNER JOIN company c ON p.company_id = c.id
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
                    "size": row[3],
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
        finally:
            cursor.close()

    async def search_by_vector(
        self, query_embedding: list[float], limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[dict[str, Any]]:
        """Search products by vector similarity using Oracle 23AI."""
        cursor = self.connection.cursor()
        try:
            # Oracle 23AI vector similarity search
            await cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.current_price,
                    p."SIZE" as size,
                    p.description,
                    p.embedding,
                    p.embedding_generated_on,
                    p.created_at,
                    p.updated_at,
                    p.company_id,
                    c.name as company_name,
                    VECTOR_DISTANCE(p.embedding, :query_embedding, COSINE) as similarity_score
                FROM product p
                INNER JOIN company c ON p.company_id = c.id
                WHERE p.embedding IS NOT NULL
                AND VECTOR_DISTANCE(p.embedding, :query_embedding, COSINE) <= :threshold
                ORDER BY similarity_score
                FETCH FIRST :limit ROWS ONLY
            """,
                {
                    "query_embedding": query_embedding,
                    "threshold": 1 - similarity_threshold,  # Convert similarity to distance
                    "limit": limit,
                },
            )

            return [
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
                    "company_id": row[9],
                    "company_name": row[10],
                    "similarity_score": 1 - row[11],  # Convert distance back to similarity
                }
                async for row in cursor
            ]
        finally:
            cursor.close()

    async def update_embedding(self, product_id: int, embedding: list[float]) -> bool:
        """Update product embedding."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute(
                """
                UPDATE product
                SET embedding = :embedding,
                    embedding_generated_on = SYSTIMESTAMP,
                    updated_at = SYSTIMESTAMP
                WHERE id = :id
            """,
                {"id": product_id, "embedding": embedding},
            )

            await self.connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()

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
        cursor = self.connection.cursor()
        try:
            # Get next ID from sequence
            await cursor.execute("SELECT product_id_seq.NEXTVAL FROM dual")
            product_id = (await cursor.fetchone())[0]

            await cursor.execute(
                """
                INSERT INTO product (
                    id, company_id, name, current_price, "SIZE",
                    description, embedding, embedding_generated_on
                ) VALUES (
                    :id, :company_id, :name, :current_price, :size,
                    :description, :embedding,
                    CASE WHEN :embedding2 IS NOT NULL THEN SYSTIMESTAMP ELSE NULL END
                )
            """,
                {
                    "id": product_id,
                    "company_id": company_id,
                    "name": name,
                    "current_price": current_price,
                    "size": size,
                    "description": description,
                    "embedding": embedding,
                    "embedding2": embedding,
                },
            )

            await self.connection.commit()

            # Return the created product
            return await self.get_by_id(product_id)
        finally:
            cursor.close()

    async def update_product(self, product_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Update a product."""
        cursor = self.connection.cursor()
        try:
            # Build UPDATE statement with safe field mapping
            field_mapping = {
                "name": "name = :name",
                "current_price": "current_price = :current_price",
                "size": '"SIZE" = :size',
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

            set_clauses.append("updated_at = SYSTIMESTAMP")
            sql = f"UPDATE product SET {', '.join(set_clauses)} WHERE id = :id"  # noqa: S608

            await cursor.execute(sql, params)
            await self.connection.commit()

            if cursor.rowcount > 0:
                return await self.get_by_id(product_id)
            return None
        finally:
            cursor.close()

    async def delete_product(self, product_id: int) -> bool:
        """Delete a product."""
        cursor = self.connection.cursor()
        try:
            await cursor.execute("DELETE FROM product WHERE id = :id", {"id": product_id})
            await self.connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
