# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Test fixtures for integration tests."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest

from app.config import db
from app.domain.products.services import ProductService


@pytest.fixture
async def driver() -> AsyncGenerator[Any, None]:
    """Provide SQLSpec driver for tests."""
    from app.config import db_manager

    async with db_manager.provide_session(db) as session:
        yield session


@pytest.fixture
def product_service(driver: Any) -> ProductService:
    """Provide ProductService for testing."""
    return ProductService(driver)
