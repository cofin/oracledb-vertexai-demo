# Recovery Guide: Modernize Oracle Schema

**Requirement**: modernize-oracle-schema
**Last Updated**: 2025-10-17

---

## Quick Start - Resuming Work

### Current Status
**Planning Complete** → Ready for Implementation

### Next Action
Start Phase 1: Create migration script

### Command to Resume
```bash
# Navigate to project
cd /home/cody/code/g/oracledb-vertexai-demo

# Review PRD
cat specs/active/modernize-oracle-schema/prd.md

# Review task checklist
cat specs/active/modernize-oracle-schema/tasks.md

# Start Phase 1: Create migration file
touch app/db/migrations/0002_add_store_table_and_modernize_types.sql
```

---

## Context Recap

### Problem
- Oracle schema is missing `store` table (PostgreSQL has it)
- Using outdated data types: `NUMBER(1)` instead of native `BOOLEAN`
- Fixture loading fails: `uv run app db load-fixtures`
- Error: "ORA-03048: SQL reserved word 'ON' is not syntactically valid"

### Solution
1. Create migration 0002 to add `store` table
2. Modernize boolean columns to use Oracle 23ai native `BOOLEAN`
3. Upgrade timestamp columns to use `TIMESTAMP WITH TIME ZONE`
4. Update application code for boolean handling
5. Test fixture loading and verify data

### Research Complete
- Oracle 23ai BOOLEAN type: ✅ Native support confirmed
- JSON/OSON: ✅ Already binary format (like PostgreSQL JSONB)
- VECTOR types: ✅ FLOAT32 optimal for Vertex AI
- Research docs: `specs/active/oracle-23ai-features/`

---

## File Locations

### Planning Documents
```
specs/active/modernize-oracle-schema/
├── prd.md              # Product Requirements Document
├── tasks.md            # High-level task checklist
├── tasks-detail.md     # Detailed implementation steps
├── progress.md         # Running progress log
└── recovery.md         # This file
```

### Research Documents
```
specs/active/oracle-23ai-features/
├── SUMMARY.md          # Quick reference
├── oracle-23ai-data-types-research.md  # Full research
└── MIGRATION-GUIDE.md  # Migration patterns
```

### Files to Create/Modify
```
app/db/migrations/
└── 0002_add_store_table_and_modernize_types.sql  # New migration

app/db/
└── utils.py  # Update COFFEE_SHOP_TABLES, _reset_sequences()

app/services/
├── product.py   # Review boolean handling
└── metrics.py   # Review boolean handling

docs/guides/
└── schema-design.md  # New or update
```

---

## Phase Breakdown

### Phase 1: Update Existing Migration (30 min) - **START HERE**

**Goal**: Update 0001 migration in-place, then wipe and reload database

**Steps**:
1. Edit file: `app/db/migrations/0001_initial_schema.sql`
2. Add store table (after product table, before response_cache):
   - Use `VARCHAR2(500)` for address (NOT CLOB)
   - Add indexes for store (city, state, zip)
   - Add store updated_at trigger
3. Modernize existing tables:
   - Change `NUMBER(1)` to `BOOLEAN` for boolean columns
   - Change `TIMESTAMP` to `TIMESTAMP WITH TIME ZONE` for timestamps
4. Wipe and reload database:
   ```bash
   uv run app db downgrade base     # Wipe everything
   uv run app db upgrade head       # Create fresh schema
   uv run app db load-fixtures      # Load all data
   ```

**Reference**: See `tasks-detail.md` Section "Phase 1" for SQL examples

---

### Phase 2: Application Code (20 min)

**Goal**: Update Python code for new schema

**Steps**:
1. Update `app/db/utils.py`:
   - Add "store" to COFFEE_SHOP_TABLES (first position)
   - Add "store" to tables_with_sequences in _reset_sequences()
2. Review `app/services/product.py`:
   - Check for `WHERE in_stock = 1` → change to `WHERE in_stock = TRUE`
3. Review `app/services/metrics.py`:
   - Check cache hit boolean handling
4. Search codebase:
   ```bash
   rg "in_stock\s*=\s*[01]" app/
   rg "cache_hit\s*=\s*[01]" app/
   ```

**Reference**: See `tasks-detail.md` Section "Phase 2"

---

### Phase 3: Testing (30 min)

**Goal**: Verify all changes work correctly

**Steps**:
1. Test migrations:
   ```bash
   uv run app db downgrade base
   uv run app db upgrade head
   ```
2. Load fixtures:
   ```bash
   uv run app db load-fixtures
   ```
3. Verify data:
   ```sql
   SELECT COUNT(*) FROM store;  -- Expect 15
   SELECT in_stock FROM product WHERE id = 1;  -- Expect TRUE/FALSE
   ```
4. Run tests:
   ```bash
   uv run pytest tests/integration/ -v
   ```
5. Start app:
   ```bash
   uv run app run
   ```

**Reference**: See `tasks-detail.md` Section "Phase 3"

---

### Phase 4: Documentation (30 min)

**Goal**: Update all documentation

**Files to update**:
- `app/db/migrations/README.md` - Document migration 0002
- `docs/guides/schema-design.md` - Full schema documentation
- `README.md` - Note Oracle 23ai features
- Clean up `specs/active/*/tmp/` directories

**Reference**: See `tasks-detail.md` Section "Phase 4"

---

## Key Commands

### Migration Commands
```bash
# Show current migration version
uv run app db show-current-revision

# Upgrade to specific version
uv run app db upgrade 0002

# Upgrade to latest
uv run app db upgrade head

# Downgrade to version
uv run app db downgrade 0001

# Downgrade to base
uv run app db downgrade base
```

### Fixture Commands
```bash
# List available fixtures
uv run app db load-fixtures --list

# Load all fixtures
uv run app db load-fixtures

# Load specific tables
uv run app db load-fixtures -t store,product
```

### Testing Commands
```bash
# Run integration tests
uv run pytest tests/integration/ -v

# Run specific test
uv run pytest tests/integration/test_load_fixtures.py -v

# Start application
uv run app run
```

---

## Common Issues & Solutions

### Issue: Migration fails with "table already exists"
**Solution**: Downgrade first
```bash
uv run app db downgrade base
uv run app db upgrade head
```

### Issue: Fixture loading fails on store table
**Solution**: Ensure migration 0002 is applied
```bash
uv run app db show-current-revision
uv run app db upgrade head
```

### Issue: Boolean columns don't work
**Solution**: Check python-oracledb version
```bash
pip show python-oracledb  # Need 2.x
pip install --upgrade python-oracledb
```

### Issue: Sequence reset fails
**Solution**: Check tables_with_sequences includes "store"
```python
# In app/db/utils.py _reset_sequences()
tables_with_sequences = [
    "store",  # Make sure this is present
    "product",
    # ...
]
```

---

## Testing Checklist

Before marking complete:

### Migration Testing
- [ ] Upgrade from 0001 to 0002 works
- [ ] Downgrade from 0002 to 0001 works
- [ ] Can repeat upgrade/downgrade cycle
- [ ] No SQL errors during migration

### Data Testing
- [ ] Store table has 15 rows
- [ ] Boolean columns accept TRUE/FALSE
- [ ] Timestamps show timezone info
- [ ] JSON columns work correctly
- [ ] Vector embeddings still work

### Application Testing
- [ ] Application starts without errors
- [ ] Product search works
- [ ] Store queries work (if implemented)
- [ ] Cache operations work
- [ ] Integration tests pass

### Documentation Testing
- [ ] Migration README updated
- [ ] Schema guide complete
- [ ] README updated
- [ ] Temp files cleaned

---

## Dependencies

### Required Software
- Oracle 23ai Free Edition (running)
- python-oracledb 2.x
- SQLSpec migrations framework
- pytest (for testing)

### Required Files
- Fixture files in `app/db/fixtures/`:
  - `store.json.gz` ✅ (already exists)
  - `product.json.gz` ✅
  - `intent_exemplar.json.gz` ✅

### Research Documents
- `specs/active/oracle-23ai-features/SUMMARY.md` - Type reference
- `specs/active/oracle-23ai-features/MIGRATION-GUIDE.md` - Migration patterns

---

## Success Criteria

**All of these must pass**:
- [ ] `uv run app db load-fixtures` completes successfully
- [ ] `SELECT COUNT(*) FROM store` returns 15
- [ ] `SELECT in_stock FROM product WHERE id = 1` returns TRUE or FALSE (not 1 or 0)
- [ ] `uv run app db upgrade head` completes without errors
- [ ] `uv run app db downgrade base` completes without errors
- [ ] `uv run app run` starts application successfully
- [ ] `uv run pytest tests/integration/` passes all tests
- [ ] Documentation is complete and accurate

---

## Timeline Estimate

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Migration Script | 30 min | ⏳ Not Started |
| Phase 2: Application Code | 20 min | ⏳ Not Started |
| Phase 3: Testing | 30 min | ⏳ Not Started |
| Phase 4: Documentation | 30 min | ⏳ Not Started |
| **Total** | **1 hour 50 min** | - |

**Buffer**: 30 min for unexpected issues

**Total with buffer**: ~2.5 hours

---

## Agent Coordination

### Who Does What

**Implementation Agent** (You or another agent):
- Phase 1: Create migration script
- Phase 2: Update application code
- Initial testing

**Testing Agent**:
- Phase 3: Comprehensive testing
- Validation of all changes
- Integration test verification

**Docs & Vision Agent**:
- Phase 4: Documentation updates
- Schema documentation
- Cleanup temp files

---

## Progress Tracking

Update `progress.md` after completing each major task:
```bash
# After Phase 1
echo "### Phase 1 Complete - $(date)" >> specs/active/modernize-oracle-schema/progress.md

# After Phase 2
echo "### Phase 2 Complete - $(date)" >> specs/active/modernize-oracle-schema/progress.md

# Continue for all phases
```

---

## Questions? Need Help?

### Review These Documents
1. **PRD** (`prd.md`) - Why we're doing this
2. **Tasks** (`tasks.md`) - What needs to be done
3. **Tasks Detail** (`tasks-detail.md`) - How to do each task
4. **Oracle 23ai Research** (`specs/active/oracle-23ai-features/SUMMARY.md`) - Type reference

### Key Resources
- [Oracle 23ai BOOLEAN Documentation](https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Data-Types.html#GUID-A3C0D836-BADB-44E5-A5D4-265BA5968483)
- [SQLSpec Migrations Guide](https://docs.litestar.dev/latest/usage/databases/sqlspec/)
- PostgreSQL Reference Schema: `../postgres-vertexai-demo/app/db/migrations/0001_initial_schema_with_pgvector_support.sql`

---

**Last checkpoint**: Planning complete, ready for Phase 1 implementation
**Next step**: Create migration file `0002_add_store_table_and_modernize_types.sql`
**Estimated time to completion**: 2-2.5 hours
