from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.db.repositories.product import ProductRepository
    from app.schemas import ProductDTO


class ProductService:
    """Handles database operations for products using a repository."""

    def __init__(self, product_repository: ProductRepository) -> None:
        """Initialize with product repository."""
        self.repository = product_repository

    async def get_all(self) -> list[ProductDTO]:
        """Get all products with company information."""
        return await self.repository.get_all()

    async def get_by_id(self, product_id: int) -> ProductDTO | None:
        """Get product by ID with company information."""
        return await self.repository.get_by_id(product_id)

    async def get_by_name(self, name: str) -> ProductDTO | None:
        """Get product by name."""
        return await self.repository.get_by_name(name)

    async def search_by_description(self, search_term: str) -> list[ProductDTO]:
        """Search products by description."""
        return await self.repository.search_by_description(search_term)

    async def get_products_without_embeddings(
        self, limit: int = 100, offset: int = 0
    ) -> tuple[list[ProductDTO], int]:
        """Get products that have null embeddings with pagination."""
        return await self.repository.get_products_without_embeddings(limit, offset)

    async def search_by_vector(
        self, query_embedding: list[float], limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[ProductDTO]:
        """Search products by vector similarity using Oracle 23AI."""
        return await self.repository.search_by_vector(query_embedding, limit, similarity_threshold)

    async def search_by_vector_with_timing(
        self, embedding: list[float], limit: int = 5
    ) -> tuple[list[dict], dict[str, float]]:
        """Search products by vector with timing information for demo purposes."""
        results, oracle_time = await self.repository.vector_search_with_distance(embedding, limit)
        timings = {"oracle_ms": oracle_time}
        return results, timings

    async def update_embedding(self, product_id: int, embedding: list[float]) -> bool:
        """Update product embedding."""
        return await self.repository.update_embedding(product_id, embedding)

    async def create_product(
        self,
        name: str,
        company_id: int,
        current_price: float,
        size: str,
        description: str,
        embedding: list[float] | None = None,
    ) -> ProductDTO | None:
        """Create a new product."""
        return await self.repository.create_product(
            name, company_id, current_price, size, description, embedding
        )

    async def update_product(self, product_id: int, updates: dict[str, Any]) -> ProductDTO | None:
        """Update a product."""
        return await self.repository.update_product(product_id, updates)

    async def delete_product(self, product_id: int) -> bool:
        """Delete a product."""
        return await self.repository.delete_product(product_id)
