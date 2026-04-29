# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Phase 5.5 contract: ``POST /api/vector-demo`` returns the
``partials/search_result_list.html.j2`` fragment for HTMX clients
(wrapped in ``PushUrl`` so the explore page URL captures ``?q=...``)
and the existing JSON dict for SPA clients.

Like the chat partial tests this exercises the controller via ``.fn``
to avoid booting the full Dishka container — the wiring being asserted
is the HTMX vs JSON branch, not the DI graph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from litestar.plugins.htmx import HTMXTemplate

from app.domain.products import schemas as product_schemas
from app.domain.products.controllers import VectorController
from app.domain.products.schemas import ProductMatch

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.anyio


def _matches() -> list[ProductMatch]:
    return [
        ProductMatch(
            id=1,
            name="Cold Brew",
            description="smooth dark cold brew",
            price=5.25,
            similarity_score=0.91,
        ),
    ]


def _mock_services() -> tuple[AsyncMock, AsyncMock]:
    mock_vector_search = AsyncMock()
    mock_vector_search.similarity_search.return_value = (
        _matches(),
        False,
        {"embedding_ms": 12.0, "oracle_ms": 4.0},
    )
    mock_metrics = AsyncMock()
    return mock_vector_search, mock_metrics


async def test_htmx_returns_partial_and_pushes_url() -> None:
    request = MagicMock()
    request.htmx = True
    mock_vector_search, mock_metrics = _mock_services()

    controller = object.__new__(VectorController)
    response = await VectorController.vector_search_demo.fn(
        controller,
        data=product_schemas.VectorQuery(query="dark roast"),
        request=request,
        vector_search_service=mock_vector_search,
        metrics_service=mock_metrics,
    )

    assert isinstance(response, HTMXTemplate)
    assert response.template_name == "partials/search_result_list.html.j2"
    # HTMXTemplate(push_url=...) writes HX-Push-Url at construction time —
    # the browser uses that header to capture /explore?q=... in history.
    assert response.headers["HX-Push-Url"] == "/explore?q=dark%20roast"


async def test_non_htmx_returns_json() -> None:
    from app.domain.products.schemas import VectorDemo

    request = MagicMock()
    request.htmx = False
    mock_vector_search, mock_metrics = _mock_services()

    response: Any = await VectorController.vector_search_demo.fn(
        object.__new__(VectorController),
        data=product_schemas.VectorQuery(query="dark roast"),
        request=request,
        vector_search_service=mock_vector_search,
        metrics_service=mock_metrics,
    )

    assert isinstance(response.content, VectorDemo)
    assert response.content.results[0].name == "Cold Brew"
    assert response.content.cache_hit is False
