# High-Level Task Checklist: Dishka DI Migration

**Project:** Migrate to Dishka Dependency Injection
**Estimated:** 12-20 hours total
**Status:** Planning

---

## Phase 1: Setup & Foundation (2-3 hours)

### Task 1.1: Install Dependencies
- [ ] Run `uv add dishka`
- [ ] Verify installation: `uv run python -c "import dishka; print(dishka.__version__)"`
- [ ] Update `pyproject.toml` if needed

**Agent:** Expert
**Estimated:** 15 minutes

---

### Task 1.2: Create DI Module with Clean Imports
- [ ] Create `app/lib/di.py`
- [ ] Re-export `FromDishka` as `Inject`
- [ ] Re-export `inject` decorator
- [ ] Re-export `setup_dishka`
- [ ] Add docstring explaining clean import pattern

**Agent:** Expert
**Estimated:** 30 minutes

**Expected Output:**

```python
# app/lib/di.py
"""Dependency injection utilities and clean imports.

This module provides a clean interface to the underlying DI framework
(Dishka) without exposing implementation details throughout the codebase.

Example:
    from app.lib.di import Inject, inject

    class MyController(Controller):
        @get("/")
        @inject
        async def handler(self, service: Inject[MyService]) -> Response:
            ...
"""

from dishka.integrations.litestar import (
    FromDishka as Inject,
    inject,
    setup_dishka,
)

__all__ = ["Inject", "inject", "setup_dishka"]
```

---

### Task 1.3: Create SQLSpec Provider
- [ ] Create `app/server/providers.py`
- [ ] Implement `SQLSpecProvider` class
- [ ] Add `get_sqlspec_manager()` - APP scope
- [ ] Add `get_database_config()` - APP scope
- [ ] Add `get_db_session()` - REQUEST scope with `provide_session()`
- [ ] Add comprehensive docstrings

**Agent:** Expert
**Estimated:** 1 hour

**Verification:**
- [ ] Provider uses `async with manager.provide_session(config)` pattern
- [ ] Generator properly yields session
- [ ] Scopes correctly set (APP for singletons, REQUEST for sessions)

---

### Task 1.4: Create Core Service Provider
- [ ] Add `CoreServiceProvider` class to `providers.py`
- [ ] Add simple services (auto-wired): ProductService, CacheService, MetricsService, ExemplarService, StoreService
- [ ] Add complex services (auto-wired): IntentService, AgentToolsService
- [ ] Add VertexAIService - APP scope singleton
- [ ] Add OracleVectorSearchService - explicit provider with mixed scopes
- [ ] Add docstrings explaining auto-wiring

**Agent:** Expert
**Estimated:** 45 minutes

---

### Task 1.5: Create ADK Provider
- [ ] Add `ADKProvider` class to `providers.py`
- [ ] Add `get_adk_runner()` - REQUEST scope
- [ ] Document that ADKRunner manages its own session service

**Agent:** Expert
**Estimated:** 15 minutes

---

### Task 1.6: Add Container Context Helpers
- [ ] Add `ContextVar` for request container storage
- [ ] Add `get_request_container()` helper
- [ ] Add `set_request_container()` helper
- [ ] Add error handling for missing container
- [ ] Document usage in ADK tools

**Agent:** Expert
**Estimated:** 30 minutes

---

### Task 1.7: Update ASGI App Setup
- [ ] Modify `app/asgi.py`
- [ ] Import Dishka setup utilities from `app.lib.di`
- [ ] Import providers
- [ ] Create async container with all providers
- [ ] Add `dishka_lifespan()` context manager
- [ ] Call `setup_dishka(container, app)`
- [ ] **Keep service locator intact** (parallel systems)

**Agent:** Expert
**Estimated:** 30 minutes

**Verification:**
- [ ] App starts without errors
- [ ] Both service locator and Dishka available
- [ ] Container properly closed on shutdown

---

## Phase 2: Controller Migration (4-6 hours)

### Task 2.1: Migrate Simple Endpoints
Endpoints: `/`, `/favicon.ico`

- [ ] Remove from `dependencies` dict (if present)
- [ ] Import `Inject, inject` from `app.lib.di`
- [ ] Add `@inject` decorator
- [ ] Change type hints to `Inject[Service]`
- [ ] Test each endpoint manually
- [ ] Run tests

**Agent:** Expert
**Estimated:** 30 minutes

---

### Task 2.2: Migrate Dashboard Endpoints
Endpoints: `/dashboard`, `/metrics`, `/api/metrics/summary`, `/api/metrics/charts`

Services used: MetricsService, CacheService

- [ ] Update endpoint signatures
- [ ] Add `@inject` decorators
- [ ] Change type hints to `Inject[Service]`
- [ ] Test dashboard loading
- [ ] Verify metrics updates
- [ ] Run tests

**Agent:** Expert
**Estimated:** 1 hour

---

### Task 2.3: Migrate Chat Endpoints
Endpoints: `/` (POST), `/chat/stream/{query_id}`

Services used: ADKRunner, VertexAIService

- [ ] Update endpoint signatures
- [ ] Add `@inject` decorators
- [ ] Change type hints to `Inject[Service]`
- [ ] Test chat flow end-to-end
- [ ] Test streaming endpoint
- [ ] Verify ADK integration works
- [ ] Run tests

**Agent:** Expert
**Estimated:** 1.5 hours

---

### Task 2.4: Migrate Vector Demo Endpoint
Endpoints: `/api/vector-demo`

Services used: VertexAIService, OracleVectorSearchService, MetricsService

- [ ] Update endpoint signature
- [ ] Add `@inject` decorator
- [ ] Change type hints to `Inject[Service]`
- [ ] Test vector search flow
- [ ] Verify embeddings work
- [ ] Verify metrics recording
- [ ] Run tests

**Agent:** Expert
**Estimated:** 45 minutes

---

### Task 2.5: Migrate Helper Endpoints
Endpoints: `/api/help/query-log/{message_id}`

Services used: MetricsService, VertexAIService

- [ ] Update endpoint signature
- [ ] Add `@inject` decorator
- [ ] Change type hints to `Inject[Service]`
- [ ] Test query log retrieval
- [ ] Run tests

**Agent:** Expert
**Estimated:** 30 minutes

---

### Task 2.6: Remove Controller Dependencies Dict
- [ ] Remove entire `dependencies = {...}` dict from `CoffeeChatController`
- [ ] Remove `from app.server import deps` import
- [ ] Verify all endpoints still work
- [ ] Run full test suite

**Agent:** Expert
**Estimated:** 15 minutes

---

## Phase 3: ADK Tools Migration (3-4 hours)

### Task 3.1: Update ADK Tool Functions - Part 1
Tools: `search_products_by_vector`, `get_product_details`

- [ ] Remove `db_manager.provide_session()` calls
- [ ] Remove `service_locator.get()` calls
- [ ] Add `get_request_container()` calls
- [ ] Use `container.get(AgentToolsService)`
- [ ] Keep tool signatures unchanged (ADK compatibility)
- [ ] Add error handling for missing container

**Agent:** Expert
**Estimated:** 1 hour

---

### Task 3.2: Update ADK Tool Functions - Part 2
Tools: `classify_intent`, `record_search_metric`

- [ ] Apply same pattern as Task 3.1
- [ ] Handle JSON serialization for `record_search_metric`
- [ ] Test intent classification
- [ ] Test metrics recording

**Agent:** Expert
**Estimated:** 45 minutes

---

### Task 3.3: Update ADK Tool Functions - Part 3
Tools: `get_store_locations`, `find_stores_by_location`, `get_store_hours`

- [ ] Apply same pattern as Task 3.1
- [ ] Test store location queries
- [ ] Test store hours retrieval

**Agent:** Expert
**Estimated:** 45 minutes

---

### Task 3.4: Test ADK Agent End-to-End
- [ ] Start app
- [ ] Send chat message via UI
- [ ] Verify ADK agent responds
- [ ] Verify tool calls work
- [ ] Verify metrics recorded
- [ ] Check logs for errors

**Agent:** Testing
**Estimated:** 30 minutes

---

### Task 3.5: Setup Container Context in ADK Flow
- [ ] Ensure container is set before ADK tools run
- [ ] Add middleware or hook to set container context
- [ ] Test context availability in tools
- [ ] Add logging for container lifecycle

**Agent:** Expert
**Estimated:** 45 minutes

---

## Phase 4: Complete Cleanup (2-3 hours)

### Task 4.1: Remove Service Locator Module
- [ ] **DELETE** `app/services/locator.py` entirely (142 lines)
- [ ] No commenting out, no references left
- [ ] Commit with message: "feat: remove service locator module"

**Agent:** Expert
**Estimated:** 5 minutes

---

### Task 4.2: Remove Old Dependencies Module
- [ ] **DELETE** `app/server/deps.py` entirely (71 lines)
- [ ] No commenting out, no references left
- [ ] Commit with message: "feat: remove old dependency providers"

**Agent:** Expert
**Estimated:** 5 minutes

---

### Task 4.3: Clean Up Config Module
- [ ] Remove `from app.services.locator import ServiceLocator` import
- [ ] Remove `service_locator = ServiceLocator()` line
- [ ] Remove any references to `service_locator`
- [ ] Verify `db_manager` and `db` still exported
- [ ] Run tests

**Agent:** Expert
**Estimated:** 15 minutes

---

### Task 4.4: Remove All Import References
- [ ] Search codebase for `service_locator` imports
- [ ] Remove all occurrences
- [ ] Search for `from app.server import deps`
- [ ] Remove all occurrences
- [ ] Run: `git grep "service_locator"` - should return empty
- [ ] Run: `git grep "from app.server import deps"` - should return empty

**Agent:** Expert
**Estimated:** 30 minutes

**Verification Commands:**
```bash
git grep "service_locator" # Should return nothing
git grep "from app.server import deps" # Should return nothing
git grep "ServiceLocator" # Should return nothing
```

---

### Task 4.5: Run Full Linting Suite
- [ ] Run `make lint` (or equivalent)
- [ ] Run `mypy app/`
- [ ] Run `pyright app/`
- [ ] Run `ruff check app/`
- [ ] Fix any errors found
- [ ] Commit fixes

**Agent:** Expert
**Estimated:** 30 minutes

---

### Task 4.6: Run Full Test Suite
- [ ] Run `make test` (or `uv run pytest`)
- [ ] Verify all tests pass
- [ ] Check test coverage
- [ ] Fix any failing tests
- [ ] Commit fixes

**Agent:** Testing
**Estimated:** 45 minutes

---

### Task 4.7: Manual Testing Checklist
- [ ] Start app: `uv run app run`
- [ ] Test home page loads
- [ ] Test chat interface
- [ ] Send product query ("I need a strong coffee")
- [ ] Verify ADK agent responds
- [ ] Check dashboard loads
- [ ] Verify metrics updating
- [ ] Test vector demo
- [ ] Check browser console for errors
- [ ] Check server logs for errors

**Agent:** Testing
**Estimated:** 30 minutes

---

## Phase 5: Testing & Documentation (3-4 hours)

### Task 5.1: Create Mock Provider Tests
- [ ] Create `tests/fixtures/mock_providers.py`
- [ ] Implement `MockSQLSpecProvider`
- [ ] Implement `MockServiceProvider`
- [ ] Create `test_container` fixture
- [ ] Add example tests

**Agent:** Testing
**Estimated:** 1 hour

---

### Task 5.2: Update Existing Tests
- [ ] Update service tests to use Dishka container
- [ ] Update controller tests to use DI
- [ ] Update ADK tool tests
- [ ] Remove service locator mocks
- [ ] Run all tests

**Agent:** Testing
**Estimated:** 2 hours

---

### Task 5.3: Performance Testing
- [ ] Benchmark response times before/after
- [ ] Compare memory usage
- [ ] Test concurrent requests
- [ ] Verify no regressions
- [ ] Document results

**Agent:** Testing
**Estimated:** 45 minutes

---

### Task 5.4: Update Documentation
- [ ] Update `AGENTS.md` with DI patterns
- [ ] Create `docs/guides/dependency-injection.md`
- [ ] Add examples of adding new services
- [ ] Add testing patterns
- [ ] Document clean import convention (`Inject` vs `FromDishka`)

**Agent:** Docs & Vision
**Estimated:** 1.5 hours

---

### Task 5.5: Code Review Checklist
- [ ] Verify all service locator code removed
- [ ] Verify clean imports used (`Inject` not `FromDishka`)
- [ ] Verify all endpoints use `@inject`
- [ ] Verify proper scopes (APP vs REQUEST)
- [ ] Verify no commented code
- [ ] Verify tests comprehensive
- [ ] Verify documentation complete

**Agent:** Docs & Vision
**Estimated:** 30 minutes

---

## Final Verification

### Checklist

- [ ] **Zero service locator references:** `git grep "service_locator"` returns empty
- [ ] **Zero old deps references:** `git grep "from app.server import deps"` returns empty
- [ ] **Clean imports:** All controllers use `from app.lib.di import Inject, inject`
- [ ] **All tests pass:** `make test` succeeds
- [ ] **Linters clean:** `make lint` succeeds
- [ ] **Manual testing complete:** All endpoints functional
- [ ] **Documentation updated:** DI guide exists
- [ ] **Performance verified:** No regressions
- [ ] **Git history clean:** Clear commit messages
- [ ] **Code reduction achieved:** Net -133 lines minimum

---

## Agent Assignments Summary

| Agent | Tasks | Est. Hours |
|-------|-------|------------|
| **Expert** | Setup, providers, controller migration, ADK tools, cleanup | 10-14 |
| **Testing** | Test migration, mock providers, performance testing | 4-5 |
| **Docs & Vision** | Documentation updates, code review | 2-3 |

**Total:** 16-22 hours

---

## Dependencies Between Tasks

```
Phase 1 (Setup)
  ├─ Task 1.1 (Install) ──┐
  ├─ Task 1.2 (DI module) ├─→ Phase 2 (Controllers)
  ├─ Task 1.3 (SQLSpec)   │
  ├─ Task 1.4 (Services)  │
  ├─ Task 1.5 (ADK)       │
  ├─ Task 1.6 (Context)   ├─→ Phase 3 (ADK Tools)
  └─ Task 1.7 (ASGI)      ┘

Phase 2 (Controllers) ──→ Phase 3 (ADK Tools)

Phase 3 (ADK Tools) ──→ Phase 4 (Cleanup)

Phase 4 (Cleanup) ──→ Phase 5 (Testing & Docs)
```

**Critical Path:** Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

---

## Notes

- Keep service locator intact until Phase 4
- Test each controller migration before moving to next
- ADK tools are critical - test thoroughly
- Document any issues in `progress.md`
- Update `recovery.md` after each phase
