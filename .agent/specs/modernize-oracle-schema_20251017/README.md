# Modernize Oracle Schema & Fix Data Model Parity

**Status**: 📋 Planning Complete → Ready for Implementation
**Priority**: 🔴 High
**Estimated Effort**: 2-2.5 hours
**Created**: 2025-10-17

---

## Quick Links

- **[PRD](prd.md)** - Full requirements and technical design
- **[Tasks](tasks.md)** - High-level task checklist
- **[Tasks Detail](tasks-detail.md)** - Step-by-step implementation guide
- **[Progress](progress.md)** - Running progress log
- **[Recovery](recovery.md)** - ⭐ **How to resume work** ⭐

---

## Problem Summary

The Oracle database schema is missing the `store` table and uses outdated data type patterns, causing fixture loading to fail.

### Key Issues
1. ❌ Missing `store` table (PostgreSQL has it)
2. ❌ Using `NUMBER(1)` instead of native `BOOLEAN`
3. ❌ Using `TIMESTAMP` instead of `TIMESTAMP WITH TIME ZONE`
4. ❌ Fixture loading fails: `uv run app db load-fixtures`

---

## Solution Overview

Create migration 0002 to:
1. ✅ Add `store` table with all PostgreSQL columns
2. ✅ Modernize boolean columns to Oracle 23ai native `BOOLEAN`
3. ✅ Upgrade timestamp columns to `TIMESTAMP WITH TIME ZONE`
4. ✅ Update application code for new types
5. ✅ Test and document changes

---

## Quick Start

### For First Time
```bash
# Read the recovery guide
cat specs/active/modernize-oracle-schema/recovery.md

# Start Phase 1: Create migration script
# See tasks-detail.md for complete SQL examples
```

### For Resuming Work
```bash
# Check current status
cat specs/active/modernize-oracle-schema/progress.md

# Review next steps
cat specs/active/modernize-oracle-schema/recovery.md

# Continue where you left off
```

---

## Research Complete ✅

Oracle 23ai feature research is complete and saved in:
- `specs/active/oracle-23ai-features/SUMMARY.md` - Quick reference
- `specs/active/oracle-23ai-features/oracle-23ai-data-types-research.md` - Full details

### Key Findings
- ✅ **BOOLEAN**: Native support in Oracle 23ai
- ✅ **JSON**: Already uses OSON binary format (like PostgreSQL JSONB)
- ✅ **VECTOR**: FLOAT32 optimal for Vertex AI embeddings
- ✅ **TIMESTAMP WITH TIME ZONE**: Full support for UTC timestamps

---

## Implementation Phases

### Phase 1: Migration Script (30 min) ⏳
Create `app/db/migrations/0002_add_store_table_and_modernize_types.sql`
- Add store table
- Modernize boolean columns
- Upgrade timestamp columns
- Write downgrade script

### Phase 2: Application Code (20 min) ⏳
Update Python code for new schema
- Update `app/db/utils.py`
- Review `app/services/product.py`
- Review `app/services/metrics.py`

### Phase 3: Testing (30 min) ⏳
Verify all changes work
- Test migrations
- Load fixtures
- Run integration tests
- Test application startup

### Phase 4: Documentation (30 min) ⏳
Update documentation
- Migration README
- Schema design guide
- Main README
- Clean up temp files

---

## Success Criteria

All of these must pass:
- [ ] `uv run app db load-fixtures` completes successfully
- [ ] Store table has 15 rows
- [ ] Boolean columns use TRUE/FALSE (not 1/0)
- [ ] Migrations upgrade/downgrade work
- [ ] Application starts without errors
- [ ] Integration tests pass

---

## Files Structure

```
specs/active/modernize-oracle-schema/
├── README.md           # This file
├── prd.md              # Product Requirements Document
├── tasks.md            # High-level tasks
├── tasks-detail.md     # Detailed implementation steps
├── progress.md         # Running progress log
├── recovery.md         # Resume work guide
├── research/           # Research outputs (empty - see oracle-23ai-features)
└── tmp/                # Temporary files (will be cleaned)
```

---

## Next Action

**Start here**: Read [recovery.md](recovery.md) for step-by-step resumption guide

**Phase 1 Start**: Create migration file and write SQL (see [tasks-detail.md](tasks-detail.md) Phase 1)

**Need context?**: Read [prd.md](prd.md) for complete technical design

---

## Agent Assignments

- **Implementation**: Phases 1 & 2 (migration + code)
- **Testing**: Phase 3 (validation)
- **Docs & Vision**: Phase 4 (documentation + cleanup)

---

**Created by**: Planner Agent
**Last Updated**: 2025-10-17
**Status**: Ready for implementation
