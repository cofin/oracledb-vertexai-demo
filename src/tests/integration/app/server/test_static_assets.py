# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""HTTP regression tests for the static-asset and ``/favicon.ico`` routes."""

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
