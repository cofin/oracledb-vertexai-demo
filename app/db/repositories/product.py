from app.schemas import ProductDTO
from .base import BaseRepository

class ProductRepository(BaseRepository[ProductDTO]):
    def __init__(self, connection):
        super().__init__(connection, ProductDTO)

    async def get_by_id(self, product_id: int) -> ProductDTO | None:
        query = "SELECT id, name, description, price FROM product WHERE id = :id"
        return await self.fetch_one(query, {"id": product_id})

    async def vector_search(self, embedding: list[float], limit: int = 5) -> list[ProductDTO]:
        query = """
            SELECT id, name, description, price
            FROM product
            WHERE VECTOR_DISTANCE(embedding, :embedding, COSINE) < 0.8
            ORDER BY VECTOR_DISTANCE(embedding, :embedding, COSINE)
            FETCH FIRST :limit ROWS ONLY
        """
        return await self.fetch_all(query, {"embedding": embedding, "limit": limit})
