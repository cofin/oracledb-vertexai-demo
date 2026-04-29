# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Static-asset HTTP regression tests for Ch 4 Phase 2/3.

Phase 2 rescues 23 brand assets from ``src/js/public/`` to
``src/resources/public/``. Phase 3.4 wires a ``/favicon.ico`` route via the
litestar-vite static-asset router so the browser's default favicon request
resolves through the bundled output. This file pins the eventual contract
ahead of time per the chapter's TDD discipline; the test stays skipped until
Phase 3.4 lands the route.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

pytestmark = pytest.mark.anyio


async def test_favicon_resolves(client: AsyncTestClient) -> None:
    """``GET /favicon.ico`` must return 200 with an image content-type."""
    response = await client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
