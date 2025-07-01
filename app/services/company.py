from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.repositories.company import CompanyRepository
    from app.schemas import CompanyDTO


class CompanyService:
    """Handles database operations for companies using a repository."""

    def __init__(self, company_repository: CompanyRepository):
        """Initialize with company repository."""
        self.repository = company_repository

    async def get_all(self) -> list[CompanyDTO]:
        """Get all companies."""
        return await self.repository.get_all()

    async def get_by_id(self, company_id: int) -> CompanyDTO | None:
        """Get company by ID."""
        return await self.repository.get_by_id(company_id)

    async def get_by_name(self, name: str) -> CompanyDTO | None:
        """Get company by name."""
        return await self.repository.get_by_name(name)

    async def create_company(self, name: str) -> CompanyDTO | None:
        """Create a new company."""
        return await self.repository.create_company(name)

    async def update_company(self, company_id: int, name: str) -> CompanyDTO | None:
        """Update a company."""
        return await self.repository.update_company(company_id, name)

    async def delete_company(self, company_id: int) -> bool:
        """Delete a company."""
        return await self.repository.delete_company(company_id)
