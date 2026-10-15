# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""`GET /api/explain-plan` controller and plan-row parser unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from litestar.exceptions import ValidationException

from app.domain.products.controllers import VectorController
from app.domain.products.services import OracleVectorSearchService


@pytest.mark.anyio
async def test_explain_plan_returns_plan_lines_and_summary() -> None:
    """Verify `VectorController.explain_plan` returns `plan_lines`, `plan_summary`, and `plan_rows`."""
    mock_service = AsyncMock()
    mock_service.explain_search_plan.return_value = {
        "plan_lines": [
            "Plan hash value: 12345",
            "----------------------------------------",
            "| Id  | Operation                |",
            "----------------------------------------",
            "|   0 | SELECT STATEMENT         |",
            "|   1 |  SORT ORDER BY            |",
            "|   2 |   TABLE ACCESS BY VECTOR  |",
            "----------------------------------------",
        ],
        "plan_summary": "TABLE ACCESS BY VECTOR",
        "plan_rows": [
            {
                "id": "2",
                "operation": "TABLE ACCESS BY VECTOR",
                "name": "PRODUCT",
                "rows": "5",
                "bytes": "400",
                "cost": "3 (0)",
                "time": "00:00:01",
                "raw_line": "|   2 |   TABLE ACCESS BY VECTOR  | PRODUCT |",
                "is_vector": True,
            }
        ],
    }

    controller = VectorController(owner=MagicMock())
    request = MagicMock()
    request.query_params = {"query": "dark roast"}
    response = await VectorController.explain_plan.fn(controller, request=request, vector_search_service=mock_service)

    assert response["plan_lines"][0].startswith("Plan hash value")
    assert "VECTOR" in response["plan_summary"]
    assert response["plan_rows"][0]["operation"] == "TABLE ACCESS BY VECTOR"
    mock_service.explain_search_plan.assert_awaited_once_with("dark roast")


@pytest.mark.anyio
async def test_explain_plan_rejects_empty_query() -> None:
    """Empty or whitespace queries should fail validation up-front."""
    controller = VectorController(owner=MagicMock())
    request = MagicMock()
    request.query_params = {"query": "   "}
    with pytest.raises(ValidationException):
        await VectorController.explain_plan.fn(controller, request=request, vector_search_service=AsyncMock())


def test_explain_plan_parser_extracts_table_rows() -> None:
    """Verify `OracleVectorSearchService.parse_plan_rows` extracts structured table rows and highlights hybrid indexes."""
    rows = OracleVectorSearchService.parse_plan_rows([
        "Plan hash value: 12345",
        "| Id  | Operation                            | Name                   | Rows | Bytes | Cost (%CPU)| Time     |",
        "|   0 | SELECT STATEMENT                     |                        |    5 |   400 |     3   (0)| 00:00:01 |",
        "|* 11 |   DOMAIN INDEX                       | PRODUCT_HYBRID_CTX_IDX |      |       |     4   (0)| 00:00:01 |",
        "|  19 |   VECTOR INDEX HNSW SCAN IN-FILTER   | PRODUCT_EMBEDDING_IDX  |    1 |   256 |   156   (0)| 00:00:01 |",
    ])

    assert rows[0].is_vector is False
    assert rows[1].id == "11"
    assert rows[1].operation == "DOMAIN INDEX"
    assert rows[1].name == "PRODUCT_HYBRID_CTX_IDX"
    assert rows[1].is_vector is True
    assert rows[2].id == "19"
    assert rows[2].operation == "VECTOR INDEX HNSW SCAN IN-FILTER"
    assert rows[2].name == "PRODUCT_EMBEDDING_IDX"
    assert rows[2].is_vector is True


@pytest.mark.anyio
async def test_explain_plan_passes_vector_mode_when_requested() -> None:
    """Verify `VectorController.explain_plan` forwards `mode='vector'` when requested via query params."""
    mock_service = AsyncMock()
    mock_service.explain_search_plan.return_value = {
        "plan_lines": ["Plan hash value: 999"],
        "plan_summary": "VECTOR INDEX HNSW SCAN",
        "plan_rows": [],
    }
    controller = VectorController(owner=MagicMock())
    request = MagicMock()
    request.query_params = {"query": "dark roast", "mode": "vector"}
    response = await VectorController.explain_plan.fn(controller, request=request, vector_search_service=mock_service)

    assert response["plan_summary"] == "VECTOR INDEX HNSW SCAN"
    mock_service.explain_search_plan.assert_awaited_once_with("dark roast", mode="vector")
