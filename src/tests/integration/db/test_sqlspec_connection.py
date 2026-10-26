# SPDX-FileCopyrightText: 2026 Google LLC
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
    """Parameterized SQLSpec `select_one_or_none` test case."""

    sql: str
    params: dict[str, Any]
    assert_result: Callable[[Any], None]


def _assert_basic_select(result: Any) -> None:
    """Assert basic scalar select result."""
    assert result is not None
    assert result["test_value"] == 1


def _assert_dict_access(result: Any) -> None:
    """Assert dictionary access across string, integer, and float projections."""
    assert result is not None
    assert result["str_value"] == "test"
    assert result["int_value"] == 123
    assert result["float_value"] == 45.67


def _assert_parameter_binding(result: Any) -> None:
    """Assert named parameter binding returns the bound value."""
    assert result is not None
    assert result["value"] == "test_value"


async def test_driver_connection(driver: OracleAsyncDriver) -> None:
    """Test that SQLSpec driver connects successfully."""
    assert driver is not None
    assert hasattr(driver, "select")
    assert hasattr(driver, "execute")


@pytest.mark.parametrize(
    "case",
    [
        SelectCase(sql="SELECT 1 as test_value FROM dual", params={}, assert_result=_assert_basic_select),
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
async def test_select_one_cases(driver: OracleAsyncDriver, case: SelectCase) -> None:
    """Exercise representative SQLSpec `select_one_or_none` result contracts."""
    result = await driver.select_one_or_none(case.sql, **case.params)
    case.assert_result(result)


async def test_select_multiple_rows(driver: OracleAsyncDriver) -> None:
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
    for i, row in enumerate(results, 1):
        assert row["row_num"] == i


async def test_execute_with_rowcount(driver: OracleAsyncDriver) -> None:
    """Test execute returns SQLResult with `rows_affected`."""
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

    result = await driver.execute("INSERT INTO test_sqlspec_tmp (id, value) VALUES (:id, :value)", id=1, value="test")
    assert result.rows_affected == 1
    await driver.execute("DROP TABLE test_sqlspec_tmp")


async def test_transaction_support(driver: OracleAsyncDriver) -> None:
    """Test transaction begin/commit/rollback support."""
    assert hasattr(driver, "begin")
    assert hasattr(driver, "commit")
    assert hasattr(driver, "rollback")


async def test_oracle_vector_type_support(driver: OracleAsyncDriver) -> None:
    """Test that Oracle VECTOR type is supported."""
    result = await driver.select_one_or_none(
        """
        SELECT column_name, data_type
        FROM user_tab_columns
        WHERE table_name = 'PRODUCT'
        AND column_name = 'EMBEDDING'
        """
    )

    if result:
        assert result["column_name"] == "EMBEDDING"
        assert "VECTOR" in result["data_type"].upper() or result["data_type"].upper() == "CLOB"


async def test_oracle_merge_statement_support(driver: OracleAsyncDriver) -> None:
    """Test that Oracle MERGE statements work."""
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

    result = await driver.select_one_or_none("SELECT value FROM test_merge_tmp WHERE id = :id", id=1)
    assert result is not None
    assert result["value"] == "first"

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

    result = await driver.select_one_or_none("SELECT value FROM test_merge_tmp WHERE id = :id", id=1)
    assert result is not None
    assert result["value"] == "updated"

    await driver.execute("DROP TABLE test_merge_tmp")


async def test_insert_and_fetch_generated_identity(driver: OracleAsyncDriver) -> None:
    """Test identity insert by selecting the generated row."""
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
    insert_result = await driver.execute("INSERT INTO test_returning_tmp (value) VALUES (:value)", value=value)
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

    await driver.execute("DROP TABLE test_returning_tmp")


async def test_oracle_schema_annotations(driver: OracleAsyncDriver) -> None:
    """Verify that Oracle 26ai schema annotations are correctly created and queryable."""
    annotations = await driver.select(
        """
        SELECT object_name,
               object_type,
               column_name,
               annotation_name,
               annotation_value
        FROM user_annotations_usage
        WHERE object_name IN (
            'PRODUCT',
            'STORE',
            'STORE_PRODUCT_INVENTORY',
            'EMBEDDING_CACHE',
            'PRODUCT_IN_STOCK_IDX'
        )
        ORDER BY object_name, column_name, annotation_name
        """
    )

    assert len(annotations) > 0

    annotation_map: dict[tuple[str, str | None, str], Any] = {}
    for row in annotations:
        obj_name = row["object_name"].upper()
        col_name = row["column_name"].upper() if row["column_name"] else None
        ann_name = row["annotation_name"].upper()
        ann_val = row["annotation_value"]

        key = (obj_name, col_name, ann_name)
        annotation_map[key] = ann_val

    assert annotation_map.get(("PRODUCT", None, "DISPLAY")) == "Cymbal Coffee products"
    assert annotation_map.get(("PRODUCT", None, "AI_SURFACE")) == "PRODUCT_RAG"
    assert annotation_map.get(("STORE", None, "DISPLAY")) == "Cymbal Coffee stores"

    assert annotation_map.get(("PRODUCT", "EMBEDDING", "EMBEDDING_MODEL")) == "gemini-embedding-2"
    assert annotation_map.get(("PRODUCT", "EMBEDDING", "EMBEDDING_DIMENSIONS")) == "3072"
    assert annotation_map.get(("PRODUCT", "EMBEDDING", "EMBEDDING_PURPOSE")) == "document"
    assert annotation_map.get(("EMBEDDING_CACHE", "EMBEDDING", "EMBEDDING_MODEL")) == "gemini-embedding-2"
    assert (
        annotation_map.get(("STORE_PRODUCT_INVENTORY", "STOCK_STATUS", "ENUM_VALUES"))
        == "IN_STOCK, LOW_STOCK, OUT_OF_STOCK"
    )

    assert annotation_map.get(("PRODUCT_IN_STOCK_IDX", None, "DISPLAY")) == "Product stock lookup"


async def test_clob_inline_string_materialization_across_select_and_stream(driver: OracleAsyncDriver) -> None:
    """Verify SQLSpec 0.69.0 default fetch_lobs=False materializes CLOB columns as str in select and select_stream."""
    query = "SELECT TO_CLOB('cortado') AS clob_col FROM dual"
    selected = await driver.select(query)
    assert len(selected) == 1
    assert isinstance(selected[0]["clob_col"], str)
    assert selected[0]["clob_col"] == "cortado"

    streamed_rows: list[dict[str, Any]] = [row async for row in driver.select_stream(query)]
    assert len(streamed_rows) == 1
    assert isinstance(streamed_rows[0]["clob_col"], str)
    assert streamed_rows[0]["clob_col"] == "cortado"
