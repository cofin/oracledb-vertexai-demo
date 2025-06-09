"""Product service with Advanced Alchemy patterns."""

from collections.abc import Sequence

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import select

from app.db.models import Product


class ProductService(SQLAlchemyAsyncRepositoryService[Product]):
    """Handles database operations for products."""

    class Repo(SQLAlchemyAsyncRepository[Product]):
        """Product repository."""
        model_type = Product

    repository_type = Repo
    match_fields = ["name"]

    async def get_by_name(self, name: str) -> Product | None:
        """Get product by name."""
        return await self.get_one_or_none(name=name)

    async def get_with_embeddings(self, product_id: int) -> Product | None:
        """Get product with embeddings loaded."""
        stmt = select(Product).where(Product.id == product_id)
        result = await self.repository.session.execute(stmt)
        product = result.scalar_one_or_none()
        return product

    async def search_by_description(self, search_term: str) -> Sequence[Product]:
        """Search products by description."""
        stmt = select(Product).where(
            Product.description.ilike(f"%{search_term}%"),
        ).limit(10)
        result = await self.repository.session.execute(stmt)
        products = list(result.scalars().all())
        return products

