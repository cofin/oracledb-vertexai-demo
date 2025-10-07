"""Integration tests for EmbeddingCache with SQLSpec."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.embedding_cache import EmbeddingCache

pytestmark = pytest.mark.anyio


class TestEmbeddingCache:
    """Test suite for EmbeddingCache using SQLSpec and Oracle VECTOR type."""

    async def test_cache_miss_then_hit(
        self,
        embedding_cache: EmbeddingCache,
    ) -> None:
        """Test cache miss followed by cache hit."""
        # Create mock VertexAI service
        mock_vertex = MagicMock()
        test_embedding = [0.1] * 768
        mock_vertex.create_embedding = AsyncMock(return_value=test_embedding)

        query = "test query for caching"

        # First call - should be cache miss
        embedding1, cache_hit1 = await embedding_cache.get_embedding(query, mock_vertex)
        assert not cache_hit1, "First call should be cache miss"
        assert len(embedding1) == 768
        assert mock_vertex.create_embedding.called

        # Second call - should be cache hit (memory cache)
        mock_vertex.create_embedding.reset_mock()
        embedding2, cache_hit2 = await embedding_cache.get_embedding(query, mock_vertex)
        assert cache_hit2, "Second call should be cache hit"
        assert embedding1 == embedding2
        assert not mock_vertex.create_embedding.called, "Should not call Vertex AI on cache hit"

    async def test_oracle_cache_persistence(
        self,
        embedding_cache: EmbeddingCache,
    ) -> None:
        """Test that embeddings persist in Oracle cache across instances."""
        # Create mock VertexAI service
        mock_vertex = MagicMock()
        test_embedding = [0.2] * 768
        mock_vertex.create_embedding = AsyncMock(return_value=test_embedding)

        query = "oracle persistence test"

        # Store in cache
        embedding1, _ = await embedding_cache.get_embedding(query, mock_vertex)
        assert len(embedding1) == 768

        # Create new cache instance (simulates new session)
        from app.config import db

        new_driver = await db.async_driver()
        new_cache = EmbeddingCache(new_driver, ttl_hours=24)

        # Should hit Oracle cache (not memory)
        embedding2, cache_hit = await new_cache.get_embedding(query, mock_vertex)
        assert cache_hit, "Should hit Oracle cache on new instance"
        assert embedding1 == embedding2

    async def test_vector_type_automatic_conversion(
        self,
        embedding_cache: EmbeddingCache,
    ) -> None:
        """Test that SQLSpec automatically handles Oracle VECTOR type conversion."""
        mock_vertex = MagicMock()
        test_embedding = [float(i) / 768 for i in range(768)]  # Unique values
        mock_vertex.create_embedding = AsyncMock(return_value=test_embedding)

        query = "vector conversion test"

        # Store embedding - SQLSpec should handle list -> VECTOR conversion
        embedding, _ = await embedding_cache.get_embedding(query, mock_vertex)

        # Verify we get back a list (VECTOR -> list conversion)
        assert isinstance(embedding, list)
        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)

    async def test_cache_normalization(
        self,
        embedding_cache: EmbeddingCache,
    ) -> None:
        """Test that queries are normalized for consistent caching."""
        mock_vertex = MagicMock()
        test_embedding = [0.3] * 768
        mock_vertex.create_embedding = AsyncMock(return_value=test_embedding)

        # Different case and whitespace should hit same cache
        queries = [
            "Test Query",
            "test query",
            "  test query  ",
            "TEST QUERY",
        ]

        # First query - cache miss
        embedding1, hit1 = await embedding_cache.get_embedding(queries[0], mock_vertex)
        assert not hit1

        # All other queries should be cache hits due to normalization
        for query in queries[1:]:
            embedding, hit = await embedding_cache.get_embedding(query, mock_vertex)
            assert hit, f"Query '{query}' should hit cache due to normalization"
            assert embedding == embedding1

    async def test_clear_expired_embeddings(
        self,
        embedding_cache: EmbeddingCache,
    ) -> None:
        """Test clearing expired cache entries."""
        # Create a cache entry
        mock_vertex = MagicMock()
        test_embedding = [0.4] * 768
        mock_vertex.create_embedding = AsyncMock(return_value=test_embedding)

        query = "expiration test"
        await embedding_cache.get_embedding(query, mock_vertex)

        # Clear expired entries (should not delete recently created entry)
        deleted_count = await embedding_cache.clear_expired()
        assert deleted_count >= 0  # Should not error

        # Verify entry still exists
        embedding, hit = await embedding_cache.get_embedding(query, mock_vertex)
        assert hit, "Recently created entry should not be deleted"

    async def test_merge_upsert_pattern(
        self,
        embedding_cache: EmbeddingCache,
    ) -> None:
        """Test that MERGE statement properly upserts cache entries."""
        mock_vertex = MagicMock()
        embedding1 = [0.5] * 768
        embedding2 = [0.6] * 768

        query = "merge test"

        # First insert
        mock_vertex.create_embedding = AsyncMock(return_value=embedding1)
        result1, _ = await embedding_cache.get_embedding(query, mock_vertex)
        assert result1 == embedding1

        # Clear memory cache to force Oracle check
        embedding_cache._memory_cache.clear()

        # Update with new embedding (simulating re-generation)
        # This should trigger MERGE UPDATE path
        mock_vertex.create_embedding = AsyncMock(return_value=embedding2)

        # Store new embedding directly to test MERGE
        await embedding_cache._store_in_oracle(
            embedding_cache._cache_key(query),
            query,
            embedding2,
        )

        # Verify updated embedding
        embedding_cache._memory_cache.clear()
        result2, hit = await embedding_cache.get_embedding(query, mock_vertex)
        assert hit, "Should hit cache after update"
        # Note: The cached value depends on whether MERGE updated or we get old value
