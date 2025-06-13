"""Integration tests for Company service."""

import pytest

from app.services.company import CompanyService


@pytest.mark.anyio
class TestCompanyService:
    """Integration tests for CompanyService."""

    @pytest.mark.asyncio
    async def test_create_company(self, oracle_connection) -> None:
        """Test creating a company."""
        service = CompanyService(oracle_connection)

        company = await service.create_company("Test New Company")

        assert company is not None
        assert company["name"] == "Test New Company"
        assert company["id"] is not None

    @pytest.mark.asyncio
    async def test_get_company_by_name(self, oracle_connection) -> None:
        """Test getting company by name."""
        service = CompanyService(oracle_connection)

        # Create a company first
        created_company = await service.create_company("Another Coffee Co.")

        # Retrieve by name
        found_company = await service.get_by_name("Another Coffee Co.")

        assert found_company is not None
        assert found_company["id"] == created_company["id"]
        assert found_company["name"] == "Another Coffee Co."

    @pytest.mark.asyncio
    async def test_company_exists_by_name(self, oracle_connection) -> None:
        """Test checking if company exists by name."""
        service = CompanyService(oracle_connection)

        # Check non-existent company
        exists = await service.exists_by_name("Non-existent Company")
        assert not exists

        # Create a company
        await service.create_company("Existing Coffee Co.")

        # Check existing company
        exists = await service.exists_by_name("Existing Coffee Co.")
        assert exists

    @pytest.mark.asyncio
    async def test_list_companies(self, oracle_connection) -> None:
        """Test listing companies."""
        service = CompanyService(oracle_connection)

        # Create multiple companies
        company_names = ["Company A", "Company B", "Company C"]

        for name in company_names:
            await service.create_company(name)

        # List all companies
        companies = await service.list()

        # Should have at least the test companies we created plus the setup one
        min_expected_companies = 4  # 3 created + 1 from setup
        assert len(companies) >= min_expected_companies
        actual_names = [company["name"] for company in companies]
        for name in company_names:
            assert name in actual_names
