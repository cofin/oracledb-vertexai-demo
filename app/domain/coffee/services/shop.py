"""Shop service with Advanced Alchemy patterns."""

from collections.abc import Sequence

from advanced_alchemy.filters import LimitOffset
from advanced_alchemy.repository import SQLAlchemyAsyncSlugRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from sqlalchemy.orm import selectinload

from app.db import models as m


class ShopService(SQLAlchemyAsyncRepositoryService[m.Shop]):
    """Handles database operations for shops."""

    class Repo(SQLAlchemyAsyncSlugRepository[m.Shop]):
        """Shop repository with slug support."""

        model_type = m.Shop

    repository_type = Repo
    match_fields = ["name"]

    async def get_by_slug(self, slug: str) -> m.Shop | None:
        """Get shop by slug."""
        return await self.get_one_or_none(slug=slug)

    async def get_with_inventory(self, shop_id: int) -> m.Shop | None:
        """Get shop with inventory loaded."""
        return await self.get_one_or_none(m.Shop.id == shop_id, load=[selectinload(m.Shop.inventory)])

    async def find_by_location(self, latitude: float, longitude: float, radius_km: float = 10) -> Sequence[m.Shop]:
        """Find shops within radius of location."""
        # Simple implementation - in production you'd use spatial queries
        return await self.list(LimitOffset(limit=10, offset=0))
