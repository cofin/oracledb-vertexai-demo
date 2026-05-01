# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for SQLSpec database connection and configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlspec.adapters.oracledb import OracleAsyncDriver

pytestmark = pytest.mark.anyio


@dataclass(frozen=True)
class SelectCase:
    sql: str
    params: dict[str, Any]
    assert_result: Callable[[Any], None]


def _assert_basic_select(result: Any) -> None:
    assert result is not None
    assert result["test_value"] == 1


def _assert_dict_access(result: Any) -> None:
    assert result is not None
    assert result["str_value"] == "test"
    assert result["int_value"] == 123
    assert result["float_value"] == 45.67


def _assert_parameter_binding(result: Any) -> None:
    assert result is not None
    assert result["value"] == "test_value"


class TestSQLSpecConnection:
    """Test suite for SQLSpec database connection and pool configuration."""

    async def test_driver_connection(self, driver: OracleAsyncDriver) -> None:
        """Test that SQLSpec driver connects successfully."""
        assert driver is not None
        assert hasattr(driver, "select")
        assert hasattr(driver, "execute")

    @pytest.mark.parametrize(
        "case",
        [
            SelectCase(
                sql="SELECT 1 as test_value FROM dual",
                params={},
                assert_result=_assert_basic_select,
            ),
            SelectCase(
                sql="""
                SELECT
                    'test' as str_value,
                    123 as int_value,
                    45.67 as float_value
                FROM dual
                """,
                params={},
                assert_result=_assert_dict_access,
            ),
            SelectCase(
                sql="SELECT :param1 as value FROM dual",
                params={"param1": "test_value"},
                assert_result=_assert_parameter_binding,
            ),
        ],
        ids=("basic-select", "dict-access", "parameter-binding"),
    )
    async def test_select_one_cases(self, driver: OracleAsyncDriver, case: SelectCase) -> None:
        """Exercise representative SQLSpec select_one_or_none result contracts."""
        result = await driver.select_one_or_none(case.sql, **case.params)
        case.assert_result(result)

    async def test_select_multiple_rows(self, driver: OracleAsyncDriver) -> None:
        """Test SELECT returning multiple rows."""
        results = await driver.select(
            """
            SELECT level as row_num
            FROM dual
            CONNECT BY level <= 5
            """
        )

        assert isinstance(results, list)
        assert len(results) == 5
        # Verify dict access for each row
        for i, row in enumerate(results, 1):
            assert row["row_num"] == i

    async def test_execute_with_rowcount(self, driver: OracleAsyncDriver) -> None:
        """Test execute returns SQLResult with rows_affected."""
        # Create a temp table for testing
        await driver.execute(
            """
            DECLARE
                table_exists NUMBER;
            BEGIN
                SELECT COUNT(*) INTO table_exists
                FROM user_tables
                WHERE table_name = 'TEST_SQLSPEC_TMP';

                IF table_exists > 0 THEN
                    EXECUTE IMMEDIATE 'DROP TABLE test_sqlspec_tmp';
                END IF;

                EXECUTE IMMEDIATE 'CREATE TABLE test_sqlspec_tmp (id NUMBER, value VARCHAR2(100))';
            END;
            """
        )

        # Insert and check rowcount
        result = await driver.execute(
            "INSERT INTO test_sqlspec_tmp (id, value) VALUES (:id, :value)",
            id=1,
            value="test",
        )

        assert result.rows_affected == 1

        # Cleanup
        await driver.execute("DROP TABLE test_sqlspec_tmp")

    async def test_transaction_support(self, driver: OracleAsyncDriver) -> None:
        """Test transaction begin/commit/rollback support."""
        # Verify transaction methods exist
        assert hasattr(driver, "begin")
        assert hasattr(driver, "commit")
        assert hasattr(driver, "rollback")

    async def test_oracle_vector_type_support(self, driver: OracleAsyncDriver) -> None:
        """Test that Oracle VECTOR type is supported."""
        # Check if we can query vector columns
        # This assumes the product table has embedding column
        result = await driver.select_one_or_none(
            """
            SELECT column_name, data_type
            FROM user_tab_columns
            WHERE table_name = 'PRODUCT'
            AND column_name = 'EMBEDDING'
            """
        )

        if result:
            # Verify VECTOR type is recognized
            assert result["column_name"] == "EMBEDDING"
            # Oracle 26ai uses VECTOR data type
            assert "VECTOR" in result["data_type"].upper() or result["data_type"].upper() == "CLOB"

    async def test_oracle_merge_statement_support(self, driver: OracleAsyncDriver) -> None:
        """Test that Oracle MERGE statements work."""
        # Create temp table
        await driver.execute(
            """
            DECLARE
                table_exists NUMBER;
            BEGIN
                SELECT COUNT(*) INTO table_exists
                FROM user_tables
                WHERE table_name = 'TEST_MERGE_TMP';

                IF table_exists > 0 THEN
                    EXECUTE IMMEDIATE 'DROP TABLE test_merge_tmp';
                END IF;

                EXECUTE IMMEDIATE 'CREATE TABLE test_merge_tmp (id NUMBER PRIMARY KEY, value VARCHAR2(100))';
            END;
            """
        )

        # Test MERGE (upsert)
        await driver.execute(
            """
            MERGE INTO test_merge_tmp t
            USING (SELECT :id as id, :value as value FROM dual) s
            ON (t.id = s.id)
            WHEN MATCHED THEN
                UPDATE SET t.value = s.value
            WHEN NOT MATCHED THEN
                INSERT (id, value) VALUES (s.id, s.value)
            """,
            id=1,
            value="first",
        )

        # Verify insert
        result = await driver.select_one_or_none(
            "SELECT value FROM test_merge_tmp WHERE id = :id",
            id=1,
        )
        assert result["value"] == "first"

        # Update via MERGE
        await driver.execute(
            """
            MERGE INTO test_merge_tmp t
            USING (SELECT :id as id, :value as value FROM dual) s
            ON (t.id = s.id)
            WHEN MATCHED THEN
                UPDATE SET t.value = s.value
            WHEN NOT MATCHED THEN
                INSERT (id, value) VALUES (s.id, s.value)
            """,
            id=1,
            value="updated",
        )

        # Verify update
        result = await driver.select_one_or_none(
            "SELECT value FROM test_merge_tmp WHERE id = :id",
            id=1,
        )
        assert result["value"] == "updated"

        # Cleanup
        await driver.execute("DROP TABLE test_merge_tmp")

    async def test_insert_and_fetch_generated_identity(self, driver: OracleAsyncDriver) -> None:
        """Test identity insert by selecting the generated row."""
        # Create temp table
        await driver.execute(
            """
            DECLARE
                table_exists NUMBER;
            BEGIN
                SELECT COUNT(*) INTO table_exists
                FROM user_tables
                WHERE table_name = 'TEST_RETURNING_TMP';

                IF table_exists > 0 THEN
                    EXECUTE IMMEDIATE 'DROP TABLE test_returning_tmp';
                END IF;

                EXECUTE IMMEDIATE 'CREATE TABLE test_returning_tmp (id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY, value VARCHAR2(100))';
            END;
            """
        )

        value = "test_returning"
        insert_result = await driver.execute(
            "INSERT INTO test_returning_tmp (value) VALUES (:value)",
            value=value,
        )
        assert insert_result.rows_affected == 1

        result = await driver.select_one_or_none(
            """
            SELECT id, value
            FROM test_returning_tmp
            WHERE value = :value
            ORDER BY id DESC
            FETCH FIRST 1 ROW ONLY
            """,
            value=value,
        )

        assert result is not None
        assert "id" in result
        assert result["id"] > 0
        assert result["value"] == value

        # Cleanup
        await driver.execute("DROP TABLE test_returning_tmp")
