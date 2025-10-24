"""Test fixtures for integration tests."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest

from app.config import db
from app.services.product import ProductService


@pytest.fixture
async def driver() -> AsyncGenerator[Any, None]:
    """Provide SQLSpec driver for tests."""
    driver_instance = await db.async_driver()
    yield driver_instance


@pytest.fixture
def product_service(driver: Any) -> ProductService:
    """Provide ProductService for testing."""
    return ProductService(driver)
