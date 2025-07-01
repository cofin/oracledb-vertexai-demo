from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.repositories.shop import ShopRepository
    from app.schemas import ShopDTO


class ShopService:
    """Handles database operations for shops using a repository."""

    def __init__(self, shop_repository: ShopRepository):
        """Initialize with shop repository."""
        self.repository = shop_repository

    async def get_all(self) -> list[ShopDTO]:
        """Get all shops."""
        return await self.repository.get_all()

    async def get_by_id(self, shop_id: int) -> ShopDTO | None:
        """Get shop by ID."""
        return await self.repository.get_by_id(shop_id)

    async def get_by_name(self, name: str) -> ShopDTO | None:
        """Get shop by name."""
        return await self.repository.get_by_name(name)

    async def create_shop(self, name: str, address: str) -> ShopDTO | None:
        """Create a new shop."""
        return await self.repository.create_shop(name, address)

    async def update_shop(self, shop_id: int, updates: dict[str, any]) -> ShopDTO | None:
        """Update a shop."""
        return await self.repository.update_shop(shop_id, updates)

    async def delete_shop(self, shop_id: int) -> bool:
        """Delete a shop."""
        return await self.repository.delete_shop(shop_id)
