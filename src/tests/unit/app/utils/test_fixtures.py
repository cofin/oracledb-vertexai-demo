# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin the ON-clause aliasing of the FixtureLoader Oracle MERGE."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.utils.fixtures import FixtureLoader, _prepare_record


class _CaptureDriver:
    """Async driver double that records the SQL passed to ``execute``."""

    def __init__(self) -> None:
        self.statements: list[Any] = []

    async def execute(self, statement: Any) -> Any:
        self.statements.append(statement)

        class _Result:
            rowcount = 1

        return _Result()

    async def commit(self) -> None:
        return None


@pytest.mark.asyncio
async def test_merge_renders_aliased_target() -> None:
    driver = _CaptureDriver()
    loader = FixtureLoader(fixtures_dir=Path("/tmp"), driver=driver, table_order=["product"])

    await loader._merge_records("product", [{"id": 1, "name": "x"}])

    assert driver.statements, "FixtureLoader must execute a MERGE statement"
    rendered = driver.statements[0].build().sql.lower()

    assert "merge into" in rendered
    assert '"product" "t"' in rendered or "product t" in rendered, (
        f"Target table is missing the `t` alias used in ON clause: {rendered}"
    )
    assert '"t"."id"' in rendered or "t.id" in rendered, (
        f"ON clause does not reference `t.id`: {rendered}"
    )


def test_prepare_record_converts_boolean_for_oracle_json_table() -> None:
    prepared = _prepare_record({"id": 1, "pickup_available": False, "in_stock": True})

    assert prepared["pickup_available"] == 0
    assert prepared["in_stock"] == 1
