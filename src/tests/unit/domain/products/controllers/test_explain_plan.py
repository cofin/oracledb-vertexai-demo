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
    """Verify `OracleVectorSearchService.parse_plan_rows` extracts structured table rows."""
    rows = OracleVectorSearchService.parse_plan_rows([
        "Plan hash value: 12345",
        "| Id  | Operation                 | Name    | Rows | Bytes | Cost (%CPU)| Time     |",
        "|   0 | SELECT STATEMENT          |         |    5 |   400 |     3   (0)| 00:00:01 |",
        "|   2 |   TABLE ACCESS BY VECTOR  | PRODUCT |    5 |   400 |     3   (0)| 00:00:01 |",
    ])

    assert rows[1].id == "2"
    assert rows[1].operation == "TABLE ACCESS BY VECTOR"
    assert rows[1].name == "PRODUCT"
    assert rows[1].is_vector is True
