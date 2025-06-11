"""Product service with Advanced Alchemy patterns."""

from collections.abc import Sequence

from advanced_alchemy.filters import LimitOffset
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from app.db import models as m


class ProductService(SQLAlchemyAsyncRepositoryService[m.Product]):
    """Handles database operations for products."""

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
        return await self.list_and_count(
            m.Product.embedding.is_(None),
            limit_offset
        )
