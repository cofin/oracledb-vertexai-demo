"""Test fixtures for integration tests."""

import pytest

from app.config import db
from app.services.product import ProductService


@pytest.fixture
async def driver():
    """Provide SQLSpec driver for tests."""
    return await db.async_driver()


@pytest.fixture
async def product_service(driver):
    """Provide ProductService for testing."""
    return ProductService(driver)
