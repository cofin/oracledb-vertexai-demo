"""Test fixtures for integration tests."""

import pytest

from app.config import db
from app.services.embedding_cache import EmbeddingCache
from app.services.intent_router import IntentRouter
from app.services.product import ProductService
from app.services.response_cache import ResponseCacheService


@pytest.fixture
async def driver():
    """Provide SQLSpec driver for tests."""
    return await db.async_driver()


@pytest.fixture
async def product_service(driver):
    """Provide ProductService for testing."""
    return ProductService(driver)


@pytest.fixture
async def embedding_cache(driver):
    """Provide EmbeddingCache for testing."""
    return EmbeddingCache(driver, ttl_hours=24)


@pytest.fixture
async def response_cache(driver):
    """Provide ResponseCacheService for testing."""
    return ResponseCacheService(driver)


@pytest.fixture
async def intent_router(driver):
    """Provide IntentRouter for testing."""
    from unittest.mock import MagicMock

    # Create mock VertexAI service
    mock_vertex = MagicMock()

    # Router with optional cache
    return IntentRouter(driver=driver, vertex_ai_service=mock_vertex)
