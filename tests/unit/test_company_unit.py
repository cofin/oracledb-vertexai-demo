"""Unit tests for Company service."""

from unittest.mock import AsyncMock

import pytest

from app.db.models import Company
from app.domain.coffee.services.company import CompanyService


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
    async def test_get_by_name_success(
        self,
        company_service: CompanyService,
        mock_session: AsyncMock
    ) -> None:
        """Test get_by_name returns company when found."""
        # Arrange
        expected_company = Company(id=1, name="Test Company")
        company_service.get_one_or_none = AsyncMock(return_value=expected_company)

        # Act
        result = await company_service.get_by_name("Test Company")

        # Assert
        assert result == expected_company
        company_service.get_one_or_none.assert_called_once_with(name="Test Company")

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(
        self,
        company_service: CompanyService,
        mock_session: AsyncMock
    ) -> None:
        """Test get_by_name returns None when not found."""
        # Arrange
        company_service.get_one_or_none = AsyncMock(return_value=None)

        # Act
        result = await company_service.get_by_name("Non-existent Company")

        # Assert
        assert result is None
        company_service.get_one_or_none.assert_called_once_with(name="Non-existent Company")

    @pytest.mark.asyncio
    async def test_exists_by_name_true(
        self,
        company_service: CompanyService,
        mock_session: AsyncMock
    ) -> None:
        """Test exists_by_name returns True when company exists."""
        # Arrange
        company_service.exists = AsyncMock(return_value=True)

        # Act
        result = await company_service.exists_by_name("Existing Company")

        # Assert
        assert result is True
        company_service.exists.assert_called_once_with(name="Existing Company")

    @pytest.mark.asyncio
    async def test_exists_by_name_false(
        self,
        company_service: CompanyService,
        mock_session: AsyncMock
    ) -> None:
        """Test exists_by_name returns False when company doesn't exist."""
        # Arrange
        company_service.exists = AsyncMock(return_value=False)

        # Act
        result = await company_service.exists_by_name("Non-existent Company")

        # Assert
        assert result is False
        company_service.exists.assert_called_once_with(name="Non-existent Company")
