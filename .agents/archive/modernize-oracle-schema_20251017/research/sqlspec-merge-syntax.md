# SQLSpec MERGE Syntax Research

**Date**: 2025-10-17
**Source**: `/home/cody/code/litestar/sqlspec/sqlspec/builder/_merge.py`
**Test Examples**: `/home/cody/code/litestar/sqlspec/tests/unit/test_sql_factory.py`

## Overview

SQLSpec's `merge()` function provides a fluent API for building SQL MERGE (UPSERT) statements with proper parameter binding.

## Method Signatures

### `merge(target_table: str)` → `Merge`
Creates a MERGE builder targeting the specified table.

### `.using(source, alias=None)` → `Self`
Specifies the source table or subquery for the MERGE operation.

**Arguments**:
- `source`: Can be:
  - String (table name): `"new_users"`
  - Dict (inline values): `{"name": "John", "email": "john@test.com"}`
  - QueryBuilder (subquery)
  - Expression
- `alias`: Optional table alias

### `.on(condition: str | exp.Expression)` → `Self`
Specifies the join condition between target and source.

**CRITICAL**: The `.on()` method takes a **single string argument** containing the **entire condition expression**, NOT separate column/value pairs.

**Correct Usage**:
```python
.on("target_table.id = source_table.id")
```

**INCORRECT Usage** (This is what was causing the error):
```python
.on("id", value)  # ❌ WRONG - takes only 1 positional argument
```

### `.when_matched_then_update(set_values=None, condition=None, **assignments)` → `Self`
Specifies what to do when a match is found.

**Arguments**:
- `set_values`: Optional dict of column → value mappings
- `condition`: Optional WHERE condition for the UPDATE
- `**assignments`: Keyword arguments for column updates

### `.when_not_matched_then_insert(columns=None, values=None, **value_kwargs)` → `Self`
Specifies what to do when no match is found.

**Arguments**:
- `columns`: Can be:
  - Mapping (dict): `{"name": "John", "email": "john@test.com"}`
  - Sequence of column names: `["name", "email"]`
- `values`: Sequence of values (required if columns is a sequence)
- `**value_kwargs`: Keyword arguments for column values

## Complete Working Examples from Tests

### Example 1: Basic MERGE with Dict-style INSERT
```python
query = (
    sql.merge("users")
    .using("new_users")
    .on("users.id = new_users.id")  # Single string condition
    .when_matched_then_update(name="Updated John", email="updated@test.com")
    .when_not_matched_then_insert(
        name="new_users.name",
        email="new_users.email",
        created_at=sql.raw("NOW()")
    )
)
stmt = query.build()
```

### Example 2: MERGE with Inline Source Data (Dict)
```python
# When source is a dict, SQLSpec generates a SELECT from DUAL
source_data = {"id": 1, "name": "John", "email": "john@test.com"}

query = (
    sql.merge("users")
    .using(source_data, alias="source")
    .on("users.id = source.id")  # Reference the alias
    .when_matched_then_update(
        name="source.name",
        email="source.email",
        updated_at=sql.raw("NOW()")
    )
    .when_not_matched_then_insert(
        id="source.id",
        name="source.name",
        email="source.email",
        created_at=sql.raw("NOW()")
    )
)
stmt = query.build()
```

### Example 3: Full MERGE with All Clauses
```python
query = (
    sql.merge("users")
    .using("new_users")
    .on("users.id = new_users.id")
    .when_matched_then_update(
        name="new_users.name",
        email="new_users.email",
        updated_at=sql.raw("NOW()")
    )
    .when_not_matched_then_insert(
        ["id", "name", "email", "created_at"],
        ["new_users.id", "new_users.name", "new_users.email", sql.raw("NOW()")]
    )
    .when_not_matched_by_source_then_update(
        status="archived",
        archived_at=sql.raw("NOW()")
    )
)
stmt = query.build()
```

## Fix for fixtures.py

### Original Incorrect Code (Lines 215-220)
```python
merge_query = (
    sql.merge(table_name)
    .on("id", processed_record["id"])  # ❌ WRONG SIGNATURE
    .when_matched_update(**processed_record)  # ❌ WRONG METHOD NAME
    .when_not_matched_insert(**processed_record)  # ❌ WRONG METHOD NAME
)
```

### Corrected Code
```python
# Use dict as source (generates SELECT from DUAL in Oracle)
merge_query = (
    sql.merge(table_name)
    .using(processed_record, alias="source")
    .on(f"{table_name}.id = source.id")  # Single string condition
    .when_matched_then_update(**processed_record)  # Correct method name
    .when_not_matched_then_insert(**processed_record)  # Correct method name
)
```

## Key Findings

1. **`.on()` signature**: Takes a single string containing the full join condition
2. **Method names**:
   - Use `when_matched_then_update()` NOT `when_matched_update()`
   - Use `when_not_matched_then_insert()` NOT `when_not_matched_insert()`
3. **`.using()` with dict**: When passing a dict as source, SQLSpec automatically:
   - Creates a `SELECT ... FROM DUAL` subquery (Oracle)
   - Parameterizes all values
   - Requires an alias to reference in `.on()` condition
4. **Parameter binding**: All values are automatically parameterized with unique names

## Oracle-Specific Considerations

- Oracle uses `MERGE INTO target USING source ON condition` syntax
- When source is a dict, SQLSpec generates: `SELECT :val1 as col1, :val2 as col2 FROM DUAL`
- DUAL is Oracle's dummy table for SELECT without a real source table
- The generated SQL is fully parameterized for security and performance

## References

- SQLSpec merge implementation: `/home/cody/code/litestar/sqlspec/sqlspec/builder/_merge.py`
- Test examples: `/home/cody/code/litestar/sqlspec/tests/unit/test_sql_factory.py` (lines 1373-1524)
- Oracle MERGE documentation: https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/MERGE.html
