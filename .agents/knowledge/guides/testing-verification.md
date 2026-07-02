# Testing & Verification Guide

This guide details the testing architecture, pytest conventions, database integration test setups, and manual verification protocols.

## Test Suite Architecture

All tests live under `src/tests/` and are strictly categorized by type and module path:
- **Unit Tests:** `src/tests/unit/<module_path>/test_*.py`
- **Integration Tests:** `src/tests/integration/<module_path>/test_*.py`
- **Support Helpers:** `src/tests/support/` contains reusable test constants, paths, and mocks.

### Strict Conventions
- **No Issue Buckets:** Do not create top-level directories named after issue IDs or tickets. Do not name test modules after issues.
- **No Loose Root Tests:** Do not place `test_*.py` files directly under `src/tests/unit/` or `src/tests/integration/` roots. They must map to a specific module subdirectory.
- **SPDX Headers:** All subdirectories must contain `__init__.py` files with SPDX headers so that linter namespaces are recognized.
- **Target Coverage:** Maintain >80% coverage for all new Python files. Verify with:
  ```bash
  pytest --cov=app --cov-report=html
  ```

## Async Testing (AnyIO)

Async tests must use the AnyIO runner.
- Annotate async tests with `@pytest.mark.anyio`.
- Enter `AsyncTestClient` with `async with` inside fixtures or tests. If you fail to enter the client context, the Litestar app lifespan is not triggered, leaking database connections and Dishka containers across tests.

```python
@pytest.fixture
async def client(app):
    async with AsyncTestClient(app) as c:
        yield c
```

## Dependency Injection (DI) Mocking

Tests should mock services rather than building real external integrations:
- For handler tests that inject components, use Dishka DI container overrides or mock services directly.
- Ensure route-level DI parameters are satisfied.

## Oracle Integration Tests

Integration tests run against a real Oracle instance. Pytest fixtures manage the lifecycle:
1. `conftest.py` overrides application settings with the test DSN.
2. `src/tests/integration/conftest.py` closes any lingering SQLSpec connection pool before tests start.
3. The `driver` fixture bootstraps tables, runs truncates, and loads fixtures.
4. **Parallel Worker Safety:** Do not truncate shared fixture tables in the middle of tests. Use unique keys (e.g. unique SKUs/SKUs with timestamps) to prevent tests running concurrently from colliding, and run targeted cleanup instead.
5. The connection pool is closed after *each* test run to prevent event-loop bind leaks.

### Setup and Migrations
Ensure the database is up and migrated before running tests:
```bash
make start-infra
uv run python manage.py database upgrade --no-prompt
```

## Assertions Guidelines

- **Vector Search:** Assert specific metadata, score bounds, and result counts. Do not assert the exact text of AI-generated answers, as models are non-deterministic.
- **Telemetry:** Assert that `search_metrics` and `sql_phases` contain timing entries.
- **HTMX Route Verification:** Send `HX-Request: true` header in test clients or use HTMX conftest fixtures. Assert that HTMX actions return the expected partial HTML block (e.g. `hx-swap` targets, specific HTML class/id).

## Manual Verification Protocol

For changes affecting the UI or user-facing flow, provide a manual verification plan.

### Frontend Change Template
```text
The automated tests have passed. For manual verification, please follow these steps:

**Manual Verification Steps:**
1. Start the development server with: `uv run coffee run`
2. Open browser to: `http://localhost:8000`
3. Confirm that you see: [User action and visual outcome]
```

### Backend/API Change Template
```text
The automated tests have passed. For manual verification, please follow these steps:

**Manual Verification Steps:**
1. Ensure the server is running.
2. Execute: `curl -X POST http://localhost:8000/api/chat/stream -d '{"message": "Hello"}'`
3. Confirm that you receive: [Expected HTTP code, headers, or JSON keys]
```

A phase is only checkpointed after passing automated tests and securing the user's manual validation feedback.
