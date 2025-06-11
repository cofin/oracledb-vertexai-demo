"""Tests for Vertex AI service."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.vertex_ai import OracleVectorSearchService, VertexAIService


@pytest.fixture
def vertex_ai_service() -> Generator[VertexAIService, None, None]:
    """Create a VertexAIService instance for testing."""
    with (
        patch("app.domain.coffee.services.vertex_ai.vertexai.init"),
        patch("app.domain.coffee.services.vertex_ai.GenerativeModel"),
        patch("app.domain.coffee.services.vertex_ai.get_settings") as mock_settings,
    ):
        mock_settings.return_value.app.GOOGLE_PROJECT_ID = "test-project"

        yield VertexAIService()


@pytest.fixture
def mock_metrics_service() -> AsyncMock:
    """Create a mock metrics service."""
    mock = AsyncMock()
    mock.record_search = AsyncMock()
    return mock


@pytest.fixture
def mock_cache_service() -> AsyncMock:
    """Create a mock cache service."""
    mock = AsyncMock()
    mock.get_cached_response = AsyncMock(return_value=None)
    mock.cache_response = AsyncMock()
    return mock


class TestVertexAIService:
    """Test cases for VertexAIService."""

    @pytest.mark.asyncio
    async def test_generate_content_success(self, vertex_ai_service: VertexAIService) -> None:
        """Test successful content generation."""
        # Mock the model response
        mock_response = MagicMock()
        mock_response.text = "This is a great coffee recommendation!"

        with patch.object(vertex_ai_service.model, "generate_content_async", return_value=mock_response):
            result = await vertex_ai_service.generate_content("Tell me about coffee")

        assert result == "This is a great coffee recommendation!"

    @pytest.mark.asyncio
    async def test_generate_content_with_cache_hit(
        self, vertex_ai_service: VertexAIService, mock_cache_service: AsyncMock
    ) -> None:
        """Test content generation with cache hit."""
        # Setup cache hit
        mock_cache_service.get_cached_response.return_value = {
            "content": "Cached response",
        }
        vertex_ai_service.set_services(None, mock_cache_service)  # type: ignore[arg-type]

        result = await vertex_ai_service.generate_content("Tell me about coffee")

        assert result == "Cached response"
        mock_cache_service.get_cached_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_content_with_cache_miss(
        self, vertex_ai_service: VertexAIService, mock_cache_service: AsyncMock
    ) -> None:
        """Test content generation with cache miss."""
        mock_cache_service.get_cached_response.return_value = None
        vertex_ai_service.set_services(None, mock_cache_service)  # type: ignore[arg-type]

        mock_response = MagicMock()
        mock_response.text = "Fresh response"

        with patch.object(vertex_ai_service.model, "generate_content_async", return_value=mock_response):
            result = await vertex_ai_service.generate_content("Tell me about coffee")

        assert result == "Fresh response"
        mock_cache_service.cache_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_embedding(self, vertex_ai_service: VertexAIService) -> None:
        """Test embedding creation."""
        mock_embeddings = [0.1] * 768

        with patch("app.domain.coffee.services.vertex_ai.aiplatform.gapic.PredictionServiceClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.predict.return_value = MagicMock(
                predictions=[{"embeddings": {"values": mock_embeddings}}],
            )
            mock_client.return_value = mock_instance

            result = await vertex_ai_service.create_embedding("coffee description")

        assert result == mock_embeddings
        assert len(result) == 768

    @pytest.mark.asyncio
    async def test_stream_content(self, vertex_ai_service: VertexAIService) -> None:
        """Test streaming content generation."""
        mock_chunks = [
            MagicMock(text="Hello "),
            MagicMock(text="world!"),
            MagicMock(text=None),  # Test handling None
        ]

        with patch.object(vertex_ai_service.model, "generate_content_async", return_value=mock_chunks):
            chunks = [chunk async for chunk in vertex_ai_service.stream_content("test")]

        assert chunks == ["Hello ", "world!"]


class TestOracleVectorSearchService:
    """Test cases for OracleVectorSearchService."""

    @pytest.fixture
    def mock_product_service(self) -> AsyncMock:
        """Create a mock product service."""
        mock = AsyncMock()
        mock.repository = MagicMock()
        mock.repository.session = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_similarity_search(self, vertex_ai_service: VertexAIService, mock_product_service: AsyncMock) -> None:
        """Test Oracle vector similarity search."""
        vector_search = OracleVectorSearchService(mock_product_service, vertex_ai_service)

        # Mock embedding creation
        mock_embedding = [0.1] * 768
        with patch.object(vertex_ai_service, "create_embedding", return_value=mock_embedding):
            # Mock database result
            mock_result = [
                MagicMock(id=1, name="Coffee A", description="Great coffee", distance=0.1),
                MagicMock(id=2, name="Coffee B", description="Good coffee", distance=0.2),
            ]

            mock_product_service.repository.session.execute = AsyncMock(return_value=mock_result)

            results = await vector_search.similarity_search("best coffee", k=2)

        assert len(results) == 2
        assert results[0]["name"] == "Coffee A"
        assert results[0]["distance"] == 0.1
        assert results[1]["name"] == "Coffee B"

    @pytest.mark.asyncio
    async def test_similarity_search_empty_results(
        self, vertex_ai_service: VertexAIService, mock_product_service: AsyncMock
    ) -> None:
        """Test vector search with no results."""
        vector_search = OracleVectorSearchService(mock_product_service, vertex_ai_service)

        with patch.object(vertex_ai_service, "create_embedding", return_value=[0.1] * 768):
            mock_product_service.repository.session.execute = AsyncMock(
                return_value=[],
            )

            results = await vector_search.similarity_search("obscure query", k=4)

        assert results == []

    @pytest.mark.asyncio
    async def test_similarity_search_error_handling(
        self, vertex_ai_service: VertexAIService, mock_product_service: AsyncMock
    ) -> None:
        """Test vector search error handling."""
        vector_search = OracleVectorSearchService(mock_product_service, vertex_ai_service)

        with patch.object(vertex_ai_service, "create_embedding", side_effect=Exception("Embedding error")):
            results = await vector_search.similarity_search("test query", k=4)

        assert results == []  # Should return empty list on error
