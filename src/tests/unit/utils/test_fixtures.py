# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin the ON-clause aliasing of the FixtureLoader Oracle MERGE."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.db.utils import _reset_sequences
from app.utils.fixtures import FixtureLoader, _prepare_record

pytestmark = pytest.mark.anyio


class _CaptureResult:
    """Stub execution result reporting a single affected row."""

    rowcount = 1


class _CaptureDriver:
    """Async driver double that records the SQL passed to ``execute``."""

    def __init__(self) -> None:
        self.statements: list[Any] = []

    async def execute(self, statement: Any) -> Any:
        self.statements.append(statement)
        return _CaptureResult()

    async def commit(self) -> None:
        return None


async def test_merge_renders_aliased_target() -> None:
    """Verify FixtureLoader MERGE statement aliases the target table as `t` in the ON clause."""
    driver = _CaptureDriver()
    loader = FixtureLoader(fixtures_dir=Path("/tmp"), driver=driver, table_order=["product"])

    await loader._merge_records("product", [{"id": 1, "name": "x"}])

    assert driver.statements, "FixtureLoader must execute a MERGE statement"
    rendered = driver.statements[0].build().sql.lower()

    assert "merge into" in rendered
    assert '"product" "t"' in rendered or "product t" in rendered, (
        f"Target table is missing the `t` alias used in ON clause: {rendered}"
    )
    assert '"t"."id"' in rendered or "t.id" in rendered, f"ON clause does not reference `t.id`: {rendered}"


def test_prepare_record_converts_boolean_for_oracle_json_table() -> None:
    """Verify `_prepare_record` converts Python booleans to integer 0/1 flags for Oracle JSON_TABLE."""
    prepared = _prepare_record({"id": 1, "pickup_available": False, "in_stock": True})

    assert prepared["pickup_available"] == 0
    assert prepared["in_stock"] == 1


def test_prepare_record_preserves_embedding_vectors_for_oracle_binding() -> None:
    """Verify `_prepare_record` preserves float list embeddings unchanged for Oracle VECTOR binding."""
    embedding = [0.1, 0.2, 0.3]

    prepared = _prepare_record({"id": 1, "embedding": embedding})

    assert prepared["embedding"] == embedding
    assert isinstance(prepared["embedding"], list)


async def test_reset_sequences_includes_agent_event() -> None:
    """Verify `_reset_sequences` resets the `agent_event` identity sequence."""
    driver: Any = _CaptureDriver()

    await _reset_sequences(driver)

    assert any("ALTER TABLE agent_event MODIFY id" in str(stmt) for stmt in driver.statements)
