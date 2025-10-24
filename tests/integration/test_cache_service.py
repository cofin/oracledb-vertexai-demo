"""Integration tests for CacheService with SQLSpec."""


import pytest

from app.services.cache import CacheService

pytestmark = pytest.mark.anyio


class TestCacheService:
    """Test suite for CacheService using SQLSpec and Oracle VECTOR type."""

    async def test_cache_miss_then_hit(
        self,
        cache_service: CacheService,
    ) -> None:
        """Test cache miss followed by cache hit."""
        query = "test query for caching"
        model_name = "test-model"
        test_embedding = [0.1] * 768

        # First call - should be cache miss
        cached_item = await cache_service.get_cached_embedding(query, model_name)
        assert cached_item is None, "First call should be cache miss"

        # Store in cache
        await cache_service.set_cached_embedding(query, test_embedding, model_name)

        # Second call - should be cache hit
        cached_item = await cache_service.get_cached_embedding(query, model_name)
        assert cached_item is not None, "Second call should be cache hit"
        # Use pytest.approx for float32 precision tolerance
        assert cached_item.embedding == pytest.approx(test_embedding, rel=1e-6)

    async def test_oracle_cache_persistence(
        self,
        cache_service: CacheService,
    ) -> None:
        """Test that embeddings persist in Oracle cache across instances."""
        query = "oracle persistence test"
        model_name = "test-model"
        test_embedding = [0.2] * 768

        # Store in cache and commit
        await cache_service.set_cached_embedding(query, test_embedding, model_name)
        await cache_service.commit()

        # Create new cache instance (simulates new session)
        from app.config import db, db_manager

        async with db_manager.provide_session(db) as session:
            new_cache = CacheService(session)

            # Should hit Oracle cache
            cached_item = await new_cache.get_cached_embedding(query, model_name)
            assert cached_item is not None, "Should hit Oracle cache on new instance"
            assert cached_item.embedding == pytest.approx(test_embedding, rel=1e-6)

    async def test_vector_type_automatic_conversion(
        self,
        cache_service: CacheService,
    ) -> None:
        """Test that SQLSpec automatically handles Oracle VECTOR type conversion."""
        query = "vector conversion test"
        model_name = "test-model"
        test_embedding = [float(i) / 768 for i in range(768)]  # Unique values

        # Store embedding - SQLSpec should handle list -> VECTOR conversion
        await cache_service.set_cached_embedding(query, test_embedding, model_name)

        # Verify we get back a list (VECTOR -> list conversion)
        cached_item = await cache_service.get_cached_embedding(query, model_name)
        assert cached_item is not None
        embedding = cached_item.embedding
        assert isinstance(embedding, list)
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)
        assert embedding == pytest.approx(test_embedding, rel=1e-6)

    async def test_cache_normalization_in_service(
        self,
        cache_service: CacheService,
    ) -> None:
        """Test that queries are normalized for consistent caching."""
        # In the new design, normalization is not part of the cache service.
        # The service that calls the cache is responsible for normalization.
        # This test is to document that the CacheService itself does not normalize.
        query1 = "Test Query"
        query2 = "test query"
        model_name = "test-model"
        test_embedding = [0.3] * 768

        # Store with one version of the query
        await cache_service.set_cached_embedding(query1, test_embedding, model_name)

        # Try to get with another version
        cached_item = await cache_service.get_cached_embedding(query2, model_name)
        assert cached_item is None, "CacheService should not normalize keys"

    async def test_merge_upsert_pattern(
        self,
        cache_service: CacheService,
    ) -> None:
        """Test that MERGE statement properly upserts cache entries."""
        query = "merge test"
        model_name = "test-model"
        embedding1 = [0.5] * 768
        embedding2 = [0.6] * 768

        # First insert
        await cache_service.set_cached_embedding(query, embedding1, model_name)
        cached1 = await cache_service.get_cached_embedding(query, model_name)
        assert cached1 is not None
        assert cached1.embedding == pytest.approx(embedding1, rel=1e-6)
        assert cached1.hit_count == 1

        # Second insert of the same key should update
        await cache_service.set_cached_embedding(query, embedding2, model_name)
        cached2 = await cache_service.get_cached_embedding(query, model_name)
        assert cached2 is not None
        assert cached2.embedding == pytest.approx(embedding2, rel=1e-6)
        assert cached2.hit_count == 2 # hit count is updated on get
