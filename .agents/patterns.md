# Project Patterns

> Consolidated learnings and patterns from all flows.
> This file is the single source of truth for project conventions.

<!-- truth: start -->
## Code Conventions

- Use `app/domain/chat/services/_adk/runner.py` as the canonical ADK runner location in DDD projects.
- Preserve ADK runner context fields (`intent_details`, `search_details`, `store_details`, `products_found`, `stores_found`) through controller response payloads and UI rendering.
- Keep migration README updated with concrete baseline tables and type usage after schema modernization.
- Beads is authoritative for task status; markdown artifacts should mirror Beads via sync after status changes.

## Architecture Patterns

- **Litestar App Composition:** Keep app setup thin. Compose routes, plugins, dependencies, and middleware strictly from domain modules. Use async I/O universally.
- **Dishka DI:** Prefer centralized Dishka setup (`setup_dishka`) with `DomainPlugin(use_dishka_router=True)` and handler-level `Inject[T]` over route-level `@inject`.
- Dishka router integration (`Inject[ADKRunner]` on handlers, no route decorators) keeps DI explicit and framework-native.
- **SQLSpec Data Access:** 
  - Always use typed adapters and context managers (`async with config.create_driver() as db:`).
  - Use `schema_type` to map typed results instead of raw dictionaries.
  - Prefer the query builder (`sql.select().to_statement()`) or `SQLFileLoader` over raw string concatenation.

## Gotchas & Warnings

- `make test` used `.ONESHELL` without `set -e`, which allowed false-green runs when pytest failed; enforce fail-fast in the test target.
- Integration tests using SQLSpec Oracle pool under `pytest-anyio` + xdist can hit event-loop binding issues; reset/close `db.pool_instance` in function-scoped fixtures to avoid cross-loop pool reuse.
- Cache integration tests should use unique keys per test run to remain deterministic under parallel workers.
- Fixture load ordering should include `store` before dependent semantic tables to keep imports deterministic.
- Product reads should normalize Oracle boolean nullability (`NVL(in_stock, TRUE)`) for stable typed API responses.

## Testing Patterns

- Maintain both lightweight chat UI and richer dashboard UI tests to keep quick-path and analytics-path regressions visible.
- UI verification is safer when tests assert rendered contextual fields (products/stores/results), not only final answer text.

## Context for AI Assistants

- Persona-aware system prompt composition (`BASE_SYSTEM_INSTRUCTION` + persona overlay) keeps one static ADK agent reusable while preserving behavioral flexibility.
- Preserve generated API/types artifacts and route scaffolding early (`litestar assets generate-types`) to reduce frontend/backend contract drift.
- Modern Oracle baseline is already captured in `0001_cymball_coffee_products.sql` with `BOOLEAN`, `JSON`, and `VECTOR` columns plus `store` table parity.
- Maintaining `.agents/knowledge/index.md` as a compact registry makes cross-flow recall faster than searching raw specs.
- During migration from legacy guides, preserving concise gotchas in `patterns.md` yields better downstream implementation quality.
<!-- truth: end -->