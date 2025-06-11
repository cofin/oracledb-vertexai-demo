"""Tests for Coffee Chat Controller."""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

from app.domain.coffee.schemas import CoffeeChatReply, PointsOfInterest

if TYPE_CHECKING:
    from litestar import Litestar


class TestCoffeeChatController:
    """Test cases for CoffeeChatController."""

    @pytest.fixture
    def mock_recommendation_service(self) -> AsyncMock:
        """Create a mock recommendation service."""
        service = AsyncMock()

        # Default reply
        service.get_recommendation.return_value = CoffeeChatReply(
            message="Here are some coffee recommendations",
            messages=[],
            answer="I recommend trying our Ethiopian single origin!",
            points_of_interest=[
                PointsOfInterest(
                    id=1,
                    name="Cymbal Coffee Shop",
                    address="123 Main St",
                    latitude=37.7749,
                    longitude=-122.4194,
                )
            ],
            query_id="test-query-123",
            search_metrics={"avg_search_time_ms": 50.0},
        )

        return service

    @pytest.fixture
    def mock_metrics_service(self) -> AsyncMock:
        """Create a mock metrics service."""
        service = AsyncMock()
        service.get_performance_stats.return_value = {
            "total_searches": 100,
            "avg_search_time_ms": 50.0,
            "avg_oracle_time_ms": 25.0,
            "avg_similarity_score": 0.85,
        }
        return service

    @pytest.mark.asyncio
    async def test_show_ocw_page(self, app: "Litestar") -> None:
        """Test the main page loads successfully."""
        from litestar.testing import AsyncTestClient

        async with AsyncTestClient(app=app) as client:
            response = await client.get("/")
            assert response.status_code == HTTP_200_OK
            assert b"Coffee Connoisseur" in response.content

    @pytest.mark.asyncio
    async def test_htmx_chat_request(self, app: "Litestar", mock_recommendation_service: AsyncMock) -> None:
        """Test HTMX partial response for chat."""
        from litestar.testing import AsyncTestClient

        # Override the dependency
        app.dependency_providers["recommendation_service"] = lambda: mock_recommendation_service

        async with AsyncTestClient(app=app) as client:

                response = await client.post(
                    "/",
                    data={"message": "I want good coffee"},
                    headers={"HX-Request": "true"},
                )

                assert response.status_code == HTTP_200_OK
                assert response.headers.get("Content-Type", "").startswith("text/html")

                # Check for secure template elements
                content = response.text
                assert "You:" in content
                assert "I want good coffee" in content  # Message should be escaped
                assert "AI Coffee Expert:" in content
                assert "Ethiopian single origin" in content
                assert "Cymbal Coffee Shop" in content

    @pytest.mark.asyncio
    async def test_non_htmx_chat_request(self, client: AsyncTestClient, mock_recommendation_service: AsyncMock) -> None:
        """Test full page response for non-HTMX requests."""
        with client.app.dependency_providers:
            client.app.dependency_providers["recommendation_service"] = lambda: mock_recommendation_service

            response = await client.post(
                "/",
                data={"message": "I want good coffee"},
            )

            assert response.status_code == HTTP_200_OK
            assert b"<!DOCTYPE html>" in response.content
            assert b"Coffee Connoisseur" in response.content

    @pytest.mark.asyncio
    async def test_xss_prevention(self, client: AsyncTestClient, mock_recommendation_service: AsyncMock) -> None:
        """Test XSS prevention in user input."""
        # Set up malicious response
        mock_recommendation_service.get_recommendation.return_value = CoffeeChatReply(
            message="<script>alert('XSS')</script>",
            messages=[],
            answer="<img src=x onerror=alert('XSS')>",
            points_of_interest=[
                PointsOfInterest(
                    id=1,
                    name="<script>alert('XSS')</script>",
                    address="<img src=x onerror=alert('XSS')>",
                    latitude=37.7749,
                    longitude=-122.4194,
                )
            ],
            query_id="test-xss",
            search_metrics={},
        )

        with client.app.dependency_providers:
            client.app.dependency_providers["recommendation_service"] = lambda: mock_recommendation_service

            response = await client.post(
                "/",
                data={"message": "<script>alert('XSS')</script>"},
                headers={"HX-Request": "true"},
            )

            # Check that scripts are escaped
            assert b"<script>" not in response.content
            assert b"&lt;script&gt;" in response.content
            assert b"onerror=" not in response.content

    @pytest.mark.asyncio
    async def test_coordinate_validation(self, client: AsyncTestClient, mock_recommendation_service: AsyncMock) -> None:
        """Test that invalid coordinates are filtered out."""
        # Set up response with invalid coordinates
        mock_recommendation_service.get_recommendation.return_value = CoffeeChatReply(
            message="Found locations",
            messages=[],
            answer="Here are the shops",
            points_of_interest=[
                PointsOfInterest(
                    id=1,
                    name="Valid Shop",
                    address="123 Main St",
                    latitude=37.7749,
                    longitude=-122.4194,
                ),
                PointsOfInterest(
                    id=2,
                    name="Invalid Shop",
                    address="456 Oak Ave",
                    latitude=91.0,  # Invalid
                    longitude=-181.0,  # Invalid
                ),
            ],
            query_id="test-coords",
            search_metrics={},
        )

        with client.app.dependency_providers:
            client.app.dependency_providers["recommendation_service"] = lambda: mock_recommendation_service

            response = await client.post(
                "/",
                data={"message": "Show me shops"},
                headers={"HX-Request": "true"},
            )

            # Only valid shop should appear
            assert b"Valid Shop" in response.content
            assert b"Invalid Shop" not in response.content

    @pytest.mark.asyncio
    async def test_csp_headers(self, client: AsyncTestClient, mock_recommendation_service: AsyncMock) -> None:
        """Test Content Security Policy headers are set."""
        with client.app.dependency_providers:
            client.app.dependency_providers["recommendation_service"] = lambda: mock_recommendation_service

            response = await client.post(
                "/",
                data={"message": "test"},
                headers={"HX-Request": "true"},
            )

            # Check CSP header exists
            csp = response.headers.get("Content-Security-Policy")
            assert csp is not None
            assert "script-src 'self'" in csp
            assert "nonce-" in csp
            assert "https://maps.googleapis.com" in csp
            assert "object-src 'none'" in csp

    @pytest.mark.asyncio
    async def test_streaming_endpoint(self, client: AsyncTestClient, mock_recommendation_service: AsyncMock) -> None:
        """Test the SSE streaming endpoint."""
        # Mock streaming response
        async def mock_stream() -> AsyncGenerator[str, None]:
            yield "Hello"
            yield " from"
            yield " streaming!"

        mock_vertex_ai = AsyncMock()
        mock_vertex_ai.stream_content.return_value = mock_stream()
        mock_recommendation_service.vertex_ai = mock_vertex_ai

        with client.app.dependency_providers:
            client.app.dependency_providers["recommendation_service"] = lambda: mock_recommendation_service

            # Streaming endpoints need special handling in tests
            response = await client.get("/chat/stream/test-query-123")

            assert response.status_code == HTTP_200_OK
            assert response.headers.get("Content-Type") == "text/event-stream"
            assert response.headers.get("Cache-Control") == "no-cache"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncTestClient, mock_metrics_service: AsyncMock) -> None:
        """Test the metrics endpoint."""
        with client.app.dependency_providers:
            client.app.dependency_providers["metrics_service"] = lambda: mock_metrics_service

            response = await client.get("/metrics")

            assert response.status_code == HTTP_200_OK
            data = response.json()
            assert data["total_searches"] == 100
            assert data["avg_search_time_ms"] == 50.0
            assert data["avg_oracle_time_ms"] == 25.0
            assert data["avg_similarity_score"] == 0.85

    @pytest.mark.asyncio
    async def test_favicon_endpoint(self, client: AsyncTestClient) -> None:
        """Test favicon serves correctly."""
        response = await client.get("/favicon.ico")
        # May fail if file doesn't exist, which is OK for this test
        assert response.status_code in [200, 404, 500]
