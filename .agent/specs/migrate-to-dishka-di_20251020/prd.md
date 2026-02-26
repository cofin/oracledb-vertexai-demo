# Product Requirements Document: Dishka DI Migration

**Project:** Migrate from Service Locator to Dishka Dependency Injection
**Status:** Planning
**Created:** 2025-10-20
**Owner:** Engineering Team
**Estimated Effort:** 12-20 hours

---

## Executive Summary

Migrate the Litestar + SQLSpec application from a custom service locator pattern to Dishka dependency injection framework. This will eliminate architectural debt, improve testability, provide type-safe dependency resolution, and reduce code complexity by ~133 lines while following industry-standard DI patterns.

### Success Criteria

1. ✅ All services use Dishka DI instead of service locator
2. ✅ All controllers use `@inject` and `FromDishka[T]` annotations
3. ✅ ADK tool functions properly integrated with Dishka
4. ✅ Zero references to old service locator code remain
5. ✅ All existing tests pass with no regressions
6. ✅ Code reduction: -133 lines minimum
7. ✅ Full type safety maintained (mypy/pyright clean)

---

## 🔴 Critical Requirements

### Code Cleanup Policy

**REQUIREMENT:** Complete removal of old patterns - NO commenting out, NO leaving references.

When removing the service locator:
- ❌ **DO NOT** comment out old code
- ❌ **DO NOT** leave references or imports to removed modules
- ❌ **DO NOT** keep "backup" versions in the codebase
- ✅ **DO** completely delete files: `app/services/locator.py`, `app/server/deps.py`
- ✅ **DO** remove all imports of `service_locator` from `app/config.py`
- ✅ **DO** remove all import statements referencing deleted modules
- ✅ **DO** clean git history shows clear "remove service locator" commits

**Rationale:** Clean codebase, no confusion, no maintenance burden for dead code.

---

## Problem Statement

### Current Architecture Issues

**Service Locator Pattern (`app/services/locator.py` - 142 lines):**

```python
class ServiceLocator:
    def get(self, service_cls: type[T], session) -> T:
        # ❌ Hard-coded special cases for 8+ services
        if service_cls == IntentService:
            return IntentService(
                driver=session,
                exemplar_service=self.get(ExemplarService, session),
                vertex_ai_service=self.get(VertexAIService, session),
            )

        # ❌ Manual singleton tracking
        if service_cls in self._singletons:
            ...

        # ❌ Circular import workarounds
        from app.services.adk import AgentToolsService
```

**Problems:**

| Issue | Impact | Severity |
|-------|--------|----------|
| Implicit dependencies | Hard to understand service graph | High |
| Manual if/else for complex services (8+ cases) | Brittle, error-prone | High |
| No type safety for dependency graph | Runtime errors only | Medium |
| Hard to test (global state) | Low test coverage | High |
| Circular import issues | Fragile imports | Medium |
| 213 lines of boilerplate (locator + deps) | Maintenance burden | Medium |

### ADK Tool Integration Complexity

**Critical Issue:** `app/services/adk/tools.py` (132 lines)

```python
async def search_products_by_vector(query: str, ...) -> list[dict]:
    # ❌ Each tool function manually creates session
    async with db_manager.provide_session(db) as session:
        from app.config import service_locator
        tools_service = service_locator.get(AgentToolsService, session)
        return await tools_service.search_products_by_vector(...)
```

**7 tool functions** × **4 lines of boilerplate** = 28 lines of repetitive session management

**Problems:**
- Each tool creates its own DB session (inefficient)
- Service locator called in every tool
- No request-scoped session sharing
- Hard to test individual tools

---

## Proposed Solution

### Clean Import Convention

**Hide Dishka Implementation Details:**

To avoid polluting imports with `FromDishka` across the codebase, we'll create a clean re-export:

```python
# app/lib/di.py (NEW FILE)
"""Dependency injection utilities and clean imports."""

from dishka.integrations.litestar import (
    FromDishka as Inject,  # Clean name!
    inject,
    setup_dishka,
)

__all__ = ["Inject", "inject", "setup_dishka"]
```

**Usage in controllers:**

```python
from app.lib.di import Inject, inject  # Clean imports!

class CoffeeChatController(Controller):
    @post("/chat")
    @inject
    async def handle_chat(
        self,
        adk_runner: Inject[ADKRunner],  # Much cleaner than FromDishka!
        metrics: Inject[MetricsService],
    ) -> Response:
        ...
```

**Benefits:**
- ✅ Clean, readable import: `from app.lib.di import Inject, inject`
- ✅ Hides Dishka implementation details
- ✅ Easy to swap DI frameworks in future (just update `app/lib/di.py`)
- ✅ Consistent naming: `@inject` decorator + `Inject[T]` annotation

### Architecture Overview

**Dishka DI Pattern:**

```
┌─────────────────────────────────────────────────┐
│           Dishka Container                       │
│  ┌──────────────────────────────────────────┐   │
│  │  SQLSpecProvider (Scope.APP + REQUEST)   │   │
│  │    - db_manager (APP)                    │   │
│  │    - db_config (APP)                     │   │
│  │    - db_session (REQUEST) ←─────────┐   │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  CoreServiceProvider (REQUEST)           │   │
│  │    - ProductService ←────────────────┐   │   │
│  │    - CacheService                    │   │   │
│  │    - MetricsService                  │   │   │
│  │    - IntentService (auto-wired)      │   │   │
│  │    - AgentToolsService (auto-wired)  │   │   │
│  │    - VertexAIService (APP scope) ────┘   │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  ADKProvider (REQUEST)                   │   │
│  │    - ADKRunner                           │   │
│  │    - AgentToolsService (injected)        │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  Litestar Controllers (@inject)                  │
│    - CoffeeChatController                        │
│      @inject                                      │
│      async def handle_chat(                      │
│          adk_runner: FromDishka[ADKRunner],      │
│          metrics: FromDishka[MetricsService],    │
│      )                                            │
└─────────────────────────────────────────────────┘
```

### Key Design Decisions

#### 1. Provider Structure

**Three Providers:**

1. **SQLSpecProvider** - Database infrastructure (APP + REQUEST scopes)
2. **CoreServiceProvider** - Business services (REQUEST scope, VertexAI in APP scope)
3. **ADKProvider** - ADK-specific setup (REQUEST scope)

**Rationale:** Separation of concerns, clean dependency boundaries

#### 2. ADK Tool Integration Strategy

**Option A: Inject AgentToolsService into Tool Functions** ❌

```python
# Would require passing service through ADK tool system
async def search_products_by_vector(
    query: str,
    tools_service: AgentToolsService,  # ❌ ADK doesn't support this
) -> list[dict]:
    return await tools_service.search_products_by_vector(...)
```

**Problem:** ADK tool system doesn't support dependency injection in tool functions.

**Option B: Use Container Context (SELECTED)** ✅

```python
from dishka import FromDishka
from litestar import Request

# Store container in app state during setup
# Access in tool functions via request context

async def search_products_by_vector(query: str, ...) -> list[dict]:
    # Get container from Litestar app state
    container = get_container_from_context()
    async with container() as request_container:
        tools_service = await request_container.get(AgentToolsService)
        return await tools_service.search_products_by_vector(...)
```

**Rationale:** Works within ADK constraints, maintains clean DI, testable

**Option C: Make AgentToolsService a Module-Level Singleton** ❌

```python
# Global singleton
_tools_service: AgentToolsService | None = None

async def search_products_by_vector(query: str, ...) -> list[dict]:
    global _tools_service
    if not _tools_service:
        # Initialize...
    return await _tools_service.search_products_by_vector(...)
```

**Problem:** Breaks DI pattern, hard to test, session management issues

#### 3. Scope Strategy

| Service | Scope | Rationale |
|---------|-------|-----------|
| **SQLSpec Manager** | APP | Singleton, manages connection pool |
| **Database Config** | APP | Singleton, configuration |
| **Database Session** | REQUEST | Per-request, auto-cleanup |
| **VertexAIService** | APP | Singleton, no DB needed, thread-safe |
| **ProductService** | REQUEST | Needs DB session |
| **CacheService** | REQUEST | Needs DB session |
| **MetricsService** | REQUEST | Needs DB session |
| **IntentService** | REQUEST | Needs DB session + other services |
| **AgentToolsService** | REQUEST | Needs DB session + other services |
| **ADKRunner** | REQUEST | Per-request state management |

---

## Technical Specification

### File Changes

#### Files to CREATE

1. **`app/lib/di.py`** (~15 lines)
   - Re-export `FromDishka` as `Inject`
   - Re-export `inject` decorator
   - Re-export `setup_dishka`
   - Clean import interface

2. **`app/server/providers.py`** (~200 lines)
   - `SQLSpecProvider` class
   - `CoreServiceProvider` class
   - `ADKProvider` class
   - Container helper utilities

#### Files to MODIFY

1. **`app/asgi.py`** (~10 lines changed)
   - Import Dishka setup
   - Create container
   - Add lifespan handler
   - Call `setup_dishka()`

2. **`app/server/controllers.py`** (~50 lines changed)
   - Remove `dependencies` dict
   - Add `@inject` to all methods
   - Change type hints to `FromDishka[T]`

3. **`app/config.py`** (~5 lines changed)
   - Remove `service_locator` import
   - Remove `service_locator = ServiceLocator()` line

4. **`app/services/adk/tools.py`** (~30 lines changed)
   - Replace service locator calls with Dishka container access
   - Add container context helper
   - Maintain tool function signatures (ADK compatibility)

#### Files to DELETE (COMPLETELY)

1. **`app/services/locator.py`** (142 lines) - ❌ DELETE ENTIRELY
2. **`app/server/deps.py`** (71 lines) - ❌ DELETE ENTIRELY

**Total Code Change:** +200 new, -213 old = **-13 net lines** (plus improved architecture)

### Provider Implementation

#### SQLSpecProvider

```python
from dishka import Provider, provide, Scope
from typing import AsyncIterable
from sqlspec.base import SQLSpec
from sqlspec.driver import AsyncDriverAdapterBase

class SQLSpecProvider(Provider):
    """Provides SQLSpec database sessions with proper lifecycle."""

    @provide(scope=Scope.APP)
    def get_sqlspec_manager(self) -> SQLSpec:
        """Provide SQLSpec manager singleton."""
        from app.config import db_manager
        return db_manager

    @provide(scope=Scope.APP)
    def get_database_config(self):
        """Provide database configuration singleton."""
        from app.config import db
        return db

    @provide(scope=Scope.REQUEST)
    async def get_db_session(
        self,
        manager: SQLSpec,
        config,  # DatabaseConfig from app.config
    ) -> AsyncIterable[AsyncDriverAdapterBase]:
        """Provide SQLSpec async database session.

        This wraps SQLSpec's provide_session() context manager for
        automatic connection pooling and cleanup.
        """
        async with manager.provide_session(config) as session:
            yield session
            # SQLSpec handles connection return to pool
```

**Key Features:**
- ✅ Direct integration with SQLSpec's `provide_session()`
- ✅ Generator pattern for automatic cleanup
- ✅ APP-scoped singletons for manager/config
- ✅ REQUEST-scoped sessions (one per HTTP request)

#### CoreServiceProvider

```python
class CoreServiceProvider(Provider):
    """Provides core application services with automatic dependency resolution."""

    scope = Scope.REQUEST  # Default scope

    # Simple services (auto-wired by constructor)
    product_service = provide(ProductService)
    cache_service = provide(CacheService)
    metrics_service = provide(MetricsService)
    exemplar_service = provide(ExemplarService)
    store_service = provide(StoreService)

    # Complex services (auto-wired with multiple dependencies)
    intent_service = provide(IntentService)
    # IntentService.__init__(driver, exemplar_service, vertex_ai_service)
    # Dishka resolves all three automatically!

    agent_tools_service = provide(AgentToolsService)
    # AgentToolsService.__init__(driver, product_service, metrics_service, ...)
    # Dishka resolves all dependencies!

    @provide(scope=Scope.APP)
    def get_vertex_ai_service(self) -> VertexAIService:
        """Singleton VertexAI service (no DB session needed)."""
        return VertexAIService()

    @provide(scope=Scope.REQUEST)
    def get_vector_search_service(
        self,
        product_service: ProductService,
        vertex_ai_service: VertexAIService,
        cache_service: CacheService,
    ) -> OracleVectorSearchService:
        """Vector search service with mixed-scope dependencies."""
        return OracleVectorSearchService(
            products_service=product_service,
            vertex_ai_service=vertex_ai_service,
            embedding_cache=cache_service,
        )
```

**Key Features:**
- ✅ Auto-wiring for services with simple dependencies
- ✅ Explicit providers for complex initialization
- ✅ Mixed APP/REQUEST scope support
- ✅ Replaces 8+ special cases in service locator with clean declarations

#### ADKProvider

```python
class ADKProvider(Provider):
    """Provides ADK-specific services."""

    @provide(scope=Scope.REQUEST)
    def get_adk_runner(self) -> ADKRunner:
        """ADK agent runner (manages its own session service)."""
        return ADKRunner()
```

**Note:** ADKRunner creates its own `SQLSpecSessionService` internally - no changes needed.

### Controller Migration Pattern

**Before (Service Locator):**

```python
from litestar.di import Provide
from app.server import deps

class CoffeeChatController(Controller):
    dependencies = {
        "adk_runner": Provide(deps.provide_adk_runner),
        "metrics_service": Provide(deps.provide_metrics_service),
        "cache_service": Provide(deps.provide_cache_service),
    }

    @get("/dashboard")
    async def performance_dashboard(
        self,
        metrics_service: MetricsService,  # ← Implicit injection
    ) -> HTMXTemplate:
        metrics = await metrics_service.get_performance_stats(hours=24)
        return HTMXTemplate(...)
```

**After (Dishka DI):**

```python
from app.lib.di import Inject, inject  # Clean imports!

class CoffeeChatController(Controller):
    # ✅ No dependencies dict!

    @get("/dashboard")
    @inject  # ← Mark for DI
    async def performance_dashboard(
        self,
        metrics_service: Inject[MetricsService],  # ← Explicit DI (clean!)
    ) -> HTMXTemplate:
        metrics = await metrics_service.get_performance_stats(hours=24)
        return HTMXTemplate(...)
```

**Changes Per Endpoint:**
1. Remove from `dependencies` dict (if present)
2. Add `@inject` decorator
3. Change `Service` → `Inject[Service]` (imported from `app.lib.di`)

**Total:** ~10 endpoints in `CoffeeChatController`

### ADK Tools Integration

**Challenge:** ADK tool functions are called by Google ADK framework, which doesn't support DI.

**Solution:** Store Dishka container in Litestar app state, access in tools.

**Implementation:**

```python
# app/server/providers.py
from contextvars import ContextVar
from dishka import AsyncContainer

_request_container: ContextVar[AsyncContainer | None] = ContextVar(
    '_request_container', default=None
)

def get_request_container() -> AsyncContainer:
    """Get the current request-scoped Dishka container."""
    container = _request_container.get()
    if container is None:
        msg = "No active Dishka request container"
        raise RuntimeError(msg)
    return container

def set_request_container(container: AsyncContainer) -> None:
    """Set the current request-scoped container (called by middleware)."""
    _request_container.set(container)
```

**Modified Tool Function:**

```python
# app/services/adk/tools.py
from app.server.providers import get_request_container
from app.services.adk.tool_service import AgentToolsService

async def search_products_by_vector(
    query: str,
    limit: int,
    similarity_threshold: float,
) -> list[dict[str, Any]]:
    """Search for coffee products using vector similarity."""
    limit = limit or 5
    similarity_threshold = similarity_threshold or 0.7

    # Get Dishka container from context
    container = get_request_container()

    # Resolve service from container
    tools_service = await container.get(AgentToolsService)

    result = await tools_service.search_products_by_vector(
        query, limit, similarity_threshold
    )
    return result["products"]
```

**Benefits:**
- ✅ No manual session management
- ✅ Service properly injected with all dependencies
- ✅ Testable (can mock container)
- ✅ Maintains ADK tool signature compatibility

---

## Migration Strategy

### Phase 1: Setup (2-3 hours)

**Tasks:**
1. Install Dishka: `uv add dishka`
2. Create `app/server/providers.py` with initial providers
3. Update `app/asgi.py` to setup Dishka container
4. Add lifespan handler for container cleanup
5. Verify app still starts (both systems running)

**Acceptance:**
- App starts without errors
- Both service locator and Dishka providers exist
- No functional changes yet

### Phase 2: Controller Migration (4-6 hours)

**Tasks:**
1. Migrate `CoffeeChatController` methods one-by-one
2. Test each endpoint after migration
3. Verify all 10 endpoints work with Dishka

**Order:**
1. Simple endpoints first (`/`, `/dashboard`)
2. Complex endpoints next (`/api/vector-demo`, `/chat/stream`)
3. Helper endpoints last (`/metrics`, `/api/help/query-log`)

**Acceptance:**
- All endpoints functional
- No service locator calls in controllers
- All tests pass

### Phase 3: ADK Tools Migration (3-4 hours)

**Tasks:**
1. Implement container context helpers
2. Update all 7 tool functions
3. Test ADK agent flow end-to-end
4. Verify session management works

**Acceptance:**
- All tool functions use Dishka container
- No service locator calls in tools
- ADK agent responses work correctly

### Phase 4: Complete Cleanup (2-3 hours)

**Tasks:**
1. **DELETE** `app/services/locator.py` entirely
2. **DELETE** `app/server/deps.py` entirely
3. Remove `service_locator` from `app/config.py`
4. Remove all imports of deleted modules
5. Run full test suite
6. Run linters (mypy, pyright, ruff)
7. Update documentation

**Acceptance:**
- ✅ Zero references to `service_locator` in codebase
- ✅ No import errors
- ✅ All tests pass
- ✅ Linters clean
- ✅ `git grep "service_locator"` returns empty
- ✅ `git grep "from app.server import deps"` returns empty

### Phase 5: Testing & Validation (3-4 hours)

**Tasks:**
1. Run full test suite
2. Manual testing of all endpoints
3. Performance testing (ensure no regressions)
4. Update integration tests
5. Document new DI patterns

**Acceptance:**
- All tests pass
- No performance regressions
- Documentation updated

**Total Estimated Time:** 14-20 hours

---

## Testing Strategy

### Unit Tests

**Mock Providers:**

```python
import pytest
from dishka import Provider, provide, Scope, make_async_container
from unittest.mock import AsyncMock

class MockSQLSpecProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def get_mock_db_session(self):
        mock_driver = AsyncMock(spec=AsyncDriverAdapterBase)
        mock_driver.select.return_value = [...]
        return mock_driver

class MockServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_product_service(self, driver):
        return ProductService(driver)

@pytest.fixture
async def test_container():
    container = make_async_container(
        MockSQLSpecProvider(),
        MockServiceProvider(),
    )
    yield container
    await container.close()

@pytest.mark.asyncio
async def test_product_service(test_container):
    async with test_container() as request_container:
        service = await request_container.get(ProductService)
        result = await service.get_all()
        assert len(result) > 0
```

### Integration Tests

**Real Container:**

```python
@pytest.fixture
async def app_container():
    container = make_async_container(
        SQLSpecProvider(),
        CoreServiceProvider(),
        ADKProvider(),
    )
    yield container
    await container.close()

@pytest.mark.asyncio
async def test_full_chat_flow(app_container):
    async with app_container() as request_container:
        adk_runner = await request_container.get(ADKRunner)
        result = await adk_runner.process_request(
            query="I need a strong coffee",
            user_id="test_user",
        )
        assert "answer" in result
        assert result["answer"]
```

### ADK Tool Tests

```python
from app.server.providers import set_request_container
from app.services.adk import tools

@pytest.mark.asyncio
async def test_search_products_tool(app_container):
    async with app_container() as request_container:
        # Set container in context
        set_request_container(request_container)

        # Call tool function
        results = await tools.search_products_by_vector(
            query="strong coffee",
            limit=5,
            similarity_threshold=0.7,
        )

        assert len(results) > 0
        assert "name" in results[0]
```

---

## Risks & Mitigations

### Risk 1: ADK Tool Integration Breaks

**Likelihood:** Medium
**Impact:** High

**Mitigation:**
- Test ADK tools early in Phase 3
- Keep service locator until ADK tools confirmed working
- Implement container context carefully
- Add extensive logging for debugging

### Risk 2: Session Lifecycle Issues

**Likelihood:** Low
**Impact:** High

**Mitigation:**
- SQLSpec's `provide_session()` is battle-tested
- Dishka's generator pattern matches SQLSpec perfectly
- Add session lifecycle logging
- Test with concurrent requests

### Risk 3: Circular Dependency Discovery

**Likelihood:** Low
**Impact:** Medium

**Mitigation:**
- Service locator currently handles circular imports via lazy imports
- Dishka may surface hidden circular dependencies
- If discovered, refactor service dependencies
- This is actually a benefit (surfaces design issues)

### Risk 4: Performance Regression

**Likelihood:** Very Low
**Impact:** Medium

**Mitigation:**
- Dishka overhead: ~1-2ms per request (negligible)
- SQLSpec session pooling unchanged
- Benchmark before/after migration
- Monitor production metrics

---

## Success Metrics

### Code Quality

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Lines of boilerplate | 213 | ~80 | < 100 |
| Special-case if/else | 8+ | 0 | 0 |
| Type safety | Partial | Full | 100% |
| Circular imports | 3 | 0 | 0 |
| Test coverage | 70% | 85% | > 80% |

### Developer Experience

- ✅ Clear dependency graph (constructor parameters)
- ✅ Easy to add new services (auto-wiring)
- ✅ Easy to test (mock providers)
- ✅ IDE autocomplete for injected services
- ✅ No manual session management

### Production Metrics

- ✅ No increase in response time (< 2ms overhead)
- ✅ No increase in error rate
- ✅ Same connection pool behavior
- ✅ All existing functionality works

---

## Dependencies

### Package Requirements

```toml
[project.dependencies]
dishka = "^1.3.0"  # Latest stable version
```

**Note:** Check latest version at time of implementation.

### Python Version

- Requires Python 3.11+ (already met)
- Full async/await support
- Type hints support

---

## Documentation Updates

### Files to Update

1. **`AGENTS.md`** - Document new DI patterns
2. **`docs/architecture.md`** (if exists) - Update DI section
3. **Developer guide** - Add Dishka usage examples
4. **Testing guide** - Add mock provider examples

### New Documentation

1. **`docs/guides/dependency-injection.md`**
   - Dishka setup and usage
   - Adding new services
   - Testing patterns
   - Troubleshooting

---

## Future Enhancements

### Post-Migration Improvements

1. **WebSocket Support** - Add `Scope.SESSION` for WebSocket connections
2. **Background Tasks** - Add providers for Celery/AsyncIO tasks
3. **Multi-Tenancy** - Add tenant-scoped providers
4. **Feature Flags** - Inject feature flag service
5. **Observability** - Inject tracing/metrics collectors

### Potential Optimizations

1. **Lazy Loading** - Use `@provide(lazy=True)` for expensive services
2. **Caching** - Add provider-level caching for expensive initialization
3. **Connection Pooling** - Fine-tune SQLSpec pool settings with Dishka scopes

---

## Rollback Plan

### If Migration Fails

**Phase 1-2 Rollback:**
- Keep service locator code intact until Phase 4
- Can revert controller changes easily
- No data loss risk

**Phase 3-4 Rollback:**
- Git revert to before deletion
- Restore `locator.py` and `deps.py`
- Restore imports in `config.py`
- Re-run tests

**Rollback Time:** < 1 hour

---

## Approval & Sign-Off

### Review Checklist

- [ ] Architecture reviewed
- [ ] Migration strategy approved
- [ ] Cleanup policy understood (complete deletion, no comments)
- [ ] Testing strategy approved
- [ ] Timeline acceptable
- [ ] Risk mitigations acceptable

### Stakeholders

- **Engineering Lead:** [Name]
- **Backend Engineers:** [Names]
- **QA Lead:** [Name]

---

## Appendix A: Service Dependency Graph

### Current Dependencies (Service Locator)

```
ProductService
  └─ AsyncDriverAdapterBase (DB session)

CacheService
  └─ AsyncDriverAdapterBase

MetricsService
  └─ AsyncDriverAdapterBase

ExemplarService
  └─ AsyncDriverAdapterBase

StoreService
  └─ AsyncDriverAdapterBase

VertexAIService
  └─ (no dependencies) → Singleton

IntentService
  ├─ AsyncDriverAdapterBase
  ├─ ExemplarService
  └─ VertexAIService

AgentToolsService
  ├─ AsyncDriverAdapterBase
  ├─ ProductService
  ├─ MetricsService
  ├─ IntentService
  ├─ VertexAIService
  └─ StoreService

OracleVectorSearchService
  ├─ ProductService
  ├─ VertexAIService
  └─ CacheService

ADKRunner
  └─ (creates own session service)
```

### Dishka Scope Assignments

**APP Scope (Singletons):**
- SQLSpec Manager
- Database Config
- VertexAIService

**REQUEST Scope (Per-Request):**
- Database Session (AsyncDriverAdapterBase)
- ProductService
- CacheService
- MetricsService
- ExemplarService
- StoreService
- IntentService (auto-wired)
- AgentToolsService (auto-wired)
- OracleVectorSearchService (explicit provider)
- ADKRunner

---

## Appendix B: Code Examples

See research document: `specs/active/migrate-to-dishka-di/research/dishka-patterns.md`

### Key Examples

1. **SQLSpec Provider with `provide_session()`** - Section 3.2
2. **Auto-Wiring Complex Services** - Section 4.1
3. **Controller Migration** - Section 6.3
4. **Testing with Mock Providers** - Section 5.1

---

## Appendix C: Reference Links

### Official Documentation

- **Dishka Docs:** https://dishka.readthedocs.io/en/stable/
- **Litestar Integration:** https://dishka.readthedocs.io/en/stable/integrations/litestar.html
- **SQLSpec Docs:** (internal)

### Example Repositories

- **litestar_dishka_modular:** https://gitlab.bartab.fr/oss-public/litestar_dishka_modular
  - Uses SQLSpec (not SQLAlchemy)
  - Clean provider patterns
  - Production-ready structure

---

**Document Version:** 1.0
**Last Updated:** 2025-10-20
**Next Review:** After Phase 2 completion
