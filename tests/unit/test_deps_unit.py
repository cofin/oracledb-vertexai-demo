"""Unit tests for dependency providers."""

import pytest

from app.domain.coffee import deps


@pytest.mark.anyio
class TestDependencyProviders:
    """Unit tests for service providers."""

    def test_provide_company_service_exists(self) -> None:
        """Test that company service provider exists."""
        assert hasattr(deps, 'provide_company_service')
        assert callable(deps.provide_company_service)

    def test_provide_product_service_exists(self) -> None:
        """Test that product service provider exists."""
        assert hasattr(deps, 'provide_product_service')
        assert callable(deps.provide_product_service)

    def test_provide_shop_service_exists(self) -> None:
        """Test that shop service provider exists."""
        assert hasattr(deps, 'provide_shop_service')
        assert callable(deps.provide_shop_service)

    def test_provide_user_session_service_exists(self) -> None:
        """Test that user session service provider exists."""
        assert hasattr(deps, 'provide_user_session_service')
        assert callable(deps.provide_user_session_service)

    def test_provide_recommendation_service_exists(self) -> None:
        """Test that recommendation service provider exists."""
        assert hasattr(deps, 'provide_recommendation_service')
        assert callable(deps.provide_recommendation_service)