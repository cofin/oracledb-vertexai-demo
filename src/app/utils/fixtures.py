# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Load and export JSON fixtures via sqlspec primitives."""

from __future__ import annotations

import contextlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog
from anyio import Path as AsyncPath
from sqlspec import sql
from sqlspec.utils.fixtures import open_fixture_async, write_fixture_async

logger = structlog.get_logger(__name__)

DATETIME_FIELDS = frozenset({"created_at", "updated_at", "last_activity", "expires_at", "last_accessed"})


class FixtureLoader:
    """Idempotent fixture upsert via Oracle ``MERGE`` + ``JSON_TABLE``."""

    def __init__(self, fixtures_dir: Path, driver: Any, table_order: list[str]) -> None:
        self.fixtures_dir = fixtures_dir
        self.driver = driver
        self.table_order = table_order

    async def load_all_fixtures(self, specific_tables: list[str] | None = None) -> dict[str, dict[str, Any] | str]:
        """Load fixtures for every table in ``table_order``.

        Returns:
            Mapping from table name to either an ``{"upserted","failed","total"}``
            stats dict on success, or an ``"Error: ..."`` string on failure.
        """
        results: dict[str, dict[str, Any] | str] = {}
        for table_name in specific_tables or self.table_order:
            try:
                records = await open_fixture_async(self.fixtures_dir, table_name)
            except FileNotFoundError as exc:
                results[table_name] = f"Error: {exc}"
                continue

            if not isinstance(records, list) or not records:
                results[table_name] = {"upserted": 0, "failed": 0, "total": 0}
                continue

            prepared = [_prepare_record(record) for record in records]
            try:
                upserted = await self._merge_records(table_name, prepared)
            except Exception as exc:  # noqa: BLE001
                results[table_name] = f"Error: {exc!s}"
                continue
            results[table_name] = {"upserted": upserted, "failed": 0, "total": len(prepared)}
        return results

    async def _merge_records(self, table_name: str, records: list[dict[str, Any]]) -> int:
        """Merge prepared records into ``table_name``.

        Returns:
            The number of rows upserted (``rowcount`` if the driver reports it,
            otherwise the number of records submitted).
        """
        if not records:
            return 0

        columns = list({key for record in records for key in record})
        update_columns = [col for col in columns if col != "id"]

        statement = (
            sql
            .merge(dialect="oracle")
            .into(table_name, alias="t")
            .using(records, alias="src")
            .on("t.id = src.id")
            .when_matched_then_update({col: f"src.{col}" for col in update_columns})
            .when_not_matched_then_insert(columns=columns, values=[f"src.{col}" for col in columns])
        )
        result = await self.driver.execute(statement)
        await self.driver.commit()
        return getattr(result, "rowcount", None) or len(records)


class FixtureExporter:
    """Write each table's rows to a JSON (optionally gzipped) fixture file."""

    def __init__(self, fixtures_dir: Path, driver: Any, table_order: list[str]) -> None:
        self.fixtures_dir = fixtures_dir
        self.driver = driver
        self.table_order = table_order

    async def export_all_fixtures(
        self,
        tables: list[str] | None = None,
        output_dir: Path | None = None,
        compress: bool = True,
    ) -> dict[str, str]:
        """Export each requested table to a fixture file.

        Returns:
            Mapping from table name to the output file path on success or
            ``"Error: ..."`` / ``"No data found"`` otherwise.
        """
        target_dir = Path(output_dir or self.fixtures_dir)
        await AsyncPath(target_dir).mkdir(parents=True, exist_ok=True)

        results: dict[str, str] = {}
        for table_name in tables or self.table_order:
            try:
                results[table_name] = await self._export_table(table_name, target_dir, compress=compress)
            except Exception as exc:  # noqa: BLE001
                results[table_name] = f"Error: {exc!s}"
        return results

    async def _export_table(self, table_name: str, output_dir: Path, *, compress: bool) -> str:
        """Export one table.

        Returns:
            The output file path on success, or ``"No data found"`` when the
            table is empty.
        """
        rows = await self.driver.select(sql.select("*").from_(table_name))
        if not rows:
            return "No data found"

        normalized = [{key: _prepare_for_export(value) for key, value in dict(row).items()} for row in rows]
        await write_fixture_async(str(output_dir), table_name, normalized, compress=compress)
        suffix = ".json.gz" if compress else ".json"
        return str(output_dir / f"{table_name}{suffix}")


def _prepare_record(record: dict[str, Any]) -> dict[str, Any]:
    """Coerce JSON-encoded values to Python types Oracle JSON_TABLE accepts.

    Returns:
        A copy of ``record`` with ``None`` values dropped, ``price`` strings
        promoted to ``Decimal``, and ISO-8601 audit-column strings parsed to
        ``datetime``.
    """
    prepared: dict[str, Any] = {}
    for key, value in record.items():
        if value is None:
            continue
        if key == "price" and isinstance(value, str):
            prepared[key] = Decimal(value)
        elif isinstance(value, bool):
            prepared[key] = int(value)
        elif key in DATETIME_FIELDS and isinstance(value, str):
            prepared[key] = datetime.fromisoformat(value)
        else:
            prepared[key] = value
    return prepared


def _prepare_for_export(value: Any) -> Any:
    """Normalize a row value for JSON serialization.

    Returns:
        ``list`` for numpy-style arrays, ISO strings for ``datetime``-like
        values, decoded text or hex for ``bytes``; all other values pass through.
    """
    if hasattr(value, "tolist"):
        with contextlib.suppress(TypeError):
            return value.tolist()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()
    return value
