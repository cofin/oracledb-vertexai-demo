# Recovery Guide: Resuming Dishka DI Migration

**Purpose:** This document explains how to resume work on the Dishka DI migration after interruption.

**Last Updated:** 2025-10-20

---

## Quick Start

### 1. Check Current Status

```bash
# Navigate to project
cd /home/cody/code/g/oracledb-vertexai-demo

# Check progress log
cat specs/active/migrate-to-dishka-di/progress.md

# Check git status
git status
git log --oneline -10
```

### 2. Determine Current Phase

Check `progress.md` to find which phase is in progress:
- Phase 1: Setup & Foundation
- Phase 2: Controller Migration
- Phase 3: ADK Tools Migration
- Phase 4: Complete Cleanup
- Phase 5: Testing & Documentation

### 3. Resume Work

Based on current phase, follow the appropriate section below.

---

## Phase-Specific Recovery

### If in Phase 1: Setup & Foundation

**Check Progress:**

```bash
# Check if Dishka installed
uv run python -c "import dishka; print(f'✓ Dishka {dishka.__version__}')" 2>&1

# Check if DI module exists
ls -la app/lib/di.py 2>&1

# Check if providers exist
ls -la app/server/providers.py 2>&1

# Check if ASGI updated
grep "dishka" app/asgi.py
```

**Resume Points:**

1. **If nothing exists:** Start at Task 1.1 (Install Dependencies)
2. **If Dishka installed but no `di.py`:** Start at Task 1.2 (Create DI Module)
3. **If `di.py` exists but no `providers.py`:** Start at Task 1.3 (Create SQLSpec Provider)
4. **If `providers.py` exists but ASGI not updated:** Start at Task 1.7 (Update ASGI)

**Verification After Phase 1:**

```bash
# App should start without errors
uv run app run

# Check logs for Dishka initialization
# Should see no errors, both service locator and Dishka active
```

---

### If in Phase 2: Controller Migration

**Check Progress:**

```bash
# Check which endpoints migrated
grep -n "@inject" app/server/controllers.py

# Check if dependencies dict removed
grep -n "dependencies = {" app/server/controllers.py

# Count migrated endpoints
grep -c "@inject" app/server/controllers.py
```

**Resume Points:**

1. **If no `@inject` found:** Start at Task 2.1 (Migrate Simple Endpoints)
2. **If some `@inject` found:** Check which endpoints remain
3. **If all `@inject` but dependencies dict still exists:** Task 2.6 (Remove dict)

**Endpoint Checklist:**

```bash
# Check each endpoint for migration
grep -B5 "async def.*(" app/server/controllers.py | grep -E "(async def|@inject)"

# Target endpoints:
- show_coffee_chat (/)
- handle_coffee_chat (/ POST)
- stream_response (/chat/stream)
- performance_dashboard (/dashboard)
- get_metrics (/metrics)
- get_metrics_summary (/api/metrics/summary)
- get_chart_data (/api/metrics/charts)
- vector_search_demo (/api/vector-demo)
- get_query_log (/api/help/query-log)
- favicon (/favicon.ico)
```

**Verification:**

```bash
# Test each migrated endpoint
curl http://localhost:5006/
curl http://localhost:5006/dashboard
curl -X POST http://localhost:5006/ -d "message=test"
```

---

### If in Phase 3: ADK Tools Migration

**Check Progress:**

```bash
# Check which tools migrated
grep -n "get_request_container" app/services/adk/tools.py

# Count migrated tools
grep -c "get_request_container" app/services/adk/tools.py
```

**Resume Points:**

1. **If no `get_request_container` found:** Start at Task 3.1
2. **If some tools migrated:** Check which remain (7 total tools)
3. **If all tools migrated:** Task 3.4 (Test end-to-end)

**Tool Checklist:**

```bash
# 7 tool functions to migrate:
- search_products_by_vector
- get_product_details
- classify_intent
- record_search_metric
- get_store_locations
- find_stores_by_location
- get_store_hours
```

**Verification:**

```bash
# Test ADK agent flow
uv run app run

# Send chat message via UI or API
curl -X POST http://localhost:5006/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=I need a strong coffee"

# Check logs for tool calls
# Should see no errors about missing container
```

---

### If in Phase 4: Complete Cleanup

**CRITICAL:** This phase DELETES code permanently!

**Check Progress:**

```bash
# Check if files still exist
ls -la app/services/locator.py 2>&1
ls -la app/server/deps.py 2>&1

# Check for remaining references
git grep "service_locator" -- '*.py'
git grep "from app.server import deps" -- '*.py'
```

**Resume Points:**

1. **If both files exist and refs found:** Start at Task 4.1 (Delete locator)
2. **If locator deleted but deps exists:** Task 4.2 (Delete deps)
3. **If both deleted but refs remain:** Task 4.4 (Remove refs)
4. **If no refs found:** Task 4.5 (Run linters)

**Safety Checks Before Deleting:**

```bash
# Ensure all controllers migrated
grep -L "@inject" app/server/controllers.py

# Ensure all tools migrated
grep "service_locator" app/services/adk/tools.py

# If either returns results, DO NOT DELETE YET!
```

**Verification:**

```bash
# After deletion, verify no references
git grep "service_locator" -- '*.py' # Should be empty
git grep "ServiceLocator" -- '*.py'  # Should be empty
git grep "from app.server import deps" -- '*.py' # Should be empty

# Run linters
uv run ruff check app/
uv run mypy app/
uv run pyright app/

# Run tests
uv run pytest -v
```

---

### If in Phase 5: Testing & Documentation

**Check Progress:**

```bash
# Check if mock providers exist
ls -la tests/fixtures/mock_providers.py 2>&1

# Check if documentation updated
ls -la docs/guides/dependency-injection.md 2>&1

# Check test coverage
uv run pytest --cov=app --cov-report=term
```

**Resume Points:**

1. **If no mock providers:** Start at Task 5.1
2. **If mock providers exist but tests not updated:** Task 5.2
3. **If tests updated but no docs:** Task 5.4
4. **If docs exist:** Task 5.5 (Code review)

**Final Verification:**

```bash
# Run full test suite
make test

# Run linters
make lint

# Manual testing checklist
uv run app run
# Then test all endpoints manually
```

---

## Common Issues & Solutions

### Issue: "No active Dishka request container"

**Symptom:** Error when calling ADK tools

**Cause:** Container not set in context

**Solution:**
1. Check if `set_request_container()` called in middleware
2. Verify Dishka middleware configured in `app/asgi.py`
3. Add explicit middleware if needed (see `tasks-detail.md` Task 3.5)

---

### Issue: Import error for `service_locator`

**Symptom:** `ModuleNotFoundError: No module named 'app.services.locator'`

**Cause:** File deleted but imports remain

**Solution:**
```bash
# Find all remaining imports
git grep "from app.services.locator import" -- '*.py'
git grep "service_locator" -- '*.py'

# Remove each import
# Update code to use Dishka instead
```

---

### Issue: Type errors with `Inject[T]`

**Symptom:** Mypy/pyright complains about `Inject`

**Cause:** Missing import from `app.lib.di`

**Solution:**
```python
# Add import
from app.lib.di import Inject, inject

# Fix type hints
service: Inject[MyService]  # Correct

# NOT:
service: FromDishka[MyService]  # Wrong
service: MyService  # Wrong
```

---

### Issue: Tests failing after migration

**Symptom:** Pytest failures

**Common Causes:**

1. **Service locator mocks still in tests**
   - Remove `mock_service_locator` fixtures
   - Use Dishka test container instead

2. **Missing `@inject` decorators**
   - Add to all controller methods that need DI

3. **Dependencies dict still present**
   - Remove from controller class

**Solution:**
```python
# Update test fixtures
from tests.fixtures.mock_providers import test_container

@pytest.mark.asyncio
async def test_my_endpoint(test_container):
    async with test_container() as request_container:
        service = await request_container.get(MyService)
        # ... test code ...
```

---

## Rollback Procedures

### Rollback from Phase 1-3

**Safe to rollback** - Service locator still present

```bash
# Revert changes
git log --oneline -20  # Find commit before migration
git revert <commit-hash>

# Or reset (if no shared commits)
git reset --hard <commit-before-migration>

# Verify app works
uv run app run
make test
```

---

### Rollback from Phase 4 (After Deletion)

**DANGEROUS** - Files deleted!

```bash
# If committed, restore from git history
git log --all --full-history -- app/services/locator.py
git checkout <commit-hash> -- app/services/locator.py

git log --all --full-history -- app/server/deps.py
git checkout <commit-hash> -- app/server/deps.py

# Restore imports
git checkout <commit-hash> -- app/config.py

# Revert controller changes
git checkout <commit-hash> -- app/server/controllers.py

# Revert tool changes
git checkout <commit-hash> -- app/services/adk/tools.py

# Test
uv run app run
make test
```

---

## Quick Reference

### File Locations

```
specs/active/migrate-to-dishka-di/
├── prd.md                 # Product Requirements Document
├── tasks.md               # High-level task checklist
├── tasks-detail.md        # Detailed task implementation
├── progress.md            # Current status (UPDATE THIS!)
├── recovery.md            # This file
└── research/
    └── dishka-patterns.md # Research findings
```

### Key Files Being Modified

```
app/
├── asgi.py                    # MODIFY: Add Dishka setup
├── config.py                  # MODIFY: Remove service_locator
├── lib/
│   └── di.py                  # CREATE: Clean imports
├── server/
│   ├── controllers.py         # MODIFY: Add @inject
│   ├── deps.py                # DELETE: Old providers
│   └── providers.py           # CREATE: Dishka providers
└── services/
    ├── locator.py             # DELETE: Service locator
    └── adk/
        └── tools.py           # MODIFY: Use container
```

### Commands Reference

```bash
# Check status
cat specs/active/migrate-to-dishka-di/progress.md

# Verify setup
uv run python -c "import dishka; from app.lib.di import Inject, inject; print('✓')"

# Start app
uv run app run

# Run tests
uv run pytest -v

# Run linters
uv run ruff check app/
uv run mypy app/

# Search for remaining refs
git grep "service_locator" -- '*.py'
git grep "from app.server import deps" -- '*.py'
```

---

## Contact & Support

### Documentation

- **PRD:** `specs/active/migrate-to-dishka-di/prd.md`
- **Detailed Tasks:** `specs/active/migrate-to-dishka-di/tasks-detail.md`
- **Research:** `specs/active/migrate-to-dishka-di/research/dishka-patterns.md`

### External Resources

- **Dishka Docs:** https://dishka.readthedocs.io/
- **Litestar Integration:** https://dishka.readthedocs.io/en/stable/integrations/litestar.html
- **Example Repo:** https://gitlab.bartab.fr/oss-public/litestar_dishka_modular

---

**Remember:** Always update `progress.md` after completing each task!

**Last Updated:** 2025-10-20
