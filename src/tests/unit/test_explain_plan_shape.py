# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Phase 5.1b contract: ``GET /api/explain-plan`` returns
``{plan_lines: list[str], plan_summary: str}`` so the explore-page
EXPLAIN PLAN viewer (Panel 2) can render them via Jinja partial.

Two driver round-trips power this endpoint:
* ``EXPLAIN PLAN FOR <vector-search-products>`` — Oracle stages the plan
  for the vector-search SQL with a representative bind set.
* ``SELECT plan_table_output FROM TABLE(DBMS_XPLAN.DISPLAY())`` — pulls
  the plan back as one row per textual line.

The integration variant (real Oracle) is exercised separately; this test
keeps the controller-level wiring honest with a fully mocked service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.domain.products.controllers import VectorController


@pytest.mark.anyio
async def test_explain_plan_returns_plan_lines_and_summary() -> None:
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
    }

    controller = object.__new__(VectorController)
    response = await VectorController.explain_plan.fn(
        controller,
        query="dark roast",
        vector_search_service=mock_service,
    )

    assert response["plan_lines"][0].startswith("Plan hash value")
    assert "VECTOR" in response["plan_summary"]
    mock_service.explain_search_plan.assert_awaited_once_with("dark roast")


@pytest.mark.anyio
async def test_explain_plan_rejects_empty_query() -> None:
    """Empty / whitespace queries should fail validation up-front."""
    from litestar.exceptions import ValidationException

    controller = object.__new__(VectorController)
    with pytest.raises(ValidationException):
        await VectorController.explain_plan.fn(
            controller,
            query="   ",
            vector_search_service=AsyncMock(),
        )
