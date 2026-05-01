# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""``POST /api/vector-demo`` returns a Jinja partial for HTMX clients and JSON for SPA clients.

The controller is invoked via ``.fn`` so the Dishka container is not booted;
the focus here is the HTMX/JSON response branch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from litestar.plugins.htmx import HTMXTemplate

from app.domain.products.controllers import VectorController
from app.domain.products.schemas import ProductMatch

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

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


def _request(*, htmx: bool) -> MagicMock:
    request = MagicMock()
    request.htmx = htmx
    request.headers = {"content-type": "application/json"}
    request.json = AsyncMock(return_value={"query": "dark roast"})
    return request


async def test_htmx_returns_partial_and_pushes_url() -> None:
    request = _request(htmx=True)
    mock_vector_search, mock_metrics = _mock_services()

    controller = object.__new__(VectorController)
    response = await VectorController.vector_search_demo.fn(
        controller,
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

    request = _request(htmx=False)
    mock_vector_search, mock_metrics = _mock_services()

    response: Any = await VectorController.vector_search_demo.fn(
        object.__new__(VectorController),
        request=request,
        vector_search_service=mock_vector_search,
        metrics_service=mock_metrics,
    )

    assert isinstance(response.content, VectorDemo)
    assert response.content.results[0].name == "Cold Brew"
    assert response.content.cache_hit is False


async def test_htmx_vector_search_route_through_test_client(
    htmx_client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain.products.services import OracleVectorSearchService
    from app.domain.system.services import MetricsService

    async def fake_similarity_search(
        self: OracleVectorSearchService,
        query: str,
        k: int = 5,
        threshold: float = 0.5,
    ) -> tuple[list[ProductMatch], bool, dict[str, float]]:
        del self, k, threshold
        assert query == "dark roast"
        return _matches(), True, {"embedding_ms": 12.0, "oracle_ms": 4.0}

    async def fake_record_search(self: MetricsService, metrics: Any) -> None:
        del self
        assert metrics.result_count == 1

    monkeypatch.setattr(OracleVectorSearchService, "similarity_search", fake_similarity_search)
    monkeypatch.setattr(MetricsService, "record_search", fake_record_search)

    response = await htmx_client.post("/api/vector-demo", data={"query": "dark roast"})

    assert response.status_code == 200, response.text[:500]
    assert response.headers["HX-Push-Url"] == "/explore?q=dark%20roast"
    assert "Cold Brew" in response.text


async def test_htmx_vector_search_returns_inline_error_on_service_failure(
    htmx_client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain.products.services import OracleVectorSearchService

    async def fail_similarity_search(
        self: OracleVectorSearchService,
        query: str,
        k: int = 5,
        threshold: float = 0.5,
    ) -> tuple[list[ProductMatch], bool, dict[str, float]]:
        del self, query, k, threshold
        msg = "Vertex AI API has not been used in project demo-project"
        raise RuntimeError(msg)

    monkeypatch.setattr(OracleVectorSearchService, "similarity_search", fail_similarity_search)

    response = await htmx_client.post("/api/vector-demo", data={"query": "dark roast"})

    assert response.status_code == 200, response.text[:500]
    assert "Vector search is unavailable" in response.text
    assert "demo-project" not in response.text


async def test_explain_plan_route_reads_query_string(
    client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain.products.schemas import ExplainPlan
    from app.domain.products.services import OracleVectorSearchService

    async def fake_explain_search_plan(self: OracleVectorSearchService, query: str) -> ExplainPlan:
        del self
        assert query == "dark roast"
        return ExplainPlan(plan_lines=["Plan hash value: 123", "TABLE ACCESS BY VECTOR"], plan_summary="TABLE ACCESS BY VECTOR")

    monkeypatch.setattr(OracleVectorSearchService, "explain_search_plan", fake_explain_search_plan)

    response = await client.get("/api/explain-plan?query=dark%20roast")

    assert response.status_code == 200, response.text[:500]
    payload = response.json()
    assert payload["planSummary"] == "TABLE ACCESS BY VECTOR"
