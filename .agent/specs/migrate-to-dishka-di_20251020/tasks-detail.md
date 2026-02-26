# Detailed Task Breakdown: Dishka DI Migration

**Project:** Migrate to Dishka Dependency Injection
**Last Updated:** 2025-10-20

This document provides step-by-step implementation details for each task in the migration.

---

## Phase 1: Setup & Foundation

### Task 1.2: Create DI Module with Clean Imports

**File:** `app/lib/di.py` (NEW)

**Implementation:**

```python
"""Dependency injection utilities and clean imports.

This module provides a clean interface to the underlying DI framework
(Dishka) without exposing implementation details throughout the codebase.

By re-exporting with cleaner names, we:
- Hide implementation details (Dishka could be swapped later)
- Provide cleaner, more readable imports
- Maintain consistency with naming: @inject decorator + Inject[T] annotation

Example:
    from app.lib.di import Inject, inject

    class MyController(Controller):
        @get("/")
        @inject
        async def handler(self, service: Inject[MyService]) -> Response:
            return await service.do_something()
"""

from dishka.integrations.litestar import (
    FromDishka as Inject,  # Renamed for cleaner imports
    inject,
    setup_dishka,
)

__all__ = ["Inject", "inject", "setup_dishka"]
```

**Verification:**
```bash
# Test import works
uv run python -c "from app.lib.di import Inject, inject, setup_dishka; print('✓ DI module works')"
```

---

### Task 1.3: Create SQLSpec Provider

**File:** `app/server/providers.py` (NEW - Part 1)

**Implementation:**

```python
"""Dishka dependency injection providers for SQLSpec + Litestar.

This module defines all DI providers for the application, organized by concern:
- SQLSpecProvider: Database infrastructure (sessions, config)
- CoreServiceProvider: Business services (products, metrics, etc.)
- ADKProvider: ADK-specific services

The providers use Dishka's scope system:
- Scope.APP: Application-wide singletons (created once)
- Scope.REQUEST: Request-scoped (created per HTTP request, auto-cleanup)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterable
from contextvars import ContextVar

from dishka import Provider, Scope, provide

if TYPE_CHECKING:
    from sqlspec.base import SQLSpec
    from sqlspec.driver import AsyncDriverAdapterBase
    from dishka import AsyncContainer


class SQLSpecProvider(Provider):
    """Provides SQLSpec database sessions with proper lifecycle.

    Uses SQLSpec's built-in provide_session() context manager for
    connection pooling and automatic cleanup.

    Scopes:
    - APP: db_manager and db_config (singletons)
    - REQUEST: database sessions (one per HTTP request)
    """

    @provide(scope=Scope.APP)
    def get_sqlspec_manager(self) -> SQLSpec:
        """Provide SQLSpec manager singleton.

        This is the global db_manager that handles:
        - Connection pooling
        - SQL file loading
        - Database configuration

        Returns:
            SQLSpec instance managing database connections.
        """
        from app.config import db_manager
        return db_manager

    @provide(scope=Scope.APP)
    def get_database_config(self):
        """Provide database configuration singleton.

        Contains:
        - Connection string
        - Pool settings
        - Driver configuration

        Returns:
            DatabaseConfig instance (OracleConfig from app.config).
        """
        from app.config import db
        return db

    @provide(scope=Scope.REQUEST)
    async def get_db_session(
        self,
        manager: SQLSpec,
        config,  # DatabaseConfig type (OracleConfig)
    ) -> AsyncIterable[AsyncDriverAdapterBase]:
        """Provide SQLSpec async database session.

        This wraps SQLSpec's provide_session() context manager, which:
        1. Acquires connection from pool
        2. Yields AsyncDriverAdapterBase (OracleAsyncDriver)
        3. Automatically returns connection to pool on cleanup

        The session is REQUEST-scoped, so each HTTP request gets its own
        database connection, properly cleaned up after response.

        Args:
            manager: SQLSpec instance (from get_sqlspec_manager)
            config: Database configuration (from get_database_config)

        Yields:
            AsyncDriverAdapterBase: Database session for this request
        """
        async with manager.provide_session(config) as session:
            yield session
            # SQLSpec handles connection return to pool and cleanup
```

**Key Points:**
- Generator function with `async with` + `yield` for cleanup
- Perfectly matches SQLSpec's `provide_session()` pattern
- APP scope for singletons, REQUEST scope for sessions

---

### Task 1.4: Create Core Service Provider

**File:** `app/server/providers.py` (NEW - Part 2, append)

**Implementation:**

```python
class CoreServiceProvider(Provider):
    """Provides core application services with automatic dependency resolution.

    Services are organized by complexity:
    - Simple services: Only need AsyncDriverAdapterBase (auto-wired)
    - Complex services: Need multiple dependencies (auto-wired)
    - Singleton services: APP-scoped (VertexAIService)
    - Mixed-scope services: Explicit provider (OracleVectorSearchService)

    Auto-wiring: Dishka inspects constructor signatures and automatically
    resolves dependencies. For example:
        ProductService.__init__(self, driver: AsyncDriverAdapterBase)
    Dishka sees it needs AsyncDriverAdapterBase and injects the session
    from SQLSpecProvider.get_db_session().
    """

    scope = Scope.REQUEST  # Default scope for all services

    # Simple services with only driver dependency (auto-wired)
    # These all have: __init__(self, driver: AsyncDriverAdapterBase)
    product_service = provide(ProductService)
    cache_service = provide(CacheService)
    metrics_service = provide(MetricsService)
    exemplar_service = provide(ExemplarService)
    store_service = provide(StoreService)

    # Complex services with multiple dependencies (auto-wired!)
    # IntentService.__init__(driver, exemplar_service, vertex_ai_service)
    # Dishka automatically resolves all three dependencies
    intent_service = provide(IntentService)

    # AgentToolsService.__init__(driver, product_service, metrics_service, ...)
    # Dishka automatically resolves all dependencies
    adk_tools_service = provide(AgentToolsService)

    @provide(scope=Scope.APP)
    def get_vertex_ai_service(self) -> VertexAIService:
        """Singleton VertexAI service (no DB session needed).

        This is APP-scoped because:
        1. It doesn't need a database connection
        2. It can be safely shared across requests (thread-safe)
        3. Creating it once saves initialization overhead

        Returns:
            VertexAIService instance (singleton)
        """
        from app.services import VertexAIService
        return VertexAIService()

    @provide(scope=Scope.REQUEST)
    def get_vector_search_service(
        self,
        product_service: ProductService,  # REQUEST-scoped (needs DB)
        vertex_ai_service: VertexAIService,  # APP-scoped (singleton)
        cache_service: CacheService,  # REQUEST-scoped (needs DB)
    ) -> OracleVectorSearchService:
        """Vector search service with mixed-scope dependencies.

        This service demonstrates mixing APP and REQUEST scopes:
        - ProductService: REQUEST-scoped (needs DB session)
        - VertexAIService: APP-scoped (singleton, no DB)
        - CacheService: REQUEST-scoped (needs DB session)

        Dishka automatically resolves and injects all three, respecting
        their individual scope requirements.

        Args:
            product_service: Product database service
            vertex_ai_service: Vertex AI API service
            cache_service: Caching service

        Returns:
            OracleVectorSearchService instance for this request
        """
        from app.services.vertex_ai import OracleVectorSearchService
        return OracleVectorSearchService(
            products_service=product_service,
            vertex_ai_service=vertex_ai_service,
            embedding_cache=cache_service,
        )


# Add imports at top of file
from app.services import (
    CacheService,
    ExemplarService,
    MetricsService,
    ProductService,
    StoreService,
    VertexAIService,
)
from app.services.intent import IntentService
from app.services.adk.tool_service import AgentToolsService
from app.services.vertex_ai import OracleVectorSearchService
```

**Key Points:**
- Simple `provide(ServiceClass)` for auto-wiring
- Explicit providers for complex initialization
- Mixed APP/REQUEST scope support

---

### Task 1.5: Create ADK Provider

**File:** `app/server/providers.py` (Part 3, append)

**Implementation:**

```python
class ADKProvider(Provider):
    """Provides ADK-specific services.

    ADKRunner manages its own SQLSpec session service internally
    (via SQLSpecSessionService), so it doesn't need the standard
    database session injection.
    """

    @provide(scope=Scope.REQUEST)
    def get_adk_runner(self) -> ADKRunner:
        """ADK agent runner (manages its own session service).

        ADKRunner creates its own SQLSpecSessionService internally,
        which handles database sessions for ADK conversation storage.

        Returns:
            ADKRunner instance for this request
        """
        from app.services.adk import ADKRunner
        return ADKRunner()


# Add import at top
from app.services.adk import ADKRunner
```

---

### Task 1.6: Add Container Context Helpers

**File:** `app/server/providers.py` (Part 4, append to end)

**Implementation:**

```python
# Container context for ADK tools
# ADK tool functions need access to the Dishka container but are called
# by the Google ADK framework (which doesn't support DI). We use a
# ContextVar to store the current request's container.

_request_container: ContextVar[AsyncContainer | None] = ContextVar(
    '_request_container',
    default=None,
)


def get_request_container() -> AsyncContainer:
    """Get the current request-scoped Dishka container.

    This is used by ADK tool functions to access services without
    manual session management.

    Returns:
        AsyncContainer for the current request

    Raises:
        RuntimeError: If no container is set (not in request context)
    """
    container = _request_container.get()
    if container is None:
        msg = "No active Dishka request container. Ensure middleware is configured."
        raise RuntimeError(msg)
    return container


def set_request_container(container: AsyncContainer) -> None:
    """Set the current request-scoped container.

    This is called by Dishka middleware at the start of each request.

    Args:
        container: The request-scoped container to store
    """
    _request_container.set(container)


def clear_request_container() -> None:
    """Clear the current request-scoped container.

    This is called by Dishka middleware at the end of each request.
    """
    _request_container.set(None)
```

**Usage in ADK Tools:**

```python
# app/services/adk/tools.py
from app.server.providers import get_request_container

async def search_products_by_vector(query: str, ...) -> list[dict]:
    container = get_request_container()
    tools_service = await container.get(AgentToolsService)
    return await tools_service.search_products_by_vector(...)
```

---

### Task 1.7: Update ASGI App Setup

**File:** `app/asgi.py`

**Changes:**

```python
# ADD these imports at top
from contextlib import asynccontextmanager
from dishka import make_async_container
from dishka.integrations.litestar import LitestarProvider

from app.lib.di import setup_dishka
from app.server.providers import (
    SQLSpecProvider,
    CoreServiceProvider,
    ADKProvider,
)


# ADD this lifespan handler
@asynccontextmanager
async def dishka_lifespan(app: Litestar):
    """Manage Dishka container lifecycle.

    This lifespan handler ensures the Dishka container is properly
    closed when the application shuts down, releasing all resources.
    """
    yield
    # Cleanup container on shutdown
    await app.state.dishka_container.close()


def create_app() -> Litestar:
    """Create ASGI application with Dishka DI."""

    from litestar import Litestar

    from app.lib.settings import get_settings
    from app.server import plugins

    settings = get_settings()

    # CREATE Dishka container with all providers
    container = make_async_container(
        SQLSpecProvider(),  # Database session management
        CoreServiceProvider(),  # Application services
        ADKProvider(),  # ADK-specific services
        LitestarProvider(),  # Enables access to Request/Response in providers
    )

    # CREATE Litestar app
    app = Litestar(
        debug=settings.app.DEBUG,
        plugins=[plugins.app_config],
        lifespan=[dishka_lifespan],  # ADD cleanup handler
    )

    # SETUP Dishka integration (adds middleware)
    setup_dishka(container=container, app=app)

    return app


app = create_app()
```

**Verification:**
```bash
# App should start without errors
uv run app run

# Check logs for Dishka initialization
# Should see no errors related to DI
```

---

## Phase 2: Controller Migration

### Task 2.1: Migrate Simple Endpoints

**File:** `app/server/controllers.py`

**Endpoints:** `/`, `/favicon.ico`

**Changes for `/`:**

```python
# ADD import at top
from app.lib.di import Inject, inject

class CoffeeChatController(Controller):
    # ... existing code ...

    @get(path="/", name="coffee_chat.show")
    # NO @inject needed - no injected dependencies
    async def show_coffee_chat(self) -> HTMXTemplate:
        """Serve site root with CSP nonce."""
        return HTMXTemplate(
            template_name="coffee_chat.html",
            context={"csp_nonce": self.generate_csp_nonce()},
            headers={...},
        )
```

**Note:** `/` endpoint has no injected dependencies, so no changes needed.

**Changes for `/favicon.ico`:**

No changes needed - no dependencies.

---

### Task 2.2: Migrate Dashboard Endpoints

**Endpoint:** `/dashboard`

**Before:**

```python
class CoffeeChatController(Controller):
    dependencies = {
        "metrics_service": Provide(deps.provide_metrics_service),
        # ... other dependencies ...
    }

    @get(path="/dashboard", name="performance_dashboard")
    async def performance_dashboard(
        self,
        metrics_service: MetricsService  # Implicit injection
    ) -> HTMXTemplate:
        metrics = await metrics_service.get_performance_stats(hours=24)
        return HTMXTemplate(...)
```

**After:**

```python
class CoffeeChatController(Controller):
    # dependencies dict stays for now (will remove in Task 2.6)

    @get(path="/dashboard", name="performance_dashboard")
    @inject  # ADD decorator
    async def performance_dashboard(
        self,
        metrics_service: Inject[MetricsService],  # CHANGE type hint
    ) -> HTMXTemplate:
        metrics = await metrics_service.get_performance_stats(hours=24)
        return HTMXTemplate(...)
```

**Test:**
```bash
curl http://localhost:5006/dashboard
# Should return dashboard HTML
```

---

### Task 2.3: Migrate Chat Endpoints

**Endpoint:** `/` (POST)

**Before:**

```python
@post(path="/", name="coffee_chat.get")
async def handle_coffee_chat(
    self,
    data: Annotated[schemas.CoffeeChatMessage, Body(...)],
    adk_runner: ADKRunner,  # From dependencies dict
    request: HTMXRequest,
) -> HTMXTemplate:
    # ... existing code ...
```

**After:**

```python
@post(path="/", name="coffee_chat.get")
@inject  # ADD
async def handle_coffee_chat(
    self,
    data: Annotated[schemas.CoffeeChatMessage, Body(...)],
    adk_runner: Inject[ADKRunner],  # CHANGE
    request: HTMXRequest,
) -> HTMXTemplate:
    # ... existing code unchanged ...
```

**Test:**
```bash
curl -X POST http://localhost:5006/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=I need a strong coffee"
# Should return AI response
```

---

### Task 2.4: Migrate Vector Demo Endpoint

**Endpoint:** `/api/vector-demo`

**Before:**

```python
@post(path="/api/vector-demo", name="vector.demo")
async def vector_search_demo(
    self,
    data: Annotated[schemas.VectorDemoRequest, Body(...)],
    vertex_ai_service: VertexAIService,
    vector_search_service: OracleVectorSearchService,
    metrics_service: MetricsService,
    request: HTMXRequest,
) -> HTMXTemplate:
    # ... existing code ...
```

**After:**

```python
@post(path="/api/vector-demo", name="vector.demo")
@inject  # ADD
async def vector_search_demo(
    self,
    data: Annotated[schemas.VectorDemoRequest, Body(...)],
    vertex_ai_service: Inject[VertexAIService],  # CHANGE
    vector_search_service: Inject[OracleVectorSearchService],  # CHANGE
    metrics_service: Inject[MetricsService],  # CHANGE
    request: HTMXRequest,
) -> HTMXTemplate:
    # ... existing code unchanged ...
```

---

### Task 2.6: Remove Controller Dependencies Dict

**File:** `app/server/controllers.py`

**Remove:**

```python
class CoffeeChatController(Controller):
    dependencies = {  # DELETE THIS ENTIRE DICT
        "adk_runner": Provide(deps.provide_adk_runner),
        "vertex_ai_service": Provide(deps.provide_vertex_ai_service),
        "vector_search_service": Provide(deps.provide_oracle_vector_search_service),
        "products_service": Provide(deps.provide_product_service),
        "cache_service": Provide(deps.provide_cache_service),
        "metrics_service": Provide(deps.provide_metrics_service),
        "exemplar_service": Provide(deps.provide_exemplar_service),
    }
```

**Remove Import:**

```python
from app.server import deps  # DELETE
```

**Verification:**
```bash
# All endpoints should still work
make test
```

---

## Phase 3: ADK Tools Migration

### Task 3.1: Update ADK Tool Functions - Part 1

**File:** `app/services/adk/tools.py`

**Add Import at Top:**

```python
from app.server.providers import get_request_container
```

**Update `search_products_by_vector`:**

**Before:**

```python
async def search_products_by_vector(
    query: str,
    limit: int,
    similarity_threshold: float,
) -> list[dict[str, Any]]:
    """Search for coffee products using vector similarity with fresh session."""
    limit = limit or 5
    similarity_threshold = similarity_threshold or 0.7
    async with db_manager.provide_session(db) as session:
        from app.config import service_locator
        tools_service = service_locator.get(AgentToolsService, session)
        result = await tools_service.search_products_by_vector(
            query, limit, similarity_threshold
        )
        return cast("list[dict[str, Any]]", result["products"])
```

**After:**

```python
async def search_products_by_vector(
    query: str,
    limit: int,
    similarity_threshold: float,
) -> list[dict[str, Any]]:
    """Search for coffee products using vector similarity."""
    # Apply defaults
    limit = limit or 5
    similarity_threshold = similarity_threshold or 0.7

    # Get Dishka container from request context
    container = get_request_container()

    # Resolve service (Dishka handles session injection)
    tools_service = await container.get(AgentToolsService)

    # Execute search
    result = await tools_service.search_products_by_vector(
        query, limit, similarity_threshold
    )
    return cast("list[dict[str, Any]]", result["products"])
```

**Key Changes:**
1. Remove `db_manager.provide_session()` - Dishka handles this
2. Remove `service_locator.get()` - Use Dishka container
3. Add `get_request_container()` call
4. Add `await container.get(AgentToolsService)`

**Apply same pattern to `get_product_details`:**

```python
async def get_product_details(product_id: str) -> dict[str, Any]:
    """Get detailed information about a specific product by ID or name."""
    container = get_request_container()
    tools_service = await container.get(AgentToolsService)
    return await tools_service.get_product_details(product_id)
```

---

### Task 3.2: Update ADK Tool Functions - Part 2

**Update `classify_intent`:**

```python
async def classify_intent(query: str) -> dict[str, Any]:
    """Classify user intent using vector-based classification."""
    container = get_request_container()
    tools_service = await container.get(AgentToolsService)
    return await tools_service.classify_intent(query)
```

**Update `record_search_metric`:**

```python
async def record_search_metric(
    session_id: str,
    query_text: str,
    intent: str,
    response_time_ms: float,
    vector_search_time_ms: int = 0,
    vector_results_json: str = "[]",
) -> dict[str, Any]:
    """Record metrics for search performance."""
    container = get_request_container()
    tools_service = await container.get(AgentToolsService)

    # Decode JSON string to list
    vector_results = from_json(vector_results_json) if vector_results_json else []

    return await tools_service.record_search_metric(
        session_id=session_id,
        query_text=query_text,
        intent=intent,
        vector_results=vector_results,
        total_response_time_ms=int(response_time_ms),
        vector_search_time_ms=vector_search_time_ms,
    )
```

---

### Task 3.3: Update ADK Tool Functions - Part 3

**Update `get_store_locations`:**

```python
async def get_store_locations() -> list[dict[str, Any]]:
    """Get all store locations and information."""
    container = get_request_container()
    tools_service = await container.get(AgentToolsService)
    return await tools_service.get_all_store_locations()
```

**Update `find_stores_by_location`:**

```python
async def find_stores_by_location(
    city: str = "",
    state: str = ""
) -> list[dict[str, Any]]:
    """Find stores in a specific location."""
    container = get_request_container()
    tools_service = await container.get(AgentToolsService)

    # Convert empty strings to None
    city_filter = city if city else None
    state_filter = state if state else None

    return await tools_service.find_stores_by_location(city_filter, state_filter)
```

**Update `get_store_hours`:**

```python
async def get_store_hours(store_id: int) -> dict[str, Any]:
    """Get store hours for a specific store."""
    container = get_request_container()
    tools_service = await container.get(AgentToolsService)
    return await tools_service.get_store_hours(store_id)
```

---

### Task 3.5: Setup Container Context in ADK Flow

**Note:** Dishka middleware automatically handles this. If ADK tools fail, you may need to add explicit middleware:

**File:** `app/server/middleware.py` (NEW if needed)

```python
from litestar.types import ASGIApp, Receive, Scope, Send
from app.server.providers import set_request_container, clear_request_container


class DishkaContextMiddleware:
    """Middleware to set Dishka container in context for ADK tools."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] == "http":
            # Get container from app state
            container = scope["app"].state.dishka_container
            # Create request-scoped container
            async with container() as request_container:
                # Set in context for ADK tools
                set_request_container(request_container)
                try:
                    await self.app(scope, receive, send)
                finally:
                    clear_request_container()
        else:
            await self.app(scope, receive, send)
```

**Only add this if ADK tools fail to get container!**

---

## Phase 4: Complete Cleanup

### Task 4.1: Remove Service Locator Module

**Action:**

```bash
# DELETE the file completely
git rm app/services/locator.py

# Commit
git commit -m "feat: remove service locator module

Removed 142 lines of service locator anti-pattern code.
All dependency injection now handled by Dishka.

BREAKING CHANGE: ServiceLocator class no longer available"
```

---

### Task 4.2: Remove Old Dependencies Module

**Action:**

```bash
# DELETE the file completely
git rm app/server/deps.py

# Commit
git commit -m "feat: remove old dependency providers

Removed 71 lines of manual provider functions.
All providers now defined in app/server/providers.py using Dishka.

BREAKING CHANGE: provide_* functions no longer available"
```

---

### Task 4.3: Clean Up Config Module

**File:** `app/config.py`

**Remove:**

```python
from app.services.locator import ServiceLocator  # DELETE
# ...
service_locator = ServiceLocator()  # DELETE
```

**Verify exports still present:**

```python
# These should remain:
db_manager = SQLSpec()
db = _settings.db.create_config()
# ... other configs ...
```

**Test:**

```bash
uv run python -c "from app.config import db_manager, db; print('✓ Config imports work')"
```

---

### Task 4.4: Remove All Import References

**Search and Remove:**

```bash
# Find all references
git grep "service_locator"
git grep "from app.server import deps"
git grep "ServiceLocator"

# Remove each occurrence manually
# There should be none after previous tasks
```

**Verification:**

```bash
# These should return nothing:
git grep "service_locator" -- '*.py'
git grep "from app.server import deps" -- '*.py'
git grep "ServiceLocator" -- '*.py'
```

---

### Task 4.5: Run Full Linting Suite

**Commands:**

```bash
# Run all linters
uv run ruff check app/
uv run mypy app/
uv run pyright app/

# Fix any auto-fixable issues
uv run ruff check --fix app/
```

**Common Issues to Fix:**

1. **Unused imports:** Remove any leftover imports from deleted files
2. **Type errors:** Fix any type hint issues with `Inject[T]`
3. **Import ordering:** Run `ruff --fix` to sort imports

---

### Task 4.6: Run Full Test Suite

**Commands:**

```bash
# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Check coverage report
open htmlcov/index.html
```

**If tests fail:**

1. Check error messages for missing imports
2. Verify Dishka container setup in test fixtures
3. Add mock providers if needed
4. Update test expectations

---

### Task 4.7: Manual Testing Checklist

**Steps:**

```bash
# 1. Start app
uv run app run

# 2. Open browser: http://localhost:5006

# 3. Test home page
- Page loads without errors
- No console errors
- CSP nonce present

# 4. Test chat interface
- Type: "I need a strong coffee"
- Submit
- Verify AI response appears
- Check browser network tab for errors

# 5. Test dashboard
- Navigate to /dashboard
- Verify metrics display
- Check for auto-updates

# 6. Test vector demo
- Submit vector search query
- Verify results display
- Check performance metrics

# 7. Check server logs
- No errors
- Dishka lifecycle logs present
- Session management logs present

# 8. Test concurrent requests
- Open multiple browser tabs
- Submit queries simultaneously
- Verify no crashes
```

---

## Phase 5: Testing & Documentation

### Task 5.1: Create Mock Provider Tests

**File:** `tests/fixtures/mock_providers.py` (NEW)

```python
"""Mock Dishka providers for testing."""

import pytest
from dishka import Provider, Scope, provide, make_async_container
from unittest.mock import AsyncMock

from sqlspec.driver import AsyncDriverAdapterBase
from app.services import ProductService, MetricsService, CacheService


class MockSQLSpecProvider(Provider):
    """Mock database provider for testing."""

    @provide(scope=Scope.REQUEST)
    def get_mock_db_session(self) -> AsyncDriverAdapterBase:
        """Provide mock database session."""
        mock_driver = AsyncMock(spec=AsyncDriverAdapterBase)

        # Configure common mock behaviors
        mock_driver.select.return_value = []
        mock_driver.execute.return_value = None
        mock_driver.select_one.return_value = None

        return mock_driver


class MockServiceProvider(Provider):
    """Mock service provider for testing."""

    @provide(scope=Scope.REQUEST)
    def get_product_service(
        self,
        driver: AsyncDriverAdapterBase
    ) -> ProductService:
        """Provide real ProductService with mock driver."""
        return ProductService(driver)

    @provide(scope=Scope.REQUEST)
    def get_metrics_service(
        self,
        driver: AsyncDriverAdapterBase
    ) -> MetricsService:
        """Provide real MetricsService with mock driver."""
        return MetricsService(driver)

    @provide(scope=Scope.REQUEST)
    def get_cache_service(
        self,
        driver: AsyncDriverAdapterBase
    ) -> CacheService:
        """Provide real CacheService with mock driver."""
        return CacheService(driver)


@pytest.fixture
async def test_container():
    """Create test container with mock providers."""
    container = make_async_container(
        MockSQLSpecProvider(),
        MockServiceProvider(),
    )
    yield container
    await container.close()


@pytest.fixture
async def mock_product_service(test_container):
    """Get ProductService from test container."""
    async with test_container() as request_container:
        yield await request_container.get(ProductService)
```

**Usage in tests:**

```python
# tests/test_services.py
@pytest.mark.asyncio
async def test_product_service(mock_product_service):
    """Test ProductService with mock database."""
    # ProductService has mocked driver
    result = await mock_product_service.get_all()
    assert result == []  # Mock returns empty list
```

---

### Task 5.4: Update Documentation

**File:** `docs/guides/dependency-injection.md` (NEW)

```markdown
# Dependency Injection with Dishka

This guide explains how to use dependency injection in the application.

## Overview

We use [Dishka](https://dishka.readthedocs.io/) for dependency injection, providing:
- Automatic dependency resolution
- Proper lifecycle management (APP vs REQUEST scopes)
- Clean, testable code

## Clean Import Convention

To avoid exposing implementation details, we re-export Dishka with cleaner names:

\`\`\`python
from app.lib.di import Inject, inject

class MyController(Controller):
    @get("/")
    @inject
    async def handler(self, service: Inject[MyService]) -> Response:
        return await service.do_something()
\`\`\`

**Never import directly from `dishka`!** Always use `app.lib.di`.

## Adding a New Service

### Step 1: Create Service Class

\`\`\`python
# app/services/my_service.py
from app.services.base import SQLSpecService

class MyService(SQLSpecService):
    """My new service."""

    async def do_something(self) -> str:
        result = await self.driver.select_one(
            "SELECT * FROM my_table WHERE id = :id",
            id=1,
        )
        return result
\`\`\`

### Step 2: Add to Provider

\`\`\`python
# app/server/providers.py
from app.services.my_service import MyService

class CoreServiceProvider(Provider):
    scope = Scope.REQUEST

    # Add this line - auto-wiring!
    my_service = provide(MyService)
\`\`\`

### Step 3: Use in Controller

\`\`\`python
# app/server/controllers.py
from app.lib.di import Inject, inject
from app.services.my_service import MyService

class MyController(Controller):
    @get("/")
    @inject
    async def handler(self, my_service: Inject[MyService]) -> dict:
        result = await my_service.do_something()
        return {"result": result}
\`\`\`

That's it! Dishka handles dependency resolution.

## Testing

### Unit Tests (Mocked Dependencies)

\`\`\`python
from tests.fixtures.mock_providers import test_container

@pytest.mark.asyncio
async def test_my_service(test_container):
    async with test_container() as request_container:
        service = await request_container.get(MyService)
        result = await service.do_something()
        assert result is not None
\`\`\`

### Integration Tests (Real Database)

\`\`\`python
from app.server.providers import SQLSpecProvider, CoreServiceProvider
from dishka import make_async_container

@pytest.mark.asyncio
async def test_my_service_integration():
    container = make_async_container(
        SQLSpecProvider(),
        CoreServiceProvider(),
    )

    async with container() as request_container:
        service = await request_container.get(MyService)
        result = await service.do_something()
        assert result is not None

    await container.close()
\`\`\`

## Scopes

### APP Scope (Singletons)

Use for services that:
- Don't need database connections
- Are thread-safe
- Can be shared across requests

\`\`\`python
@provide(scope=Scope.APP)
def get_my_service(self) -> MyService:
    return MyService()
\`\`\`

### REQUEST Scope (Per-Request)

Use for services that:
- Need database connections
- Store request-specific state
- Should be cleaned up after response

\`\`\`python
@provide(scope=Scope.REQUEST)
def get_my_service(self, driver: AsyncDriverAdapterBase) -> MyService:
    return MyService(driver)
\`\`\`

Or use auto-wiring:

\`\`\`python
class CoreServiceProvider(Provider):
    scope = Scope.REQUEST
    my_service = provide(MyService)  # Auto-wired with driver
\`\`\`

## Troubleshooting

### "No active Dishka request container"

**Cause:** ADK tool function called outside request context.

**Solution:** Ensure Dishka middleware is configured in `app/asgi.py`.

### "Cannot resolve dependency: XYZ"

**Cause:** Service not registered in provider.

**Solution:** Add to `CoreServiceProvider`:

\`\`\`python
xyz_service = provide(XYZService)
\`\`\`

### Type errors with `Inject[T]`

**Cause:** Missing import from `app.lib.di`.

**Solution:**

\`\`\`python
from app.lib.di import Inject, inject

# Correct:
service: Inject[MyService]

# Wrong:
service: MyService
\`\`\`
\`\`\`

---

**End of Detailed Tasks**
