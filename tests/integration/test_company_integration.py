"""Integration tests for Company service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.company import CompanyService


@pytest.mark.anyio
class TestCompanyService:
    """Integration tests for CompanyService."""

    @pytest.mark.asyncio
    async def test_create_company(self, session: AsyncSession) -> None:
        """Test creating a company."""
        service = CompanyService(session=session)

        company_data = {"name": "Test Coffee Co."}
        company = await service.create(data=company_data)

        assert company.name == "Test Coffee Co."
        assert company.id is not None

    @pytest.mark.asyncio
    async def test_get_company_by_name(self, session: AsyncSession) -> None:
        """Test getting company by name."""
        service = CompanyService(session=session)

        # Create a company first
        company_data = {"name": "Another Coffee Co."}
        created_company = await service.create(data=company_data)

        # Retrieve by name
        found_company = await service.get_by_name("Another Coffee Co.")

        assert found_company is not None
        assert found_company.id == created_company.id
        assert found_company.name == "Another Coffee Co."

    @pytest.mark.asyncio
    async def test_company_exists_by_name(self, session: AsyncSession) -> None:
        """Test checking if company exists by name."""
        service = CompanyService(session=session)

        # Check non-existent company
        exists = await service.exists_by_name("Non-existent Company")
        assert not exists

        # Create a company
        company_data = {"name": "Existing Coffee Co."}
        await service.create(data=company_data)

        # Check existing company
        exists = await service.exists_by_name("Existing Coffee Co.")
        assert exists

    @pytest.mark.asyncio
    async def test_list_companies(self, session: AsyncSession) -> None:
        """Test listing companies."""
        service = CompanyService(session=session)

        # Create multiple companies
        companies_data = [
            {"name": "Company A"},
            {"name": "Company B"},
            {"name": "Company C"},
        ]

        for company_data in companies_data:
            await service.create(data=company_data)

        # List all companies
        companies = await service.list()

        min_expected_companies = 3
        assert len(companies) >= min_expected_companies
        company_names = [company.name for company in companies]
        assert "Company A" in company_names
        assert "Company B" in company_names
        assert "Company C" in company_names
