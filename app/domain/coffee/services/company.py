"""Company service with Advanced Alchemy patterns."""

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

from app.db import models as m


class CompanyService(SQLAlchemyAsyncRepositoryService[m.Company]):
    """Handles database operations for companies."""

    class Repo(SQLAlchemyAsyncRepository[m.Company]):
        """Company repository."""

        model_type = m.Company

    repository_type = Repo
    match_fields = ["name"]

    async def get_by_name(self, name: str) -> m.Company | None:
        """Get company by name."""
        return await self.get_one_or_none(name=name)

    async def exists_by_name(self, name: str) -> bool:
        """Check if company exists by name."""
        return await self.exists(name=name)
