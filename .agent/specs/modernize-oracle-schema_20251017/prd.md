# Product Requirements Document: Modernize Oracle Schema & Fix Data Model Parity

**Requirement Slug**: `modernize-oracle-schema`
**Created**: 2025-10-17
**Status**: Planning
**Priority**: High
**Estimated Effort**: 2-3 hours

---

## Executive Summary

The Oracle version of the coffee shop demo is missing the `store` table and uses outdated Oracle data type patterns (e.g., `NUMBER(1)` for booleans). This causes fixture loading failures and diverges from the PostgreSQL reference implementation. We need to:

1. Add the missing `store` table to match PostgreSQL schema
2. Modernize all data types to use Oracle 23ai native features (BOOLEAN, JSON/OSON, VECTOR, etc.)
3. Ensure schema parity between Oracle and PostgreSQL implementations
4. Update fixture loading to work with the new schema
5. Verify all CLI commands work correctly

---

## Problem Statement

### Current Issues

1. **Missing Store Table**
   - PostgreSQL has a full `store` table for coffee shop locations
   - Oracle schema completely lacks this table
   - Fixture loading fails: `uv run app db load-fixtures` errors on store.json.gz
   - User cannot test location-based features

2. **Outdated Data Types**
   - Using `NUMBER(1) CHECK (column IN (0, 1))` instead of native `BOOLEAN`
   - Using generic `JSON` without understanding Oracle's OSON binary format
   - Inconsistent with Oracle 23ai best practices

3. **Schema Divergence**
   - Oracle and PostgreSQL schemas have different table sets
   - Makes cross-database feature parity difficult
   - Complicates maintenance and testing

4. **CLI Command Issues**
   - `load-fixtures` command was just added but fails due to missing tables
   - Error: `ORA-03048: SQL reserved word 'ON' is not syntactically valid`
   - Sequence reset logic may not be optimal for Oracle

---

## Goals & Success Criteria

### Goals

1. **Achieve Schema Parity**: Oracle schema matches PostgreSQL feature set
2. **Use Modern Types**: Leverage Oracle 23ai native BOOLEAN, optimized JSON (OSON), and VECTOR types
3. **Fix Fixture Loading**: All fixtures load successfully without errors
4. **Maintain Compatibility**: Existing application code continues to work
5. **Document Changes**: Clear migration guide for future schema updates

### Success Criteria

- [ ] `uv run app db load-fixtures` completes successfully for all tables
- [ ] `store` table exists with all columns from PostgreSQL version
- [ ] All boolean columns use native `BOOLEAN` type
- [ ] Migration can be run on clean database: `uv run app db upgrade head`
- [ ] Downgrade works: `uv run app db downgrade base`
- [ ] Application starts and serves requests successfully
- [ ] All integration tests pass
- [ ] Documentation updated with new schema details

---

## Technical Design

### Research Summary

Based on Oracle 23ai feature research (see `specs/active/oracle-23ai-features/`):

| Feature | Old Pattern | New Pattern (Oracle 23ai) |
|---------|-------------|---------------------------|
| **Boolean** | `NUMBER(1) CHECK (column IN (0,1))` | `BOOLEAN` (native type) |
| **JSON** | `JSON` (understood now as OSON) | `JSON` (keep, it's already binary) |
| **Auto-increment** | `NUMBER GENERATED ALWAYS AS IDENTITY` | Keep (correct pattern) |
| **Timestamp** | `TIMESTAMP` | `TIMESTAMP WITH TIME ZONE` |
| **Vector** | `VECTOR(768, FLOAT32)` | Keep (optimal for Vertex AI) |

### Schema Changes Required

#### 1. Add Store Table

```sql
CREATE TABLE store (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    address VARCHAR2(500) NOT NULL,  -- VARCHAR2, not CLOB
    city VARCHAR2(100),
    state VARCHAR2(50),
    zip VARCHAR2(20),
    phone VARCHAR2(50),
    hours JSON,  -- Store hours: {"monday": "7am-9pm", ...}
    metadata JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE store IS 'Coffee shop store locations';
COMMENT ON COLUMN store.hours IS 'Business hours by day: {"monday": "7am-9pm", ...}';

-- Indexes for location queries
CREATE INDEX store_city_idx ON store (city);
CREATE INDEX store_state_idx ON store (state);
CREATE INDEX store_zip_idx ON store (zip);

-- Trigger for updated_at
CREATE OR REPLACE TRIGGER store_updated_at_trg
BEFORE UPDATE ON store
FOR EACH ROW
BEGIN
    :NEW.updated_at := CURRENT_TIMESTAMP;
END;
```

#### 2. Modernize Boolean Columns

Update these tables to use native BOOLEAN:
- `product.in_stock`: `NUMBER(1)` → `BOOLEAN`
- `search_metric.embedding_cache_hit`: `NUMBER(1)` → `BOOLEAN`
- `search_metric.vector_search_cache_hit`: `NUMBER(1)` → `BOOLEAN`

#### 3. Upgrade Timestamp Columns

Change all `TIMESTAMP` to `TIMESTAMP WITH TIME ZONE` for proper UTC handling:
- `product.{created_at, updated_at}`
- `response_cache.{expires_at, created_at}`
- `embedding_cache.{last_accessed, created_at}`
- `intent_exemplar.{created_at, updated_at}`
- `search_metric.created_at`
- `store.{created_at, updated_at}` (new table)

#### 4. Verify JSON Storage

Confirm `JSON` columns are using OSON (Oracle's binary JSON format):
- `product.metadata`
- `response_cache.response_data`
- `store.hours`
- `store.metadata`

**Action**: No changes needed - Oracle 23ai's `JSON` type automatically uses OSON.

---

## Implementation Plan

### Phase 1: Update Existing Migration (30 min)

**Strategy**: Update `app/db/migrations/0001_initial_schema.sql` in-place, then wipe database and reload.

1. **Update Migration File**: `app/db/migrations/0001_initial_schema.sql`
2. **Add Store Table**:
   - Add `store` table with all columns
   - Use `VARCHAR2(500)` for address (NOT CLOB)
   - Add indexes and triggers for `store`
3. **Modernize Existing Tables**:
   - Change `NUMBER(1)` to `BOOLEAN` for boolean columns
   - Change `TIMESTAMP` to `TIMESTAMP WITH TIME ZONE` for all timestamp columns
4. **Test Migration**:
   - Wipe database: `uv run app db downgrade base`
   - Run migration: `uv run app db upgrade head`
   - Verify all tables created

### Phase 2: Update Fixture Table Order (10 min)

Update `app/db/utils.py`:

```python
COFFEE_SHOP_TABLES = [
    "store",           # New table (no dependencies)
    "product",
    "embedding_cache",
    "response_cache",
    "intent_exemplar",
    "search_metric",
]
```

### Phase 3: Update Application Code for Booleans (20 min)

Review and update any code that reads/writes boolean columns:

**Files to check**:
- `app/services/product.py` - `in_stock` handling
- `app/services/metrics.py` - cache hit flags
- Any fixtures or seed data generation

**Python boolean handling**:
```python
# Oracle 23ai with python-oracledb 2.x automatically handles:
product = {"in_stock": True}  # Python bool → Oracle BOOLEAN
# Fetching:
is_in_stock = row["in_stock"]  # Oracle BOOLEAN → Python bool
```

### Phase 4: Test Fixture Loading (20 min)

1. **Clear Database**: `uv run app db downgrade base`
2. **Run Migrations**: `uv run app db upgrade head`
3. **Load Fixtures**: `uv run app db load-fixtures`
4. **Verify Data**:
   - Check `store` table: `SELECT COUNT(*) FROM store;` (expect 15 rows)
   - Check boolean columns: `SELECT in_stock FROM product WHERE id = 1;` (expect `TRUE` or `1`)
   - Check timestamps: `SELECT created_at FROM store WHERE id = 1;` (expect timezone info)

### Phase 5: Update Documentation (30 min)

1. **Update Schema Docs**: Document new `store` table
2. **Update Migration Guide**: Add notes on Oracle 23ai types
3. **Update README**: Mention boolean type usage
4. **Create Schema Comparison**: Document Oracle vs PostgreSQL parity

### Phase 6: Integration Testing (30 min)

1. **Start Application**: `uv run app run`
2. **Test Endpoints**:
   - Product search (uses embeddings)
   - Store locator (if implemented)
   - Cache operations
3. **Run Test Suite**: `uv run pytest tests/integration/`
4. **Verify Metrics**: Check `search_metric` table records correctly

---

## Migration Strategy

### Safe Migration Path

**For existing deployments**:

1. **Backup**: Always backup before schema changes
2. **Test Locally**: Run full migration on dev database first
3. **Staged Rollout**:
   - Stage 1: Add new tables/columns (non-breaking)
   - Stage 2: Migrate data to new types
   - Stage 3: Remove old columns (if any)
4. **Rollback Plan**: Test downgrade path before production

### Handling Data Migration

**Boolean column migration** (if data exists):

```sql
-- Step 1: Add new column
ALTER TABLE product ADD in_stock_new BOOLEAN;

-- Step 2: Migrate data
UPDATE product SET in_stock_new = CASE WHEN in_stock = 1 THEN TRUE ELSE FALSE END;

-- Step 3: Drop old, rename new
ALTER TABLE product DROP COLUMN in_stock;
ALTER TABLE product RENAME COLUMN in_stock_new TO in_stock;
```

**Note**: Since this is a demo app with fixture data, we can simply recreate the database.

---

## Dependencies & Prerequisites

### Required

- [x] Oracle 23ai Free Edition running
- [x] python-oracledb 2.x installed (check: `pip show python-oracledb`)
- [x] SQLSpec migrations framework configured
- [x] Fixture files: `app/db/fixtures/store.json.gz` (already exists)

### Research Complete

- [x] Oracle 23ai BOOLEAN type verified (native support)
- [x] JSON/OSON storage format documented
- [x] VECTOR type best practices confirmed
- [x] Migration patterns researched

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing queries | High | Review all SQL queries for boolean comparisons |
| Python boolean binding issues | Medium | Test with python-oracledb 2.x; verify driver version |
| Fixture loading still fails | High | Test migration before fixture loading; validate table structure |
| Performance regression | Low | Use same indexing strategy as before |
| Sequence reset issues | Medium | Update `_reset_sequences()` to handle new store table |

---

## Testing Plan

### Unit Tests

- [ ] Test boolean column reads/writes in `ProductService`
- [ ] Test JSON storage in `store` table
- [ ] Test timestamp timezone handling

### Integration Tests

- [ ] Test fixture loading: `test_load_fixtures_success()`
- [ ] Test store CRUD operations
- [ ] Test product search with embeddings
- [ ] Test cache operations with boolean flags

### Manual Testing

- [ ] Load all fixtures successfully
- [ ] Query store table data
- [ ] Verify boolean columns show as TRUE/FALSE
- [ ] Check timestamps display correctly
- [ ] Test application startup

---

## Rollback Plan

If migration fails or causes issues:

1. **Downgrade Database**: `uv run app db downgrade 0001`
2. **Review Logs**: Check migration error messages
3. **Fix Migration**: Update SQL script based on errors
4. **Re-test**: Run upgrade again on clean database
5. **If Critical**: Restore from backup

---

## Documentation Updates

### Files to Update

1. **`docs/guides/schema-design.md`** (create if missing)
   - Document complete Oracle schema
   - Explain Oracle 23ai type choices
   - Compare with PostgreSQL schema

2. **`docs/guides/autonomous-database-setup.md`**
   - Add note about Oracle 23ai feature requirements
   - Mention boolean type support

3. **`README.md`**
   - Update schema section
   - Mention modernized types

4. **`app/db/migrations/README.md`**
   - Document migration 0002
   - Explain type modernization

---

## Future Enhancements

- [ ] Add `vector_search_cache` table (like PostgreSQL)
- [ ] Add chat session tables if ADK doesn't provide
- [ ] Consider adding spatial indexes for store locations
- [ ] Evaluate HNSW indexes for better vector search performance
- [ ] Add database constraints for data integrity

---

## References

- [Oracle 23ai Research](specs/active/oracle-23ai-features/SUMMARY.md)
- [Oracle 23ai Migration Guide](specs/active/oracle-23ai-features/MIGRATION-GUIDE.md)
- [PostgreSQL Schema](../postgres-vertexai-demo/app/db/migrations/0001_initial_schema_with_pgvector_support.sql)
- [SQLSpec Documentation](https://docs.litestar.dev/latest/usage/databases/sqlspec/)
