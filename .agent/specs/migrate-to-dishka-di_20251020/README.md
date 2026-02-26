# Dishka DI Migration - Requirement Workspace

**Status:** Planning Complete ✅
**Created:** 2025-10-20
**Estimated Effort:** 12-20 hours

---

## 📋 Overview

This workspace contains all planning documents for migrating from the service locator pattern to Dishka dependency injection.

**Goal:** Replace custom service locator (213 lines) with clean Dishka DI (~80 lines), improving testability, type safety, and maintainability.

---

## 🗂️ Document Structure

### Essential Documents

1. **[prd.md](prd.md)** - Product Requirements Document
   - Problem statement and proposed solution
   - Technical specification
   - Migration strategy (5 phases)
   - Success criteria
   - Risk mitigation

2. **[tasks.md](tasks.md)** - High-Level Task Checklist
   - 38 tasks across 5 phases
   - Agent assignments
   - Time estimates
   - Dependencies

3. **[tasks-detail.md](tasks-detail.md)** - Detailed Implementation Guide
   - Step-by-step code examples
   - Verification commands
   - Common issues and solutions

4. **[progress.md](progress.md)** - Current Status Tracker
   - Task completion checkboxes
   - Time spent per phase
   - Issues and blockers
   - Metrics tracking

5. **[recovery.md](recovery.md)** - Resumption Guide
   - How to resume after interruption
   - Phase-specific recovery instructions
   - Rollback procedures
   - Quick reference commands

### Research

6. **[research/dishka-patterns.md](research/dishka-patterns.md)** - Technical Research
   - Dishka core concepts
   - Litestar integration patterns
   - SQLSpec + Dishka integration
   - Code examples (1216 lines)

---

## 🎯 Key Highlights

### Clean Import Convention

We're re-exporting `FromDishka` as `Inject` for cleaner imports:

```python
from app.lib.di import Inject, inject  # ✓ Clean!

# NOT:
from dishka.integrations.litestar import FromDishka  # ✗ Verbose
```

### Code Cleanup Policy

**CRITICAL:** Complete deletion of old code - NO commenting out!

- ❌ No commented code
- ❌ No references to deleted modules
- ✅ Clean git history

### Migration Phases

1. **Phase 1: Setup** (2-3h) - Install Dishka, create providers
2. **Phase 2: Controllers** (4-6h) - Migrate 10 endpoints
3. **Phase 3: ADK Tools** (3-4h) - Migrate 7 tool functions
4. **Phase 4: Cleanup** (2-3h) - Delete old code
5. **Phase 5: Testing** (3-4h) - Tests and docs

---

## 🚀 Quick Start

### For Reviewers

```bash
# Read PRD first
cat specs/active/migrate-to-dishka-di/prd.md

# Review task breakdown
cat specs/active/migrate-to-dishka-di/tasks.md

# Check research findings
cat specs/active/migrate-to-dishka-di/research/dishka-patterns.md
```

### For Implementers

```bash
# Start with detailed tasks
cat specs/active/migrate-to-dishka-di/tasks-detail.md

# Track progress
vim specs/active/migrate-to-dishka-di/progress.md

# If resuming work
cat specs/active/migrate-to-dishka-di/recovery.md
```

---

## 📊 Success Metrics

### Code Quality

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Boilerplate Lines | 213 | ~80 | Target: -133 |
| Special Cases | 8+ | 0 | Target: 0 |
| Type Safety | Partial | Full | Target: 100% |
| Circular Imports | 3 | 0 | Target: 0 |

### Acceptance Criteria

- [ ] All services use Dishka DI
- [ ] All controllers use `@inject` + `Inject[T]`
- [ ] ADK tools integrated with Dishka
- [ ] Zero service locator references
- [ ] All tests pass
- [ ] Code reduction: -133+ lines
- [ ] Full type safety (mypy/pyright clean)

---

## 🛠️ Implementation Order

```
Phase 1: Setup & Foundation
  ├─ Install Dishka
  ├─ Create app/lib/di.py (clean imports)
  ├─ Create app/server/providers.py
  └─ Update app/asgi.py

Phase 2: Controller Migration
  ├─ Migrate simple endpoints
  ├─ Migrate dashboard endpoints
  ├─ Migrate chat endpoints
  └─ Remove dependencies dict

Phase 3: ADK Tools Migration
  ├─ Update 7 tool functions
  ├─ Add container context
  └─ Test end-to-end

Phase 4: Complete Cleanup
  ├─ DELETE app/services/locator.py
  ├─ DELETE app/server/deps.py
  ├─ Remove all references
  └─ Run linters + tests

Phase 5: Testing & Documentation
  ├─ Create mock providers
  ├─ Update tests
  ├─ Performance testing
  └─ Update documentation
```

---

## ⚠️ Critical Notes

### Before You Start

1. **Read the PRD** - Understand the full scope
2. **Review research** - Understand Dishka patterns
3. **Check current branch** - Ensure on correct branch
4. **Run tests** - Establish baseline

### During Implementation

1. **Update progress.md** - After each task
2. **Test incrementally** - Don't wait until the end
3. **Keep service locator** - Until Phase 4
4. **Document issues** - In progress.md

### Before Cleanup (Phase 4)

1. **Verify all migrations** - Check every endpoint and tool
2. **Run full tests** - Ensure nothing broken
3. **Backup if needed** - Though git has you covered
4. **Read cleanup policy** - No comments, complete deletion

---

## 📚 Reference Links

### Internal Documentation

- [PRD](prd.md) - Complete requirements
- [Tasks](tasks.md) - High-level checklist
- [Details](tasks-detail.md) - Implementation guide
- [Progress](progress.md) - Current status
- [Recovery](recovery.md) - Resumption guide
- [Research](research/dishka-patterns.md) - Technical findings

### External Resources

- **Dishka Docs:** https://dishka.readthedocs.io/
- **Litestar Integration:** https://dishka.readthedocs.io/en/stable/integrations/litestar.html
- **Example Repo:** https://gitlab.bartab.fr/oss-public/litestar_dishka_modular

---

## 👥 Agent Assignments

| Agent | Responsibilities | Est. Hours |
|-------|------------------|------------|
| **Expert** | Setup, providers, migrations, cleanup | 10-14 |
| **Testing** | Test migration, mocks, performance | 4-5 |
| **Docs & Vision** | Documentation, code review, cleanup | 2-3 |

**Total:** 16-22 hours

---

## 🔍 Verification Commands

### Check Installation

```bash
uv run python -c "import dishka; print(f'Dishka {dishka.__version__}')"
```

### Check Migration Status

```bash
# How many endpoints migrated?
grep -c "@inject" app/server/controllers.py

# Any service locator refs left?
git grep "service_locator" -- '*.py'
git grep "from app.server import deps" -- '*.py'
```

### Verify Cleanup

```bash
# These should return empty after Phase 4:
git grep "service_locator" -- '*.py'
git grep "ServiceLocator" -- '*.py'
git grep "from app.server import deps" -- '*.py'
```

### Test Everything

```bash
# Linters
uv run ruff check app/
uv run mypy app/
uv run pyright app/

# Tests
uv run pytest -v

# Manual
uv run app run
```

---

## 📞 Support

### Questions?

1. Check [prd.md](prd.md) - Likely answered there
2. Check [recovery.md](recovery.md) - Common issues
3. Check [research](research/dishka-patterns.md) - Technical details

### Found an Issue?

1. Document in [progress.md](progress.md) under "Issues & Blockers"
2. Add to "Decisions & Changes" if it affects approach
3. Update estimate if needed

---

## ✅ Approval Checklist

- [ ] PRD reviewed and approved
- [ ] Task breakdown reviewed
- [ ] Clean import pattern approved (`Inject` vs `FromDishka`)
- [ ] Code cleanup policy understood (complete deletion)
- [ ] Timeline acceptable
- [ ] Risk mitigations acceptable
- [ ] Ready to start Phase 1

---

**Planning Completed:** 2025-10-20
**Ready for Implementation:** Awaiting approval
**Estimated Start Date:** TBD
**Estimated Completion:** TBD

---

**Next Step:** Review PRD → Approve → Begin Phase 1
