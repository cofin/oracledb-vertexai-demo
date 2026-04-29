"""Generic fixture management utilities for database operations.

This module provides a clean, generic approach to loading and exporting fixtures
without table-specific logic. Uses SQLSpec for database operations.
"""

from __future__ import annotations

import contextlib
import gzip
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import oracledb
import structlog
from sqlspec import sql

from app.utils.serialization import from_json, to_json

logger = structlog.get_logger(__name__)

# Oracle VARCHAR2 maximum length (use CLOB for larger values)
VARCHAR2_MAX_LENGTH = 4000
DATETIME_FIELDS = {
    "created_at",
    "updated_at",
    "last_activity",
    "expires_at",
    "last_accessed",
}


def _read_fixture_bytes(filepath: Path) -> bytes:
    """Read fixture bytes, supporting optional gzip compression."""

    if filepath.suffix == ".gz":
        with gzip.open(filepath, "rb") as file_obj:
            return file_obj.read()
    with filepath.open("rb") as file_obj:
        return file_obj.read()


def _infer_oracle_type(value: Any) -> str:
    """Infer Oracle column type for JSON_TABLE projection."""

    if isinstance(value, bool):
        return "NUMBER(1)"
    if isinstance(value, (int, float, Decimal)):
        return "NUMBER"
    if isinstance(value, (dict, list)):
        return "JSON"
    if isinstance(value, datetime):
        return "TIMESTAMP"
    if value is not None and len(str(value)) > VARCHAR2_MAX_LENGTH:
        return "CLOB"
    return f"VARCHAR2({VARCHAR2_MAX_LENGTH})"


def _prepare_value_for_export(value: Any) -> Any:
    """Normalize values for JSON serialization when exporting fixtures."""

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


def _is_vector_payload(value: Any) -> bool:
    """Detect a list-of-floats embedding payload."""

    if not isinstance(value, list) or not value:
        return False
    head = value[0]
    return isinstance(head, (int, float)) and not isinstance(head, bool)


class FixtureProcessor:
    """Handles fixture data processing with proper serialization."""

    def __init__(self, fixtures_dir: Path, expected_vector_dim: int | None = None) -> None:
        """Initialize the fixture processor.

        Args:
            fixtures_dir: Path to the fixtures directory
            expected_vector_dim: When set, vector columns whose length does not
                match are dropped from each record with a warning. This lets
                stale fixtures load against an updated VECTOR(N) schema and be
                refilled by the embedding pipeline afterwards.
        """
        self.fixtures_dir = fixtures_dir
        self.expected_vector_dim = expected_vector_dim
        self._dim_warning_emitted: set[str] = set()

    def load_fixture_data(self, filepath: Path) -> list[dict[str, Any]]:
        """Load fixture data from file, handling compression.

        Args:
            filepath: Path to fixture file

        Returns:
            List of fixture records
        """
        data_list = from_json(_read_fixture_bytes(filepath))

        if not isinstance(data_list, list):
            return []

        return [dict(item) if isinstance(item, Mapping) else item for item in data_list]

    def prepare_record(self, record: dict[str, Any]) -> Mapping[str, Any]:
        """Prepare a record for insertion by handling None values and data types properly.

        Args:
            record: Raw fixture record

        Returns:
            Processed record ready for insertion
        """
        prepared: dict[str, Any] = {}
        for key, value in record.items():
            if value is None:
                continue

            if key == "price" and isinstance(value, str):
                prepared[key] = Decimal(value)
                continue

            if key in DATETIME_FIELDS and isinstance(value, str):
                prepared[key] = datetime.fromisoformat(value)
                continue

            if (
                self.expected_vector_dim is not None
                and _is_vector_payload(value)
                and len(value) != self.expected_vector_dim
            ):
                if key not in self._dim_warning_emitted:
                    logger.warning(
                        "Skipping fixture column due to vector dimension mismatch",
                        column=key,
                        fixture_dim=len(value),
                        expected_dim=self.expected_vector_dim,
                    )
                    self._dim_warning_emitted.add(key)
                continue

            prepared[key] = value

        return prepared

    def get_fixture_files(self, table_order: list[str] | None = None) -> list[Path]:
        """Get all available fixture files sorted by dependency order.

        Args:
            table_order: Optional list defining table loading order

        Returns:
            List of fixture file paths in dependency order
        """
        if not self.fixtures_dir.exists():
            return []

        files = list(self.fixtures_dir.glob("*.json")) + list(self.fixtures_dir.glob("*.json.gz"))

        if table_order is None:
            return files

        def sort_key(filepath: Path) -> int:
            table_name = self.get_table_name(filepath.name)
            try:
                return table_order.index(table_name)
            except ValueError:
                return len(table_order)  # Unknown tables go last

        return sorted(files, key=sort_key)

    def get_table_name(self, filename: str) -> str:
        """Extract table name from fixture filename.

        Args:
            filename: Fixture filename

        Returns:
            Table name
        """
        return filename.replace(".json.gz", "").replace(".json", "")


class FixtureLoader:
    """Generic fixture loader that works with any table using SQLSpec."""

    def __init__(
        self,
        fixtures_dir: Path,
        driver: Any,
        table_order: list[str] | None = None,
        expected_vector_dim: int | None = None,
    ) -> None:
        """Initialize the fixture loader.

        Args:
            fixtures_dir: Path to fixtures directory
            driver: SQLSpec driver instance for database operations
            table_order: Optional list defining table loading order for dependencies
            expected_vector_dim: When set, vector columns whose length does not
                match are skipped during prep so stale fixtures can load against
                an updated VECTOR(N) schema.
        """
        self.processor = FixtureProcessor(fixtures_dir, expected_vector_dim=expected_vector_dim)
        self.driver = driver
        self.table_order = table_order or []

    async def load_all_fixtures(self, specific_tables: list[str] | None = None) -> dict[str, dict[str, Any] | str]:
        """Load all available fixtures into the database.

        Args:
            specific_tables: Optional list of specific tables to load

        Returns:
            Dictionary mapping table names to loading results
        """
        results: dict[str, dict[str, Any] | str] = {}
        fixture_files = self.processor.get_fixture_files(self.table_order)

        if not fixture_files and not specific_tables:
            return self._generate_missing_fixtures_results()

        for fixture_file in fixture_files:
            table_name = self.processor.get_table_name(fixture_file.name)

            if specific_tables and table_name not in specific_tables:
                continue

            try:
                result = await self._load_table_fixtures(table_name, fixture_file)
                results[table_name] = result
            except Exception as e:  # noqa: BLE001
                results[table_name] = f"Error: {e!s}"

        return results

    async def _load_table_fixtures(self, table_name: str, fixture_file: Path) -> dict[str, Any]:
        """Load fixtures using Oracle JSON_TABLE with MERGE for single-call bulk upsert.

        Uses JSON_TABLE to pass all records in a single JSON payload, then MERGE
        from the JSON_TABLE result. This combines INSERT and UPDATE in one operation.

        Args:
            table_name: Name of the table
            fixture_file: Path to fixture file

        Returns:
            Loading result statistics with keys: upserted, failed, total

        Raises:
            Exception: Any database error during fixture loading (no fallback)
        """
        fixture_data = self.processor.load_fixture_data(fixture_file)

        if not fixture_data:
            return {"upserted": 0, "failed": 0, "total": 0}

        total = len(fixture_data)

        # Process all records
        processed_records = [dict(self.processor.prepare_record(record)) for record in fixture_data]

        if not processed_records:
            return {"upserted": 0, "failed": 0, "total": 0}

        column_order: list[str] = []
        sample_values: dict[str, Any] = {}
        for record in processed_records:
            for column, value in record.items():
                if value is None:
                    continue
                if column not in column_order:
                    column_order.append(column)
                if column not in sample_values:
                    sample_values[column] = value

        if not column_order:
            return {"upserted": 0, "failed": 0, "total": total}

        update_columns = [column for column in column_order if column != "id"]
        insert_columns = column_order

        json_columns = [
            f"{column} {_infer_oracle_type(sample_values.get(column))} PATH '$.{column}'" for column in column_order
        ]

        # Build MERGE statement with JSON_TABLE
        # table_name is from internal COFFEE_SHOP_TABLES list, not user input
        merge_sql = f"""
            MERGE INTO {table_name} t
            USING (
                SELECT {", ".join(f"jt.{col}" for col in column_order)}
                FROM JSON_TABLE(
                    :payload, '$[*]'
                    COLUMNS (
                        {", ".join(json_columns)}
                    )
                ) jt
            ) src
            ON (t.id = src.id)
            WHEN MATCHED THEN UPDATE SET
                {", ".join(f"t.{col} = src.{col}" for col in update_columns)}
            WHEN NOT MATCHED THEN INSERT ({", ".join(insert_columns)})
                VALUES ({", ".join(f"src.{col}" for col in insert_columns)})
        """  # noqa: S608

        # Convert records to JSON payload using project's serialization
        payload = to_json(processed_records, as_bytes=True)
        # Bind as CLOB explicitly — payloads can be >1MB, exceeding VARCHAR2 limits
        async with self.driver.with_cursor(self.driver.connection) as cursor:
            temp_clob = await self.driver.connection.createlob(oracledb.DB_TYPE_CLOB)
            await temp_clob.write(payload)
            await cursor.execute(merge_sql.strip(), {"payload": temp_clob})
            upserted = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else total

        # Commit the transaction to persist the changes
        await self.driver.commit()

        return {"upserted": upserted, "failed": 0, "total": total}

    def _generate_missing_fixtures_results(self) -> dict[str, dict[str, Any] | str]:
        """Generate error results for missing fixture files.

        Returns:
            Dictionary with error messages for default tables
        """
        return {table_name: f"Error: Could not find the {table_name} fixture" for table_name in self.table_order}


class FixtureExporter:
    """Generic fixture exporter that works with any table using SQLSpec."""

    def __init__(self, fixtures_dir: Path, driver: Any, table_order: list[str] | None = None) -> None:
        """Initialize the fixture exporter.

        Args:
            fixtures_dir: Path to fixtures directory
            driver: SQLSpec driver instance for database operations
            table_order: Optional list of tables to export
        """
        self.processor = FixtureProcessor(fixtures_dir)
        self.driver = driver
        self.table_order = table_order or []

    async def export_all_fixtures(
        self,
        tables: list[str] | None = None,
        output_dir: Path | None = None,
        compress: bool = True,
    ) -> dict[str, str]:
        """Export database tables to fixture files.

        Args:
            tables: Optional list of specific tables to export
            output_dir: Output directory (defaults to fixtures dir)
            compress: Whether to gzip compress output

        Returns:
            Dictionary mapping table names to output paths or error messages
        """
        if output_dir is None:
            output_dir = self.processor.fixtures_dir

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        if tables is None:
            tables = self.table_order

        for table_name in tables:
            try:
                result = await self._export_table(table_name, output_dir, compress)
                results[table_name] = result
            except Exception as e:  # noqa: BLE001
                results[table_name] = f"Error: {e!s}"

        return results

    async def _export_table(self, table_name: str, output_dir: Path, compress: bool) -> str:
        """Export a specific table to fixture file.

        Args:
            table_name: Name of table to export
            output_dir: Output directory
            compress: Whether to compress output

        Returns:
            Path to output file or "No data found"
        """
        select_query = sql.select("*").from_(table_name)
        records = await self.driver.select(select_query)

        if not records:
            return "No data found"

        # Convert to JSON-serializable format
        json_data = []
        for record in records:
            normalized: dict[str, Any] = {}
            for key, value in dict(record).items():
                normalized[key] = _prepare_value_for_export(value)
            json_data.append(normalized)

        filename = f"{table_name}.json" if not compress else f"{table_name}.json.gz"
        output_file = output_dir / filename
        json_bytes = to_json(json_data, as_bytes=True)

        if compress:
            with gzip.open(output_file, "wb") as f:
                f.write(json_bytes)
        else:
            with output_file.open("wb") as f:
                f.write(json_bytes)

        return str(output_file)
