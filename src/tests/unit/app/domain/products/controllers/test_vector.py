# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Vector-search response-shape regression tests.

These guard against three regressions that have bitten this repo before:

1. The named SQL projects ``current_price`` again — the column does not exist.
2. The service grows back the ``r["distance"] = 1 - r["similarity_score"]``
   band-aid — callers should consume ``similarity_score`` directly.
3. The vector-demo controller stops surfacing ``price`` to API consumers — the
   user-visible payload must include the field that proves the bug fix landed.
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock

import pytest

from app.domain.products.controllers import VectorController
from app.domain.products.schemas import ProductMatch
from app.domain.products.services import OracleVectorSearchService
from tests.support.paths import APP_ROOT

PRODUCTS_SQL = APP_ROOT / "db" / "sql" / "products.sql"


def _vector_search_query() -> str:
    text = PRODUCTS_SQL.read_text()
    match = re.search(
        r"--\s*name:\s*vector-search-products\s*\n(?P<body>.+?)(?=\n--\s*name:|\Z)", text, flags=re.DOTALL
    )
    assert match, "vector-search-products named query missing from products.sql"
    return match.group("body")


def _vector_search_by_store_query() -> str:
    text = PRODUCTS_SQL.read_text()
    match = re.search(
        r"--\s*name:\s*vector-search-products-by-store\s*\n(?P<body>.+?)(?=\n--\s*name:|\Z)", text, flags=re.DOTALL
    )
    assert match, "vector-search-products-by-store named query missing from products.sql"
    return match.group("body")


def test_vector_search_query_projects_price_not_current_price() -> None:
    body = _vector_search_query()

    assert re.search(r"\bprice\b", body), (
        "vector-search-products must SELECT 'price'; the column was renamed from 'current_price'"
    )
    assert "current_price" not in body, (
        "vector-search-products must not reference 'current_price'; the column does not exist"
    )


def test_vector_search_query_projects_similarity_score_alias() -> None:
    body = _vector_search_query()

    assert re.search(r"AS\s+similarity_score\b", body, flags=re.IGNORECASE), (
        "vector-search-products must alias the distance expression as 'similarity_score'"
    )
    # Sanity: the projection should NOT also expose a 'distance' column —
    # callers must consume similarity_score directly.
    assert not re.search(r"AS\s+distance\b", body, flags=re.IGNORECASE), (
        "vector-search-products must not project a 'distance' column; callers use similarity_score"
    )


def test_vector_search_by_store_projects_inventory_context() -> None:
    body = _vector_search_by_store_query()

    assert "store_product_inventory" in body
    assert re.search(r"\bspi\.store_id\s*=\s*:store_id\b", body), "store-aware vector search must bind store_id"
    for alias in ("store_id", "store_name", "quantity_available", "stock_status", "pickup_available"):
        assert re.search(rf"\bAS\s+{alias}\b|\b{alias}\b", body, flags=re.IGNORECASE), (
            f"store-aware vector search must project {alias}"
        )


@pytest.mark.anyio
async def test_similarity_search_returns_typed_product_matches() -> None:
    """Service must return ProductMatch instances straight from the driver — no band-aid mutation."""

    mock_vertex = AsyncMock()
    mock_vertex.get_text_embedding.return_value = ([0.1] * 3072, False)

    mock_product_service = AsyncMock()
    mock_product_service.search_by_vector.return_value = [
        ProductMatch(id=1, name="Cold Brew", description="smooth dark cold brew", price=5.25, similarity_score=0.91),
        ProductMatch(id=2, name="Mocha", description="chocolate espresso", price=4.75, similarity_score=0.83),
    ]

    service = OracleVectorSearchService(vertex_ai_service=mock_vertex, product_service=mock_product_service)

    results, cache_hit, timings = await service.similarity_search("dark roast", k=5)

    assert cache_hit is False
    assert {"embedding_ms", "oracle_ms"} <= timings.keys()
    assert len(results) == 2

    for row in results:
        assert isinstance(row, ProductMatch), f"service must return ProductMatch instances, got {type(row).__name__}"
        assert row.price > 0, "ProductMatch must preserve 'price' from the SQL projection"
        assert 0 <= row.similarity_score <= 1, "similarity_score must be in [0, 1]"


@pytest.mark.anyio
async def test_product_service_search_by_vector_uses_store_aware_named_sql(mock_driver) -> None:
    from app.domain.products.services import ProductService

    mock_driver.select = AsyncMock(return_value=[])
    service = ProductService(mock_driver)

    await service.search_by_vector([0.1] * 3072, similarity_threshold=0.4, limit=3, store_id=16)

    statement = mock_driver.select.await_args.args[0]
    assert "store_product_inventory" in str(statement.sql)
    assert mock_driver.select.await_args.kwargs["store_id"] == 16
    assert mock_driver.select.await_args.kwargs["schema_type"] is ProductMatch


@pytest.mark.anyio
async def test_vector_demo_controller_surfaces_price_and_similarity_without_distance() -> None:
    """The /api/vector-demo SPA response surfaces ``price`` and ``similarity`` (0-100), not ``distance``."""

    from unittest.mock import MagicMock

    from app.domain.products.schemas import VectorDemo

    mock_vector_search = AsyncMock()
    mock_vector_search.similarity_search.return_value = (
        [
            ProductMatch(
                id=1, name="Cold Brew", description="smooth dark cold brew", price=5.25, similarity_score=0.91
            ),
            ProductMatch(id=2, name="Mocha", description="chocolate espresso", price=4.75, similarity_score=0.83),
        ],
        False,
        {"embedding_ms": 12.0, "oracle_ms": 4.0},
    )

    mock_metrics = AsyncMock()
    request = MagicMock()
    request.htmx = False
    request.headers = {"content-type": "application/json"}
    request.json = AsyncMock(return_value={"query": "dark roast"})

    response = await VectorController.vector_search_demo.fn(
        VectorController(owner=MagicMock()),
        vector_search_service=mock_vector_search,
        metrics_service=mock_metrics,
        request=request,
    )

    payload = response.content
    assert isinstance(payload, VectorDemo)
    assert payload.cache_hit is False
    assert payload.embedding_time_ms == pytest.approx(12.0)
    assert payload.oracle_time_ms == pytest.approx(4.0)

    assert len(payload.results) == 2
    for row in payload.results:
        assert row.name
        assert row.description
        assert row.price > 0
        assert 0 <= row.similarity <= 100

    # similarity is a 0-100 percentage derived from similarity_score, so check round-trip.
    assert payload.results[0].similarity == pytest.approx(91.0)
    assert payload.results[0].price == pytest.approx(5.25)

    # And the metrics record call uses similarity_score (not 1 - distance).
    assert mock_metrics.record_search.await_args is not None, "metrics_service.record_search must be awaited once"
    assert mock_metrics.record_search.await_args.args[0].similarity_score == pytest.approx(0.91), (
        "recorded similarity_score must come straight from the top result, not via 1 - distance"
    )
