"""Unit tests for Company service."""

from unittest.mock import AsyncMock, patch

import pytest

from app.db.models import Company
from app.services.company import CompanyService


@pytest.mark.anyio
class TestCompanyService:
    """Unit tests for CompanyService."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock session."""
        return AsyncMock()

    @pytest.fixture
    def company_service(self, mock_session: AsyncMock) -> CompanyService:
        """Create CompanyService with mocked session."""
        return CompanyService(session=mock_session)

    @pytest.mark.asyncio
    async def test_get_by_name_success(self, company_service: CompanyService, mock_session: AsyncMock) -> None:
        """Test get_by_name returns company when found."""
        # Arrange
        expected_company = Company(id=1, name="Test Company")

        with patch.object(company_service, "get_one_or_none", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = expected_company

            # Act
            result = await company_service.get_by_name("Test Company")

            # Assert
            assert result == expected_company
            mock_get.assert_called_once_with(name="Test Company")

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, company_service: CompanyService, mock_session: AsyncMock) -> None:
        """Test get_by_name returns None when not found."""
        with patch.object(company_service, "get_one_or_none", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Act
            result = await company_service.get_by_name("Non-existent Company")

            # Assert
            assert result is None
            mock_get.assert_called_once_with(name="Non-existent Company")

    @pytest.mark.asyncio
    async def test_exists_by_name_true(self, company_service: CompanyService, mock_session: AsyncMock) -> None:
        """Test exists_by_name returns True when company exists."""
        with patch.object(company_service, "exists", new_callable=AsyncMock) as mock_exists:
            mock_exists.return_value = True

            # Act
            result = await company_service.exists_by_name("Existing Company")

            # Assert
            assert result is True
            mock_exists.assert_called_once_with(name="Existing Company")

    @pytest.mark.asyncio
    async def test_exists_by_name_false(self, company_service: CompanyService, mock_session: AsyncMock) -> None:
        """Test exists_by_name returns False when company doesn't exist."""
        with patch.object(company_service, "exists", new_callable=AsyncMock) as mock_exists:
            mock_exists.return_value = False

            # Act
            result = await company_service.exists_by_name("Non-existent Company")

            # Assert
            assert result is False
            mock_exists.assert_called_once_with(name="Non-existent Company")
