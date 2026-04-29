"""Static-asset HTTP regression tests for Ch 4 Phase 2/3.

Phase 2 rescues 23 brand assets from ``src/js/public/`` to
``src/resources/public/``. Phase 3.4 wires a ``/favicon.ico`` route via the
litestar-vite static-asset router so the browser's default favicon request
resolves through the bundled output. This file pins the eventual contract
ahead of time per the chapter's TDD discipline; the test stays skipped until
Phase 3.4 lands the route.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Phase 3.4 not yet complete — favicon route lands in 4.11 (Phase 3 frontend scaffold)")
async def test_favicon_resolves() -> None:
    """``GET /favicon.ico`` must return 200 with ``image/x-icon`` once Phase 3.4 lands."""
    from httpx import AsyncClient

    from app.server.asgi import create_app

    async with AsyncClient(app=create_app(), base_url="http://test") as client:
        response = await client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
