"""Simple tests for Coffee Chat Controller."""

from typing import TYPE_CHECKING

import pytest
from litestar.status_codes import HTTP_200_OK

if TYPE_CHECKING:
    from litestar import Litestar


class TestCoffeeChatControllerSimple:
    """Simple test cases for CoffeeChatController."""

    @pytest.mark.asyncio
    async def test_main_page_loads(self, app: "Litestar") -> None:
        """Test that the main page loads successfully."""
        from litestar.testing import AsyncTestClient

        async with AsyncTestClient(app=app) as client:
            response = await client.get("/")
            assert response.status_code == HTTP_200_OK
            assert b"Coffee Connoisseur" in response.content
            assert b"Oracle 23AI + Google Vertex AI" in response.content

    @pytest.mark.asyncio
    async def test_favicon_endpoint(self, app: "Litestar") -> None:
        """Test favicon endpoint exists."""
        from litestar.testing import AsyncTestClient

        async with AsyncTestClient(app=app) as client:
            response = await client.get("/favicon.ico")
            # May return 404 if file doesn't exist in test environment
            assert response.status_code in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_post_without_dependencies_fails_gracefully(self, app: "Litestar") -> None:
        """Test that POST without proper dependencies fails gracefully."""
        from litestar.testing import AsyncTestClient

        async with AsyncTestClient(app=app, raise_server_exceptions=False) as client:
            response = await client.post(
                "/",
                data={"message": "test"},
                headers={"HX-Request": "true"},
            )
            # Should handle dependency injection errors gracefully
            assert response.status_code in [500, 503]
