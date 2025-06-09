"""Tests for recommendation service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.domain.coffee.services.recommendation_service import RecommendationService
from app.domain.coffee.schemas import ChatMessage, PointsOfInterest


class TestRecommendationService:
    """Test cases for RecommendationService."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        return {
            "vertex_ai": AsyncMock(),
            "vector_search": AsyncMock(),
            "products_service": AsyncMock(),
            "shops_service": AsyncMock(),
            "session_service": AsyncMock(),
            "conversation_service": AsyncMock(),
            "cache_service": AsyncMock(),
            "metrics_service": AsyncMock(),
        }

    @pytest.fixture
    def recommendation_service(self, mock_services):
        """Create a RecommendationService instance."""
        service = RecommendationService(
            vertex_ai_service=mock_services["vertex_ai"],
            vector_search_service=mock_services["vector_search"],
            products_service=mock_services["products_service"],
            shops_service=mock_services["shops_service"],
            session_service=mock_services["session_service"],
            conversation_service=mock_services["conversation_service"],
            cache_service=mock_services["cache_service"],
            metrics_service=mock_services["metrics_service"],
            user_id="test_user"
        )
        return service

    async def test_get_recommendation_basic(self, recommendation_service, mock_services):
        """Test basic recommendation flow."""
        # Setup mocks
        mock_session = MagicMock(id=uuid.uuid4(), session_id="test-session")
        mock_services["session_service"].create_session.return_value = mock_session
        
        # Mock vector search results
        mock_services["vector_search"].similarity_search.return_value = [
            {"metadata": {"id": 1}},
            {"metadata": {"id": 2}}
        ]
        
        # Mock product service
        mock_products = [
            MagicMock(id=1, name="Coffee A", description="Great coffee"),
            MagicMock(id=2, name="Coffee B", description="Good coffee")
        ]
        mock_services["products_service"].list.return_value = mock_products
        
        # Mock shop service
        mock_shops = [
            MagicMock(id=1, name="Shop A", address="123 Main St", latitude=1.0, longitude=2.0),
            MagicMock(id=2, name="Shop B", address="456 Oak Ave", latitude=3.0, longitude=4.0)
        ]
        mock_services["shops_service"].list.return_value = mock_shops
        
        # Mock conversation history
        mock_services["conversation_service"].get_conversation_history.return_value = []
        
        # Mock AI response
        mock_services["vertex_ai"].chat_with_history.return_value = "Here are some great coffee recommendations!"
        
        # Mock metrics
        mock_services["metrics_service"].get_performance_stats.return_value = {
            "avg_search_time_ms": 50.0
        }
        
        # Execute
        result = await recommendation_service.get_recommendation("I want good coffee")
        
        # Verify
        assert result.message == "I want good coffee"
        assert result.answer == "Here are some great coffee recommendations!"
        assert len(result.messages) == 2
        assert result.messages[0].source == "human"
        assert result.messages[1].source == "ai"
        assert len(result.points_of_interest) == 2
        
        # Verify service calls
        mock_services["vector_search"].similarity_search.assert_called_once_with(
            query="I want good coffee", k=4
        )
        mock_services["conversation_service"].add_message.assert_called()

    async def test_route_products_question_with_matches(self, recommendation_service, mock_services):
        """Test product routing with matches."""
        # Mock vector search
        mock_services["vector_search"].similarity_search.return_value = [
            {"metadata": {"id": 1}},
            {"metadata": {"id": 2}}
        ]
        
        # Mock products
        mock_products = [
            MagicMock(name="Ethiopian Coffee", description="Fruity notes"),
            MagicMock(name="Colombian Coffee", description="Balanced flavor")
        ]
        mock_services["products_service"].list.return_value = mock_products
        
        metadata, product_ids = await recommendation_service._route_products_question(
            "I want coffee recommendations"
        )
        
        assert len(product_ids) == 2
        assert "product_matches" in metadata
        assert len(metadata["product_matches"]) == 2
        assert "Ethiopian Coffee" in metadata["product_matches"][0]

    async def test_route_products_question_no_matches(self, recommendation_service, mock_services):
        """Test product routing without coffee keywords."""
        metadata, product_ids = await recommendation_service._route_products_question(
            "hello how are you"
        )
        
        assert product_ids == []
        assert "product_matches" not in metadata
        mock_services["vector_search"].similarity_search.assert_not_called()

    async def test_route_locations_question_with_matches(self, recommendation_service, mock_services):
        """Test location routing with matches."""
        mock_shops = [
            MagicMock(
                id=1, 
                name="Coffee House A", 
                address="123 Main St",
                latitude=1.0,
                longitude=2.0
            ),
            MagicMock(
                id=2,
                name="Coffee House B",
                address="456 Oak Ave", 
                latitude=3.0,
                longitude=4.0
            )
        ]
        mock_services["shops_service"].list.return_value = mock_shops
        
        metadata, location_count = await recommendation_service._route_locations_question(
            "where can I find coffee",
            matched_product_ids=[1, 2],
            chat_metadata={}
        )
        
        assert location_count == 2
        assert "locations" in metadata
        assert len(metadata["locations"]) == 2
        assert metadata["locations"][0]["name"] == "Coffee House A"

    async def test_route_locations_question_no_products(self, recommendation_service, mock_services):
        """Test location routing without product matches."""
        metadata, location_count = await recommendation_service._route_locations_question(
            "where can I find coffee",
            matched_product_ids=[],
            chat_metadata={}
        )
        
        assert location_count == 0
        assert "locations" not in metadata
        mock_services["shops_service"].list.assert_not_called()

    async def test_format_context(self, recommendation_service):
        """Test context formatting."""
        metadata = {
            "product_matches": [
                "- Coffee A: Great taste",
                "- Coffee B: Smooth flavor"
            ],
            "locations": [{"name": "Shop A"}, {"name": "Shop B"}]
        }
        
        context = recommendation_service._format_context("Find me coffee", metadata)
        
        assert "# User Query:" in context
        assert "Find me coffee" in context
        assert "# Matching coffee products" in context
        assert "Coffee A: Great taste" in context
        assert "# Product Availability:" in context
        assert "2 location(s)" in context

    async def test_stream_recommendation(self, recommendation_service, mock_services):
        """Test streaming recommendation."""
        # Setup mocks
        mock_session = MagicMock(id=uuid.uuid4(), session_id="test-session")
        mock_services["session_service"].create_session.return_value = mock_session
        mock_services["vector_search"].similarity_search.return_value = []
        mock_services["conversation_service"].get_conversation_history.return_value = []
        
        # Mock streaming response
        async def mock_stream():
            yield "Hello "
            yield "world!"
            
        mock_services["vertex_ai"].stream_content.return_value = mock_stream()
        
        # Execute
        chunks = []
        async for chunk in recommendation_service.stream_recommendation("test query"):
            chunks.append(chunk)
            
        assert chunks == ["Hello ", "world!"]
        
        # Verify conversation was saved
        assert mock_services["conversation_service"].add_message.call_count == 2
        
        # Check that the full response was saved
        calls = mock_services["conversation_service"].add_message.call_args_list
        assert calls[1][1]["content"] == "Hello world!"
        assert calls[1][1]["message_metadata"]["streamed"] is True

    async def test_get_recommendation_with_existing_session(self, recommendation_service, mock_services):
        """Test recommendation with existing session."""
        # Setup existing session
        mock_session = MagicMock(id=uuid.uuid4(), session_id="existing-session")
        mock_services["session_service"].get_active_session.return_value = mock_session
        
        # Setup other mocks
        mock_services["vector_search"].similarity_search.return_value = []
        mock_services["conversation_service"].get_conversation_history.return_value = []
        mock_services["vertex_ai"].chat_with_history.return_value = "Response"
        mock_services["metrics_service"].get_performance_stats.return_value = {}
        
        # Execute with existing session
        result = await recommendation_service.get_recommendation(
            "test query", 
            session_id="existing-session"
        )
        
        # Verify existing session was used
        mock_services["session_service"].get_active_session.assert_called_once_with("existing-session")
        mock_services["session_service"].create_session.assert_not_called()