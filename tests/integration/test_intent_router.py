"""Integration tests for IntentRouter with SQLSpec."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.intent_router import IntentRouter

pytestmark = pytest.mark.anyio


class TestIntentRouter:
    """Test suite for IntentRouter using SQLSpec and Oracle VECTOR_DISTANCE."""

    async def test_route_intent_vector_search(
        self,
        intent_router: IntentRouter,
    ) -> None:
        """Test intent routing using Oracle native vector similarity search."""
        # Create mock embedding
        mock_vertex = MagicMock()
        query_embedding = [0.1] * 768
        mock_vertex.get_text_embedding = AsyncMock(return_value=query_embedding)

        # Mock the vertex_ai service
        intent_router.vertex_ai = mock_vertex

        query = "I need a strong coffee"

        # Route intent
        results, embedding_hit = await intent_router.route_intent(query)

        assert isinstance(results, list)
        # Should return list of (intent, score, phrase) tuples
        for intent, score, phrase in results:
            assert isinstance(intent, str)
            assert isinstance(score, float)
            assert isinstance(phrase, str)
            assert 0.0 <= score <= 1.0

    async def test_route_intent_single(
        self,
        intent_router: IntentRouter,
    ) -> None:
        """Test single intent routing with fallback."""
        mock_vertex = MagicMock()
        query_embedding = [0.2] * 768
        mock_vertex.get_text_embedding = AsyncMock(return_value=query_embedding)

        intent_router.vertex_ai = mock_vertex

        query = "coffee recommendation please"

        # Route to single intent
        intent, confidence, phrase, cache_hit = await intent_router.route_intent_single(query)

        assert isinstance(intent, str)
        assert isinstance(confidence, float)
        assert isinstance(phrase, str)
        assert isinstance(cache_hit, bool)
        assert 0.0 <= confidence <= 1.0

    async def test_vector_distance_calculation(
        self,
        intent_router: IntentRouter,
    ) -> None:
        """Test that VECTOR_DISTANCE returns proper similarity scores."""
        mock_vertex = MagicMock()
        query_embedding = [0.3] * 768
        mock_vertex.get_text_embedding = AsyncMock(return_value=query_embedding)

        intent_router.vertex_ai = mock_vertex

        query = "what coffee do you have"

        results, _ = await intent_router.route_intent(query)

        # Verify results are sorted by similarity (highest first)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i][1] >= results[i + 1][1], (
                    "Results should be sorted by similarity score descending"
                )

    async def test_intent_threshold_filtering(
        self,
        intent_router: IntentRouter,
    ) -> None:
        """Test that intent-specific thresholds filter results correctly."""
        mock_vertex = MagicMock()
        query_embedding = [0.4] * 768
        mock_vertex.get_text_embedding = AsyncMock(return_value=query_embedding)

        intent_router.vertex_ai = mock_vertex

        # Test with a query that should match PRODUCT_RAG
        query = "coffee recommendations"

        results, _ = await intent_router.route_intent(query)

        # All results should meet their intent-specific threshold
        from app.config import INTENT_THRESHOLDS
        for intent, score, _ in results:
            threshold = INTENT_THRESHOLDS.get(intent, 0.70)
            assert score >= threshold, (
                f"Score {score} for intent {intent} should meet threshold {threshold}"
            )

    async def test_automatic_vector_conversion(
        self,
        intent_router: IntentRouter,
    ) -> None:
        """Test that SQLSpec automatically handles vector parameter conversion."""
        # This test verifies that we can pass Python list directly to VECTOR_DISTANCE
        # without manual array.array() conversion

        mock_vertex = MagicMock()
        # Create embedding as Python list (not array.array)
        query_embedding = [float(i) / 768 for i in range(768)]
        mock_vertex.get_text_embedding = AsyncMock(return_value=query_embedding)

        intent_router.vertex_ai = mock_vertex

        # This should work without errors - SQLSpec handles conversion
        results, _ = await intent_router.route_intent("test query")

        assert isinstance(results, list)
        # If we get results, vector conversion worked correctly

    async def test_llm_fallback_classification(
        self,
        intent_router: IntentRouter,
    ) -> None:
        """Test LLM fallback for medium-confidence queries."""
        mock_vertex = MagicMock()
        query_embedding = [0.5] * 768
        mock_vertex.get_text_embedding = AsyncMock(return_value=query_embedding)

        # Mock LLM response
        mock_vertex.generate_content = AsyncMock(return_value=("PRODUCT_RAG", {}))

        intent_router.vertex_ai = mock_vertex

        # Test with fallback routing
        intent, confidence, method = await intent_router.route_with_llm_fallback(
            query="some ambiguous query",
            high_confidence_threshold=0.9,
            medium_confidence_threshold=0.5,
        )

        assert intent in ["PRODUCT_RAG", "GENERAL_CONVERSATION"]
        assert method in ["vector", "llm_fallback", "default"]

    async def test_default_to_general_conversation(
        self,
        intent_router: IntentRouter,
    ) -> None:
        """Test fallback to GENERAL_CONVERSATION for no matches."""
        mock_vertex = MagicMock()
        # Create embedding that won't match anything
        query_embedding = [0.0] * 768
        mock_vertex.get_text_embedding = AsyncMock(return_value=query_embedding)

        intent_router.vertex_ai = mock_vertex

        # Query unlikely to match anything
        query = "xyzabc123nonsense"

        intent, confidence, phrase, _ = await intent_router.route_intent_single(query)

        # Should default to GENERAL_CONVERSATION with 0.0 confidence
        assert intent == "GENERAL_CONVERSATION"
        assert confidence == 0.0
