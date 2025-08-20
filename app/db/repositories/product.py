import array
import time
from typing import Any

import oracledb

from app.schemas import ProductDTO

from .base import BaseRepository


class ProductRepository(BaseRepository[ProductDTO]):
    def __init__(self, connection: oracledb.AsyncConnection) -> None:
        super().__init__(connection, ProductDTO)

    async def get_all(self) -> list[ProductDTO]:
        query = "SELECT id, name, description, current_price as price FROM product"
        return await self.fetch_all(query)

    async def get_by_id(self, product_id: int) -> ProductDTO | None:
        query = "SELECT id, name, description, current_price as price FROM product WHERE id = :id"
        return await self.fetch_one(query, {"id": product_id})

    async def get_by_name(self, name: str) -> ProductDTO | None:
        query = "SELECT id, name, description, current_price as price FROM product WHERE name = :name"
        return await self.fetch_one(query, {"name": name})

    async def vector_search(self, embedding: list[float], limit: int = 5) -> list[ProductDTO]:
        query = """
            SELECT id, name, description, current_price as price
            FROM product
            WHERE VECTOR_DISTANCE(embedding, :embedding, COSINE) < 0.8
            ORDER BY VECTOR_DISTANCE(embedding, :embedding, COSINE)
            FETCH FIRST :limit ROWS ONLY
        """
        embedding_array = array.array("f", embedding)
        return await self.fetch_all(query, {"embedding": embedding_array, "limit": limit})

    async def vector_search_with_distance(self, embedding: list[float], limit: int = 5) -> tuple[list[dict[str, Any]], float]:
        """Vector search that returns products with distance scores using Oracle 23AI native operations."""
        oracle_start = time.time()
        query = """
            SELECT id, name, description, current_price as price,
                   VECTOR_DISTANCE(embedding, :embedding, COSINE) as distance
            FROM product
            WHERE VECTOR_DISTANCE(embedding, :embedding, COSINE) < 0.8
            ORDER BY VECTOR_DISTANCE(embedding, :embedding, COSINE)
            FETCH FIRST :limit ROWS ONLY
        """

        async with self.connection.cursor() as cursor:
            embedding_array = array.array("f", embedding)
            await cursor.execute(query, {"embedding": embedding_array, "limit": limit})
            columns = [desc[0].lower() for desc in cursor.description]
            results = []
            async for row in cursor:
                row_dict = dict(zip(columns, row, strict=False))
                results.append(row_dict)

        oracle_time = (time.time() - oracle_start) * 1000
        return results, oracle_time

    async def search_by_description(self, search_term: str) -> list[ProductDTO]:
        """Search products by description."""
        query = """
            SELECT id, name, description, current_price as price
            FROM product
            WHERE LOWER(description) LIKE LOWER(:search_term)
            ORDER BY name
        """
        return await self.fetch_all(query, {"search_term": f"%{search_term}%"})

    async def get_products_without_embeddings(
        self, limit: int = 100, offset: int = 0
    ) -> tuple[list[ProductDTO], int]:
        """Get products that have null embeddings with pagination."""
        # Get total count
        count_query = "SELECT COUNT(*) FROM product WHERE embedding IS NULL"
        async with self.connection.cursor() as cursor:
            await cursor.execute(count_query)
            total_count = (await cursor.fetchone())[0]

        # Get paginated results
        query = """
            SELECT id, name, description, current_price as price
            FROM product
            WHERE embedding IS NULL
            ORDER BY id
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
        """
        products = await self.fetch_all(query, {"limit": limit, "offset": offset})
        return products, total_count

    async def search_by_vector(
        self, query_embedding: list[float], limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[ProductDTO]:
        """Search products by vector similarity using Oracle 23AI native vector operations."""
        query = """
            SELECT id, name, description, current_price as price
            FROM product
            WHERE VECTOR_DISTANCE(embedding, :embedding, COSINE) < :threshold
            ORDER BY VECTOR_DISTANCE(embedding, :embedding, COSINE)
            FETCH FIRST :limit ROWS ONLY
        """
        embedding_array = array.array("f", query_embedding)
        return await self.fetch_all(query, {
            "embedding": embedding_array,
            "limit": limit,
            "threshold": 1 - similarity_threshold  # Convert similarity to distance
        })

    async def update_embedding(self, product_id: int, embedding: list[float]) -> bool:
        """Update product embedding using Oracle 23AI native vector operations."""
        query = "UPDATE product SET embedding = :embedding WHERE id = :id"
        async with self.connection.cursor() as cursor:
            embedding_array = array.array("f", embedding)
            await cursor.execute(query, {"id": product_id, "embedding": embedding_array})
            await self.connection.commit()
            return bool(cursor.rowcount > 0)

    async def create_product(
        self,
        name: str,
        company_id: int,
        current_price: float,
        size: str,
        description: str,
        embedding: list[float] | None = None,
    ) -> ProductDTO | None:
        """Create a new product using Oracle 23AI native vector operations."""
        if embedding:
            query = """
                INSERT INTO product (name, company_id, current_price, size, description, embedding)
                VALUES (:name, :company_id, :current_price, :size, :description, :embedding)
                RETURNING id INTO :id
            """
        else:
            query = """
                INSERT INTO product (name, company_id, current_price, size, description)
                VALUES (:name, :company_id, :current_price, :size, :description)
                RETURNING id INTO :id
            """

        async with self.connection.cursor() as cursor:
            params = {
                "name": name,
                "company_id": company_id,
                "current_price": current_price,
                "size": size,
                "description": description,
                "id": cursor.var(int)
            }
            if embedding:
                params["embedding"] = array.array("f", embedding)

            await cursor.execute(query, params)
            product_id = cursor.bindvars["id"].getvalue()[0][0]
            await self.connection.commit()
            return await self.get_by_id(product_id)

    async def update_product(self, product_id: int, updates: dict[str, Any]) -> ProductDTO | None:
        """Update a product."""
        # Use static SQL generation to avoid SQL injection
        allowed_fields = {"name", "description", "current_price", "size", "company_id"}
        update_fields = [f for f in updates if f in allowed_fields]

        if not update_fields:
            return await self.get_by_id(product_id)

        # Build SQL with parameterized fields
        set_clauses = [f"{field} = :{field}" for field in update_fields]
        sql = f"UPDATE product SET {', '.join(set_clauses)} WHERE id = :id"  # noqa: S608

        # Build params dict
        params = {"id": product_id}
        for field in update_fields:
            params[field] = updates[field]

        async with self.connection.cursor() as cursor:
            await cursor.execute(sql, params)
            await self.connection.commit()
            if cursor.rowcount > 0:
                return await self.get_by_id(product_id)
            return None

    async def delete_product(self, product_id: int) -> bool:
        """Delete a product."""
        query = "DELETE FROM product WHERE id = :id"
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"id": product_id})
            await self.connection.commit()
            return bool(cursor.rowcount > 0)
