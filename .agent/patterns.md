# Project Patterns

> Consolidated learnings and patterns from all flows.
> This file is the single source of truth for project conventions.

## Code Conventions

- **Type Hints:** Python 3.11+ type hints (`mypy --strict` compliant).
- **Oracle Binding:** Use Oracle's `:name` style for parameter binding in SQL queries (never `?` or `%s`).
- **Naming:** Clean, descriptive naming (no `_optimized`, `_with_cache` suffixes). Snake_case for functions/vars, PascalCase for classes.
- **Imports:** Top-level imports only (except `typing.TYPE_CHECKING` blocks).
- **Errors:** Error messages in lowercase without trailing periods.

## Architecture Patterns

- **Service Wrapper Pattern:** Service class wraps the driver (SQLSpec, Vertex AI, ADK).
- **Layered Flow:** Controllers (Routing) -> Services (Business Logic/Orchestration) -> Repositories (Data Access).
- **Dependency Injection:** Use Dishka scopes (`AppScope` for singletons, `RequestScope` for per-request contexts like DB transactions).
- **Dishka Route Pattern:** When `DomainPlugin` uses `use_dishka_router=True` and `setup_dishka(container, app)` is configured centrally, route handlers should use `Inject[T]` parameters without route-level `@inject` decorators.

## Gotchas & Warnings

- **Oracle Vector Arrays:** Missing `array.array('f', embedding)` pattern when binding VECTOR types leads to `ORA-51805` vector format errors. Always cast embeddings correctly.
- **Loops in MCP SQLcl:** Prevent loops by providing precise prompts to SQLcl with explicit `WHERE` clauses and `FETCH FIRST N ROWS ONLY`.
- **N+1 Queries:** Be cautious of N+1 query patterns in product recommendation iterations; use batching in the repository layer.
- **Defensive Coding:** Never use `hasattr`/`getattr` workarounds. Enforce structural typing via Python `Protocols`.

## Testing Patterns

- **Pytest + Asyncio:** Test suites rely on `pytest-asyncio`. Run with `uv run pytest -n 2 --dist=loadgroup`.
- **Database Fixtures:** Use `pytest-databases` for managing Oracle database lifecycles in tests.
- **Mocking:** Inject mock Protocol implementations via Dishka rather than using `unittest.mock.patch` where possible.
- **Fail-Fast Test Targets:** When Makefile uses `.ONESHELL`, enforce `set -e` in test targets so pytest failures do not report false-green.
- **Oracle Pool Loop Safety:** Under `pytest-anyio` + xdist, reset/close shared Oracle pool state in function-scoped fixtures to avoid cross-event-loop pool reuse errors.
- **Parallel Test Isolation:** Use unique resource keys in integration tests (for example cache keys) to avoid cross-worker interference.

## Context for AI Assistants

- **Workspace Boundaries:** Always work within `.agent/specs/{flow_id}/`. Never write scratch files to the project root.
- **Cleanup:** Temporary files in `tmp/` must be cleaned up manually or by the Docs & Vision agent during the Review phase.
- **Research Preference:** Consult `.agent/knowledge/guides/` before reaching out to Web Search or Context7.
