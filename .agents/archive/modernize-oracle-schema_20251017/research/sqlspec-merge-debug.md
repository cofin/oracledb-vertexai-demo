# SQLSpec MERGE Debugging

**Date**: 2025-10-17
**Issue**: ORA-00969: missing ON keyword error when using sql.merge()

## Root Cause

The fixture loader code was attempting to use SQLSpec's `merge()` builder incorrectly:

```python
# INCORRECT USAGE (current code)
merge_query = (
    sql.merge(table_name)
    .using(processed_record, alias="source")  # ❌ Wrong: passing dict as table
    .on(f"{table_name}.id = source.id")      # ❌ Wrong: f-string with table reference
    .when_matched_then_update(**processed_record)
    .when_not_matched_then_insert(**processed_record)
)
```

### Issues Found:

1. **`.using()` signature mismatch**: The `.using()` method accepts a dict, but expects it to be used with DUAL (for Oracle-style inline values), not as a table reference with an alias.

2. **`.on()` condition issue**: When using a dict in `.using()`, the generated query tries to reference columns that don't exist in the subquery.

3. **Over-engineering**: For fixtures that load into a clean database, we don't need MERGE at all!

## Correct SQLSpec MERGE Usage

From `/home/cody/code/litestar/sqlspec/tests/unit/test_sql_factory.py`:

```python
# CORRECT: Merge between two tables
query = (
    sql.merge("users")
    .using("new_users")  # Table name as string
    .on("users.id = new_users.id")  # Simple condition string
    .when_matched_then_update(name="Updated", email="updated@test.com")
    .when_not_matched_then_insert(["id", "name"], ["new_users.id", "new_users.name"])
)
```

## Recommended Solution: Use INSERT Instead

Since fixtures load into a **clean database** (no existing rows), we should:

1. **Use simple INSERT** instead of MERGE
2. **Add error handling** for duplicates (optional, if running twice)
3. **Much simpler and faster**

### Correct Implementation:

```python
# Use simple insert for fixtures (clean DB)
insert_query = sql.insert(table_name).values(**processed_record)
await self.driver.execute(insert_query)
```

If we need upsert behavior (e.g., re-running fixtures):

```python
# Check if exists first, then insert or update
exists = await self._record_exists(table_name, processed_record.get("id"))
if exists:
    update_query = sql.update(table_name).set(processed_record).where_eq("id", processed_record["id"])
    await self.driver.execute(update_query)
else:
    insert_query = sql.insert(table_name).values(**processed_record)
    await self.driver.execute(insert_query)
```

Or use INSERT ... ON CONFLICT (PostgreSQL) / INSERT ... ON DUPLICATE KEY UPDATE (MySQL):

```python
# PostgreSQL-style upsert (if driver supports it)
insert_query = (
    sql.insert(table_name)
    .values(**processed_record)
    .on_conflict("id")
    .do_update(**{k: v for k, v in processed_record.items() if k != "id"})
)
await self.driver.execute(insert_query)
```

## Recommendation

**Use simple INSERT** for fixture loading. The database is clean, so MERGE is unnecessary complexity.

If fixtures need to be idempotent (re-runnable), use the check-then-insert/update pattern shown above.

## References

- SQLSpec tests: `/home/cody/code/litestar/sqlspec/tests/unit/test_sql_factory.py` (lines 1373-1523)
- SQLSpec merge implementation: `/home/cody/code/litestar/sqlspec/sqlspec/builder/_merge.py`
