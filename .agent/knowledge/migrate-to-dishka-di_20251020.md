# Knowledge Entry: migrate-to-dishka-di_20251020

- **Flow ID:** `migrate-to-dishka-di_20251020`
- **Description:** Migrate to Dishka DI and restructure codebase into Domain-Driven Design layout
- **Completed:** 2026-02-26
- **Archived:** 2026-02-26
- **Topics:** dishka, ddd, litestar, testing, oracle

## Summary
This flow completed the migration to domain-oriented structure with Dishka-driven dependency injection and removed the legacy service locator path. Final verification hardened test reliability by fixing false-green Make behavior and stabilizing Oracle integration tests under parallel execution.

## Patterns Elevated
- Fail-fast test targets under `.ONESHELL` (`set -e`).
- Oracle pool reset/close for pytest-anyio + xdist loop isolation.
- Unique cache keys in parallel integration tests.
- Dishka route usage via `DomainPlugin(..., use_dishka_router=True)` plus `Inject[T]` without route `@inject`.

## Key Files
- `app/domain/products/services/_product.py`
- `app/lib/di.py`
- `app/server/core.py`
- `app/server/plugins.py`
- `tests/integration/conftest.py`
- `tests/integration/test_cache_service.py`
- `tests/integration/test_product_service.py`
- `tests/integration/test_sqlspec_connection.py`
- `Makefile`
- `.agent/product-guidelines.md`

## Learnings (verbatim)

- `make test` used `.ONESHELL` without `set -e`, which allowed false-green runs when pytest failed; enforce fail-fast in the test target.
- Integration tests using SQLSpec Oracle pool under `pytest-anyio` + xdist can hit event-loop binding issues; reset/close `db.pool_instance` in function-scoped fixtures to avoid cross-loop pool reuse.
- Cache integration tests should use unique keys per test run to remain deterministic under parallel workers.
- With `DomainPlugin(..., use_dishka_router=True)` and centralized `setup_dishka(container, app)`, handlers should use `Inject[T]` directly and avoid route-level `@inject`.
