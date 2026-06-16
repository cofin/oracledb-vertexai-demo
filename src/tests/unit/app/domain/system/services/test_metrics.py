# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

import pytest
from sqlspec.driver._async import AsyncDriverAdapterBase

from app.domain.system.schemas import SearchMetricsCreate
from app.domain.system.services import MetricsService


class RecordingDriver(AsyncDriverAdapterBase):
    """Captures SQLSpec execute calls for service-boundary assertions."""

    def __init__(self) -> None:
        self.executed: list[Any] = []
        self.committed = False

    async def execute(self, statement: Any) -> None:
        self.executed.append(statement)

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.anyio
async def test_record_search_uses_database_column_names() -> None:
    driver = RecordingDriver()
    service = MetricsService(driver)

    await service.record_search(
        SearchMetricsCreate(
            query_id="query-1",
            user_id="demo",
            search_time_ms=12.5,
            embedding_time_ms=3.0,
            oracle_time_ms=4.0,
            similarity_score=0.91,
            result_count=2,
        )
    )

    assert driver.executed, "record_search must execute one insert"
    assert driver.committed is True
    statement = str(driver.executed[0])
    assert "result_count" in statement
    assert "resultCount" not in statement
