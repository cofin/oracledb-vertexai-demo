"""Generic fixture management utilities for database operations.

This module provides a clean, generic approach to loading and exporting fixtures
without table-specific logic. Uses SQLSpec for database operations.
"""

from __future__ import annotations

import gzip
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlspec import sql

from app.utils.serialization import from_json, to_json

# Oracle VARCHAR2 maximum length (use CLOB for larger values)
VARCHAR2_MAX_LENGTH = 4000


class FixtureProcessor:
    """Handles fixture data processing with proper serialization."""

    def __init__(self, fixtures_dir: Path) -> None:
        """Initialize the fixture processor.

        Args:
            fixtures_dir: Path to the fixtures directory
        """
        self.fixtures_dir = fixtures_dir

    def load_fixture_data(self, filepath: Path) -> list[dict[str, Any]]:
        """Load fixture data from file, handling compression.

        Args:
            filepath: Path to fixture file

        Returns:
            List of fixture records
        """
        if filepath.suffix == ".gz":
            with gzip.open(filepath, "rb") as f:
                data = f.read()
        else:
            with filepath.open("rb") as f:
                data = f.read()

        data_list = from_json(data)
        # Convert to list of dicts if needed
        if isinstance(data_list, list):
            return [dict(item) if isinstance(item, Mapping) else item for item in data_list]
        return []  # Return empty list if data is not a list

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
                continue  # Exclude None values to let database handle defaults

            # Handle data type conversions for common cases
            if key == "price" and isinstance(value, str):
                # Convert price string to Decimal for database
                prepared[key] = Decimal(value)
            elif key == "embedding" and isinstance(value, str):
                # Handle embedding vector conversions from numpy array string format
                import numpy as np

                # Remove newlines and normalize whitespace from numpy string format
                cleaned = value.replace("\n", " ")
                # Normalize multiple spaces to single space
                import re

                cleaned = re.sub(r"\s+", " ", cleaned).strip()

                try:
                    # Parse numpy array string format: "[ 1.0 2.0 3.0 ... ]"
                    if cleaned.startswith("[") and cleaned.endswith("]"):
                        # Remove brackets and split by whitespace
                        numbers_str = cleaned[1:-1].strip()
                        # Split by whitespace and convert to floats
                        float_values = [float(x) for x in numbers_str.split() if x.strip()]
                        prepared[key] = float_values
                    else:
                        # Fallback: try numpy fromstring
                        array_data = np.fromstring(cleaned, sep=" ")
                        prepared[key] = array_data.tolist()
                except (ValueError, TypeError):
                    # If parsing fails, skip this field and continue
                    continue
            elif key in ("created_at", "updated_at", "last_activity", "expires_at", "last_accessed") and isinstance(
                value, str
            ):
                # Convert ISO timestamp strings to datetime objects
                prepared[key] = datetime.fromisoformat(value)
            else:
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

    def __init__(self, fixtures_dir: Path, driver: Any, table_order: list[str] | None = None) -> None:
        """Initialize the fixture loader.

        Args:
            fixtures_dir: Path to fixtures directory
            driver: SQLSpec driver instance for database operations
            table_order: Optional list defining table loading order for dependencies
        """
        self.processor = FixtureProcessor(fixtures_dir)
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

        # Get column information from first record
        # Note: We include 'id' in all operations to preserve fixture IDs for idempotent loading
        first_record = processed_records[0]
        all_columns = [col for col in first_record if first_record[col] is not None]
        update_columns = [col for col in all_columns if col != "id"]  # UPDATE doesn't change id
        insert_columns = all_columns  # INSERT includes id to preserve fixture IDs

        # Build JSON_TABLE column definitions with type inference
        json_columns = []
        for col in all_columns:
            val = first_record[col]
            if isinstance(val, bool):
                oracle_type = "NUMBER(1)"  # JSON_TABLE doesn't support BOOLEAN
            elif isinstance(val, (int, float)):
                oracle_type = "NUMBER"
            elif isinstance(val, (dict, list)):
                oracle_type = "JSON"
            elif isinstance(val, datetime):
                oracle_type = "TIMESTAMP"
            elif hasattr(val, "__len__") and len(str(val)) > VARCHAR2_MAX_LENGTH:
                oracle_type = "CLOB"
            else:
                oracle_type = f"VARCHAR2({VARCHAR2_MAX_LENGTH})"

            json_columns.append(f"{col} {oracle_type} PATH '$.{col}'")

        # Build MERGE statement with JSON_TABLE
        # table_name is from internal COFFEE_SHOP_TABLES list, not user input
        merge_sql = f"""
            MERGE INTO {table_name} t
            USING (
                SELECT {", ".join([f"jt.{col}" for col in all_columns])}
                FROM JSON_TABLE(
                    :payload, '$[*]'
                    COLUMNS (
                        {", ".join(json_columns)}
                    )
                ) jt
            ) src
            ON (t.id = src.id)
            WHEN MATCHED THEN UPDATE SET
                {", ".join([f"t.{col} = src.{col}" for col in update_columns])}
            WHEN NOT MATCHED THEN INSERT ({", ".join(insert_columns)})
                VALUES ({", ".join([f"src.{col}" for col in insert_columns])})
        """  # noqa: S608

        # Convert records to JSON payload using project's serialization
        payload = to_json(processed_records).decode("utf-8")

        # Execute MERGE with JSON payload bound as CLOB to handle large payloads (>1MB)
        import oracledb

        async with self.driver.with_cursor(self.driver.connection) as cursor:
            # Create a temporary CLOB and write the JSON payload to it
            # This is necessary because the payload can exceed VARCHAR2 limits (>32KB)
            temp_clob = await self.driver.connection.createlob(oracledb.DB_TYPE_CLOB)
            await temp_clob.write(payload)

            # Execute MERGE with the CLOB object
            await cursor.execute(merge_sql.strip(), {"payload": temp_clob})
            upserted = cursor.rowcount if cursor.rowcount > 0 else total

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
            record_dict = dict(record)

            # Handle special types
            for key, value in record_dict.items():
                if hasattr(value, "isoformat"):
                    record_dict[key] = value.isoformat()
                elif isinstance(value, bytes):
                    try:
                        record_dict[key] = value.decode("utf-8")
                    except UnicodeDecodeError:
                        record_dict[key] = value.hex()

            json_data.append(record_dict)

        # Write to file
        filename = f"{table_name}.json"
        if compress:
            filename = f"{filename}.gz"

        output_file = output_dir / filename

        json_bytes = to_json(json_data)

        if compress:
            with gzip.open(output_file, "wb") as f:
                f.write(json_bytes)
        else:
            with output_file.open("wb") as f:
                f.write(json_bytes)

        return str(output_file)
