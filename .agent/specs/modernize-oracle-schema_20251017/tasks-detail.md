# Detailed Task Breakdown: Modernize Oracle Schema

**Requirement**: modernize-oracle-schema
**Created**: 2025-10-17

---

## Phase 1: Update Existing Migration (30 min)

### Task 1.1: Edit Migration File In-Place
**Estimated**: 5 minutes

**File to edit**:
- `app/db/migrations/0001_initial_schema.sql`

**Strategy**:
- Add store table after product table
- Change all `NUMBER(1)` to `BOOLEAN`
- Change all `TIMESTAMP` to `TIMESTAMP WITH TIME ZONE`
- Update downgrade script to drop store table
- **Use `VARCHAR2(500)` for address, NOT CLOB**

### Task 1.2: Write Store Table Creation SQL
**Estimated**: 10 minutes

**Add this after the product table section (line ~26)**:

```sql
-- Store locations for coffee shop finder
CREATE TABLE store (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    address VARCHAR2(500) NOT NULL,  -- VARCHAR2, NOT CLOB
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
COMMENT ON COLUMN store.hours IS 'Business hours by day';

-- Store indexes for location queries
CREATE INDEX store_city_idx ON store (city);
CREATE INDEX store_state_idx ON store (state);
CREATE INDEX store_zip_idx ON store (zip);
```

### Task 1.3: Modernize Boolean Columns
**Estimated**: 5 minutes

**Since we're updating in-place and wiping the database, just change the definitions**:

**In product table (line ~16)**:
```sql
-- Old
in_stock NUMBER(1) DEFAULT 1 CHECK (in_stock IN (0, 1)),

-- New
in_stock BOOLEAN DEFAULT TRUE,
```

**Remove comment**: Delete line 25 `COMMENT ON COLUMN product.in_stock IS 'Boolean: 1=in stock, 0=out of stock';`

**In search_metric table (lines ~87-88)**:
```sql
-- Old
embedding_cache_hit NUMBER(1) DEFAULT 0 CHECK (embedding_cache_hit IN (0, 1)),
vector_search_cache_hit NUMBER(1) DEFAULT 0 CHECK (vector_search_cache_hit IN (0, 1)),

-- New
embedding_cache_hit BOOLEAN DEFAULT FALSE,
vector_search_cache_hit BOOLEAN DEFAULT FALSE,
```

### Task 1.4: Modernize Timestamp Columns
**Estimated**: 5 minutes

**Since we're updating in-place and wiping the database, use find/replace**:

**Find and replace across the file**:
```sql
-- Old
TIMESTAMP DEFAULT SYSTIMESTAMP

-- New
TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
```

**Tables affected**:
- `product` (created_at, updated_at) - lines ~19-20
- `response_cache` (expires_at, created_at) - lines ~33-34
- `embedding_cache` (last_accessed, created_at) - lines ~48-49
- `intent_exemplar` (created_at, updated_at) - lines ~66-67
- `search_metric` (created_at) - line ~91
- `store` (created_at, updated_at) - already done if using SQL from Task 1.2

**Also update triggers to use CURRENT_TIMESTAMP**:
```sql
-- Old (line ~162)
:NEW.updated_at := SYSTIMESTAMP;

-- New
:NEW.updated_at := CURRENT_TIMESTAMP;
```

### Task 1.5: Update Downgrade Script
**Estimated**: 3 minutes

**Add to downgrade section (line ~173, before "-- Drop triggers")**:

```sql
-- Drop store trigger
DROP TRIGGER IF EXISTS store_updated_at_trg;
```

**Add to downgrade section (line ~220, before "-- Drop vector indexes")**:

```sql
-- Drop store indexes
DROP INDEX IF EXISTS store_zip_idx;
DROP INDEX IF EXISTS store_state_idx;
DROP INDEX IF EXISTS store_city_idx;
```

**Add to downgrade section (line ~231, after "DROP TABLE IF EXISTS product")**:

```sql
DROP TABLE IF EXISTS store PURGE;
```

---

## Phase 2: Application Code Updates (20 min)

### Task 2.1: Update Fixture Table Order
**Estimated**: 2 minutes

**File**: `app/db/utils.py`

**Change**:
```python
COFFEE_SHOP_TABLES = [
    "store",           # ADD THIS
    "product",
    "embedding_cache",
    "response_cache",
    "intent_exemplar",
    "search_metric",
]
```

**Also update `_reset_sequences()` tables_with_sequences list**:
```python
tables_with_sequences = [
    "store",           # ADD THIS
    "product",
    "response_cache",
    "embedding_cache",
    "intent_exemplar",
    "search_metric",
]
```

### Task 2.2: Review Product Service Boolean Handling
**Estimated**: 5 minutes

**File**: `app/services/product.py`

**Check for**:
- SQL queries with `WHERE in_stock = 1` → change to `WHERE in_stock = TRUE`
- INSERT statements with `in_stock` values
- SELECT statements reading `in_stock`

**Verify python-oracledb binding**:
```python
# Should work automatically with python-oracledb 2.x:
{"in_stock": True}  # Python bool → Oracle BOOLEAN
```

### Task 2.3: Review Metrics Service Boolean Handling
**Estimated**: 5 minutes

**File**: `app/services/metrics.py`

**Check for**:
- `embedding_cache_hit` and `vector_search_cache_hit` usage
- SQL queries comparing cache hit flags
- INSERT/UPDATE statements for metrics

### Task 2.4: Search for Hardcoded Boolean Values
**Estimated**: 5 minutes

**Commands to run**:
```bash
# Find SQL queries with = 1 or = 0 for boolean checks
rg "in_stock\s*=\s*[01]" app/
rg "cache_hit\s*=\s*[01]" app/
rg "CHECK.*IN.*\(0.*1\)" app/
```

**Update any findings** to use TRUE/FALSE instead.

### Task 2.5: Update Sequence Reset Logic
**Estimated**: 3 minutes

**File**: `app/db/utils.py`

**Already done in Task 2.1**, but verify:
- Store table is in `tables_with_sequences`
- Sequence naming convention matches: `store_id_seq`

---

## Phase 3: Testing & Verification (30 min)

### Task 3.1: Test Migration Upgrade Path
**Estimated**: 5 minutes

**Commands**:
```bash
# Start from clean slate
uv run app db downgrade base

# Apply 0001 migration
uv run app db upgrade 0001
uv run app db show-current-revision
# Expected: 0001

# Apply 0002 migration
uv run app db upgrade 0002
uv run app db show-current-revision
# Expected: 0002
```

**Verify**:
- No SQL errors during upgrade
- All objects created successfully

### Task 3.2: Test Migration Downgrade Path
**Estimated**: 5 minutes

**Commands**:
```bash
# Downgrade from 0002 to 0001
uv run app db downgrade 0001
uv run app db show-current-revision
# Expected: 0001

# Verify store table is gone
# Should error: SELECT COUNT(*) FROM store;

# Upgrade again to test repeatability
uv run app db upgrade 0002
```

### Task 3.3: Test Fixture Loading
**Estimated**: 5 minutes

**Commands**:
```bash
# Ensure we're on latest migration
uv run app db upgrade head

# List available fixtures
uv run app db load-fixtures --list

# Load all fixtures
uv run app db load-fixtures

# Expected: All tables load successfully, 0 failed
```

### Task 3.4: Verify Store Table Data
**Estimated**: 3 minutes

**Queries to run** (via SQLcl or python):
```sql
-- Check row count
SELECT COUNT(*) FROM store;
-- Expected: 15 rows

-- Check sample data
SELECT id, name, city, state FROM store WHERE id = 1;
-- Expected: "Cymbal Coffee Downtown", "San Francisco", "CA"

-- Check JSON column
SELECT JSON_VALUE(hours, '$.monday') AS monday_hours FROM store WHERE id = 1;
-- Expected: "6:30am-8pm" or similar
```

### Task 3.5: Verify Boolean Columns
**Estimated**: 3 minutes

**Queries**:
```sql
-- Check product boolean
SELECT id, name, in_stock FROM product WHERE id = 1;
-- Expected: in_stock = TRUE (or displayed as 1)

-- Insert new product with boolean
INSERT INTO product (name, in_stock) VALUES ('Test Product', FALSE);
SELECT in_stock FROM product WHERE name = 'Test Product';
-- Expected: FALSE
```

### Task 3.6: Verify Timestamp Columns
**Estimated**: 3 minutes

**Queries**:
```sql
-- Check timezone info
SELECT created_at FROM store WHERE id = 1;
-- Expected: timestamp with timezone offset (e.g., "2025-01-01 00:00:00.000000 +00:00")

-- Check current_timestamp works
INSERT INTO store (name, address) VALUES ('Test Store', '123 Test St');
SELECT created_at FROM store WHERE name = 'Test Store';
-- Expected: Recent timestamp with timezone
```

### Task 3.7: Run Integration Tests
**Estimated**: 5 minutes

**Commands**:
```bash
# Run full integration test suite
uv run pytest tests/integration/ -v

# Specifically check:
# - test_load_fixtures_success
# - test_product_crud
# - test_vector_search
# - test_cache_operations
```

### Task 3.8: Test Application Startup
**Estimated**: 1 minute

**Commands**:
```bash
# Start the application
uv run app run

# Expected: Application starts without errors
# Check logs for any schema-related warnings
```

---

## Phase 4: Documentation (30 min)

### Task 4.1: Update Migration README
**Estimated**: 8 minutes

**File**: `app/db/migrations/README.md`

**Add section**:
```markdown
## Migration 0002: Add Store Table and Modernize Types

**Date**: 2025-10-17
**Breaking Change**: Yes (requires database rebuild or careful migration)

### Changes
- Added `store` table for coffee shop locations
- Modernized boolean columns to use Oracle 23ai native `BOOLEAN` type
- Upgraded timestamp columns to use `TIMESTAMP WITH TIME ZONE`

### Upgrade Impact
- Boolean columns: `in_stock`, `embedding_cache_hit`, `vector_search_cache_hit`
- Timestamp columns: All created_at/updated_at fields

### Rollback Plan
- Downgrade to 0001 will revert all changes
- Data in store table will be lost on downgrade
```

### Task 4.2: Create Schema Design Guide
**Estimated**: 12 minutes

**File**: `docs/guides/schema-design.md` (create if missing)

**Sections**:
1. **Overview** - Database schema purpose
2. **Tables** - Document each table with:
   - Purpose
   - Columns and types
   - Indexes
   - Foreign keys (if any)
3. **Oracle 23ai Features** - Explain type choices:
   - BOOLEAN vs NUMBER(1)
   - JSON/OSON binary storage
   - VECTOR types for embeddings
   - TIMESTAMP WITH TIME ZONE for UTC
4. **Schema Parity** - Compare with PostgreSQL:
   - Tables present in both
   - Type equivalents
   - Index strategies

### Task 4.3: Update Main README
**Estimated**: 5 minutes

**File**: `README.md`

**Updates**:
- Add note about Oracle 23ai features used
- Mention native BOOLEAN support requirement
- Update database schema section

**Example addition**:
```markdown
### Database Schema

This application uses Oracle 23ai native features:
- **BOOLEAN** type for true/false flags
- **JSON** type with OSON binary storage
- **VECTOR** type for 768-dimensional embeddings
- **TIMESTAMP WITH TIME ZONE** for UTC timestamps

See [docs/guides/schema-design.md](docs/guides/schema-design.md) for complete schema documentation.
```

### Task 4.4: Document Oracle vs PostgreSQL Parity
**Estimated**: 5 minutes

**File**: `docs/guides/schema-design.md` or dedicated parity doc

**Create comparison table**:

| Feature | PostgreSQL | Oracle 23ai | Status |
|---------|------------|-------------|--------|
| Store table | ✅ Yes | ✅ Yes | ✅ Complete |
| Product table | ✅ Yes | ✅ Yes | ✅ Complete |
| Vector embeddings | pgvector | VECTOR | ✅ Complete |
| Boolean type | boolean | BOOLEAN | ✅ Complete |
| JSON storage | jsonb | JSON (OSON) | ✅ Complete |
| Vector search cache | ✅ Yes | ❌ No | 🔄 Future |

### Task 4.5: Clean Up Temp Files
**Estimated**: 2 minutes

**Docs & Vision Agent responsibility**:
```bash
# Clean up temp directories
rm -rf specs/active/modernize-oracle-schema/tmp/*
rm -rf specs/active/oracle-23ai-features/tmp/*

# Keep research and documentation
```

---

## Validation Checklist

Before marking complete, verify:

### Migration Validation
- [ ] Migration 0002 upgrade succeeds without errors
- [ ] Migration 0002 downgrade succeeds without errors
- [ ] Can upgrade from 0001 → 0002 → 0001 → 0002 repeatedly

### Data Validation
- [ ] All 15 store fixtures load correctly
- [ ] Product boolean columns accept TRUE/FALSE
- [ ] Timestamp columns display timezone info
- [ ] JSON columns store and retrieve data correctly
- [ ] Vector embeddings work in similarity searches

### Application Validation
- [ ] Application starts successfully
- [ ] Product search endpoint works
- [ ] Store locator endpoint works (if implemented)
- [ ] Cache operations work correctly
- [ ] Metrics are recorded properly

### Testing Validation
- [ ] Integration tests pass
- [ ] Unit tests pass (if affected)
- [ ] Manual testing checklist complete

### Documentation Validation
- [ ] Migration README updated
- [ ] Schema design guide complete
- [ ] Main README updated
- [ ] Code comments accurate
- [ ] Temp files cleaned up

---

## Troubleshooting Guide

### Common Issues

**Issue**: Migration fails with "table already exists"
- **Solution**: Run `uv run app db downgrade base` first

**Issue**: Boolean columns show as 1/0 instead of TRUE/FALSE
- **Solution**: Check python-oracledb version (need 2.x), verify Oracle 23ai version

**Issue**: Fixture loading fails on store table
- **Solution**: Ensure migration 0002 is applied: `uv run app db upgrade head`

**Issue**: Sequence reset fails for store table
- **Solution**: Verify `store` is in `tables_with_sequences` list in `app/db/utils.py`

**Issue**: Timestamp columns don't show timezone
- **Solution**: Check query tool settings, try `TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS TZH:TZM')`

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | 30 min | None |
| Phase 2 | 20 min | Phase 1 complete |
| Phase 3 | 30 min | Phases 1-2 complete |
| Phase 4 | 30 min | Phase 3 complete |
| **Total** | **1 hour 50 min** | - |

**Buffer**: Add 30 min for unexpected issues = **~2.5 hours total**
