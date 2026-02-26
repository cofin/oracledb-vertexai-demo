# Learnings

- `make test` used `.ONESHELL` without `set -e`, which allowed false-green runs when pytest failed; enforce fail-fast in the test target.
- Integration tests using SQLSpec Oracle pool under `pytest-anyio` + xdist can hit event-loop binding issues; reset/close `db.pool_instance` in function-scoped fixtures to avoid cross-loop pool reuse.
- Cache integration tests should use unique keys per test run to remain deterministic under parallel workers.
- With `DomainPlugin(..., use_dishka_router=True)` and centralized `setup_dishka(container, app)`, handlers should use `Inject[T]` directly and avoid route-level `@inject`.
