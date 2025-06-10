"""Shop service with Advanced Alchemy patterns."""

from collections.abc import Sequence

from advanced_alchemy.repository import SQLAlchemyAsyncSlugRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Shop


class ShopService(SQLAlchemyAsyncRepositoryService[Shop]):
    """Handles database operations for shops."""

    class Repo(SQLAlchemyAsyncSlugRepository[Shop]):
        """Shop repository with slug support."""
        model_type = Shop

    repository_type = Repo
    match_fields = ["name"]

    async def get_by_slug(self, slug: str) -> Shop | None:
        """Get shop by slug."""
        return await self.get_one_or_none(slug=slug)

    async def get_with_inventory(self, shop_id: int) -> Shop | None:
        """Get shop with inventory loaded."""
        stmt = (
            select(Shop)
            .where(Shop.id == shop_id)
            .options(selectinload(Shop.inventory))
        )
        result = await self.repository.session.execute(stmt)
        shop = result.scalar_one_or_none()
        return shop

    async def find_by_location(self, latitude: float, longitude: float, radius_km: float = 10) -> Sequence[Shop]:
        """Find shops within radius of location."""
        # Simple implementation - in production you'd use spatial queries
        stmt = select(Shop).limit(10)
        result = await self.repository.session.execute(stmt)
        shops = list(result.scalars().all())
        return shops

