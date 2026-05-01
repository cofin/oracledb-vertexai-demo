# Master PRD: Test Suite Reorganization

*PRD ID: `test-suite-reorganization_20260501`*
*Created: 2026-05-01*
*Status: Implemented*

---

## North Star

Turn the existing pytest suite from an issue-by-issue accumulation of files into a durable test architecture that matches the application structure, is easy to extend, and runs faster against Oracle.

The target layout is strict:

```text
src/tests/
  unit/<module path>/test_<behavior>.py
  integration/<module path>/test_<behavior>.py
```

`<module path>` mirrors the code under test after the import root. Examples:

- `src/app/domain/chat/services/adk.py` -> `src/tests/unit/app/domain/chat/services/test_adk.py`
- `src/app/domain/products/controllers/_vector.py` -> `src/tests/unit/app/domain/products/controllers/test_vector.py`
- `src/app/db/sql/products.sql` / SQLSpec registry -> `src/tests/unit/app/db/test_named_sql.py`
- `tools/oracle/database.py` -> `src/tests/integration/tools/oracle/test_database.py`

The end state should have fewer files, fewer explicitly named one-off tests, stronger parameterized coverage, shared fixtures where the behavior is the same, and a single Oracle container/schema/fixture bootstrap per test run.

No application behavior changes are part of this PRD.

---

## Current State Reviewed

Verified against the live tree on 2026-05-01:

- Pytest root is `src/tests` via `pyproject.toml`.
- `make test` runs `uv run pytest -n 2 --dist=loadgroup src/tests`.
- Current top-level test buckets are `src/tests/unit`, `src/tests/api`, and `src/tests/integration`.
- Current suite contains 34 test files and about 3,652 lines of Python tests.
- The largest drift hotspots are:
  - `src/tests/unit/test_adk_runner.py` at 566 lines.
  - `src/tests/integration/test_oracle_deploy.py` at 318 lines.
  - `src/tests/integration/test_sqlspec_connection.py` at 249 lines.
  - `src/tests/unit/test_vector_search_shape.py` at 179 lines.
  - `src/tests/unit/test_logging.py` at 168 lines.
  - `src/tests/unit/test_container_shape.py` at 152 lines.
  - `src/tests/api/test_chat_partial.py` at 146 lines.
- `src/tests/api` is not part of the requested target layout. These tests use Litestar `AsyncTestClient`, so they belong under `integration/app/server/...` or `integration/app/domain/...`, depending on the code path under test.
- `src/tests/integration/conftest.py` currently bootstraps Oracle DDL, truncates fixture tables, loads `.json.gz` fixtures, and seeds `SEED-SKU-001` inside the function-scoped `driver` fixture. That means expensive setup runs per test that asks for `driver`.
- `src/tests/integration/test_fixtures.py` defines local `driver` and `product_service` fixtures that duplicate and bypass `src/tests/integration/conftest.py`.
- Some async unit tests use `pytest.mark.asyncio` while repo patterns prefer `pytest.mark.anyio`.
- Current tests already pin useful behavior; this PRD reorganizes and consolidates them rather than deleting coverage to make the tree look smaller.

---

## Product Decisions

1. Keep only two top-level test categories: `unit` and `integration`.
2. Treat Litestar `AsyncTestClient` and app-lifespan tests as integration tests, even if their expensive dependencies are stubbed.
3. Treat pure controller `.fn` invocation, service tests with mocked drivers, schema/SQL shape tests, import-surface tests, and source-policy tests as unit tests.
4. Mirror source module paths under each category. Do not create issue-name buckets like `api`, `coverage`, `regression`, or `fixtures`.
5. Consolidate by functionality first, then by module path. A single file may contain many parameterized behavior cases when they all exercise the same public contract.
6. Prefer table-driven tests using `pytest.mark.parametrize`, small case dataclasses, and common fixtures over many explicit `test_one_specific_name` functions.
7. Share the Oracle container for the entire test run. Tests should assume the repo-managed container is started by `make start-infra` and migrated before `make test`, matching current project guidance.
8. Share Oracle DDL and fixture loading per xdist group/session where possible. Do not recreate product/cache tables and reload product/store fixtures per test.
9. Keep per-test cleanup limited to the data a test mutates. Prefer transaction rollback, unique keys/SKUs, and targeted cleanup over blanket table truncation.
10. Add layout/fixture guard tests so the suite does not drift back into top-level issue buckets.

---

## Roadmap

### Chapter 1 - `test-suite-foundation_20260501`

Define the testing architecture and shared fixtures before moving files.

Deliverables:

- Create or update test-only helper modules under `src/tests/fixtures/` or `src/tests/support/` for shared case data, fake drivers, fake ADK events, and common HTTP response assertions.
- Add a layout guard test, for example `src/tests/unit/tests/test_layout.py`, that rejects:
  - `src/tests/api/`
  - direct `src/tests/unit/test_*.py` files outside a module path, except explicitly allowed suite infrastructure tests
  - direct `src/tests/integration/test_*.py` files outside a module path
- Standardize async tests on `pytest.mark.anyio`.
- Document the unit/integration boundary in `src/tests/README.md`.
- Keep `pyproject.toml` test discovery unchanged unless implementation proves a narrow change is needed.

Acceptance:

- A future contributor can determine where a new test belongs from the README and guard test.
- Existing tests still collect before any behavior consolidation begins.
- The guard test is initially allowed to list current violations, then becomes strict after Chapters 2-4 complete.

### Chapter 2 - `test-suite-unit-layout_20260501`

Move and consolidate pure unit coverage under module paths.

Target mapping:

| Current file(s) | Target |
|---|---|
| `unit/test_adk_runner.py`, `unit/test_workflow_factory.py`, `unit/test_classifier.py`, `unit/test_chat_di.py`, `unit/test_chat_exceptions.py` | `unit/app/domain/chat/services/` split by module: `test_adk.py`, `test_workflow.py`, `test_classifier.py`, `test_exceptions.py` |
| `unit/test_cache_service.py`, `unit/test_metrics_*_shape.py` | `unit/app/domain/system/services/test_cache.py`, `unit/app/domain/system/controllers/test_metrics.py` |
| `unit/test_vector_search_shape.py`, `unit/test_filter_dependencies.py` | `unit/app/domain/products/controllers/test_vector.py`, `unit/app/domain/products/controllers/test_filters.py`, `unit/app/domain/products/services/test_vector_search.py` |
| `unit/test_container_shape.py`, `unit/test_di_module.py`, `unit/test_database_settings.py` | `unit/app/test_ioc.py`, `unit/app/lib/test_di.py`, `unit/app/lib/test_settings.py` |
| `unit/test_named_sql_loading.py`, `unit/test_fixture_loader_merge_sql.py` | `unit/app/db/test_named_sql.py`, `unit/app/utils/test_fixtures.py` |
| `unit/test_domain_layout.py`, `unit/test_service_base.py`, `unit/test_schema_naming_convention.py` | `unit/app/domain/test_layout.py`, `unit/app/lib/test_service.py`, `unit/app/domain/test_schema_conventions.py` |
| `unit/test_logging.py`, `unit/test_cli_surface.py`, `unit/test_patterns_doc.py`, `unit/test_copyright_config.py`, `unit/test_chat_frontend.py`, `unit/test_adk2_surface_pin.py` | module-path homes under `unit/app/lib/`, `unit/app/cli/`, `unit/agents/`, `unit/project/`, `unit/src/resources/`, and `unit/vendor/google_adk/` |

Consolidation requirements:

- Break `test_adk_runner.py` into focused module files, not one equally large moved file.
- Parameterize repeated constructor/provider scope assertions using case objects.
- Parameterize controller branch tests by request mode and expected response shape where assertions are shared.
- Reuse fake event/session/tool fixtures instead of rebuilding `MagicMock` chains in every ADK test.
- Keep behavior names readable, but remove one-function-per-regression file layout.

Acceptance:

- No pure unit test remains directly under `src/tests/unit/`.
- Unit tests mirror `app` and `tools` module paths.
- `uv run pytest src/tests/unit --collect-only` collects the same meaningful unit coverage after moves.
- Focused unit pytest passes before moving to integration layout.

### Chapter 3 - `test-suite-http-layout_20260501`

Move app-lifespan and HTTP contract tests out of `src/tests/api` into integration module paths.

Target mapping:

| Current file | Target |
|---|---|
| `api/test_chat_partial.py` | `integration/app/domain/chat/controllers/test_chat_http.py` |
| `api/test_vector_demo_partial.py` | `integration/app/domain/products/controllers/test_vector_http.py` |
| `api/test_pages.py` | `integration/app/domain/web/controllers/test_pages.py` |
| `api/test_static_assets.py` | `integration/app/server/test_static_assets.py` |

Consolidation requirements:

- Use shared `client`, `htmx_client`, and ADK runner stubs from common fixtures.
- Parameterize HTMX vs non-HTMX response branches when the same endpoint contract is being checked.
- Keep SSE behavior in one focused file with table-driven event expectations.
- Delete `src/tests/api` after the move.

Acceptance:

- `find src/tests -maxdepth 1 -type d` shows only infrastructure plus `unit` and `integration`.
- HTTP tests still avoid live Vertex AI and real ADK runner calls through shared stubs.
- `uv run pytest src/tests/integration/app/domain/chat/controllers src/tests/integration/app/domain/products/controllers src/tests/integration/app/domain/web/controllers src/tests/integration/app/server --collect-only` collects the moved HTTP tests.

### Chapter 4 - `test-suite-oracle-fixtures_20260501`

Replace per-test Oracle bootstrap with session-scoped schema/data setup and explicit mutation cleanup.

Deliverables:

- Refactor `src/tests/integration/conftest.py` so the expensive Oracle setup has separate fixture layers:
  - `oracle_integration_group`: xdist group marker remains `oracle_integration`.
  - `oracle_schema`: session or worker scoped; ensures migrations/DDL and one-time test support objects exist.
  - `oracle_seed_data`: session or worker scoped; truncates fixture-owned tables once, loads app fixtures once, seeds canonical test rows once.
  - `oracle_session` / `driver`: function scoped; yields a fresh SQLSpec session against the shared schema.
  - `mutated_tables` or cleanup helper: opt-in cleanup for tests that insert/update shared tables.
- Move test-only DDL out of inline strings where practical. Reuse app migrations for app tables; keep only truly test-specific temp tables in helper functions.
- Replace `test_fixtures.py` duplicate fixture definitions with shared fixtures or delete it if it has no tests.
- Replace shared `SEED-SKU-001` mutation with unique per-test SKUs where a test writes product data.
- Avoid closing and reopening the global SQLSpec pool after every test unless implementation proves the driver/pool is event-loop bound. If pool closure is still required, keep it function-scoped and document why.

Acceptance:

- Product/store fixture loading happens once per integration test worker/session, not once per `driver` test.
- DDL for product/cache tables is not executed per test.
- Integration tests that mutate Oracle data use unique identifiers or explicit cleanup.
- Existing `make test` xdist grouping remains safe.
- `uv run pytest src/tests/integration/app/db src/tests/integration/app/domain/products --collect-only` collects the Oracle-backed tests under module paths.

### Chapter 5 - `test-suite-consolidation-pass_20260501`

Finish parameterization, remove duplication, and prove the reorganized suite is stable.

Consolidation targets:

- `integration/app/db/test_sqlspec_connection.py`: combine basic `SELECT`, dict access, parameter binding, multiple rows, and vector metadata checks into table-driven cases where possible.
- `integration/tools/oracle/test_deploy.py`: split by source module and parameterize deployment-mode/env cases, wallet validation cases, health status mapping, and runtime command cases.
- `unit/app/domain/chat/services/test_adk.py`: use fixtures/case objects for cached response, generated response, grounded product RAG, credential errors, and SSE metrics.
- `unit/app/test_ioc.py`: parameterize provider factory scope checks and provider class presence.
- `unit/app/lib/test_log.py`: parameterize warning/filter/status cases.
- `unit/app/domain/test_schema_conventions.py`: keep AST/source policy checks together and parameterized by schema file.

Acceptance:

- No top-level issue/feature bucket remains in `src/tests`.
- The suite has fewer files or demonstrably clearer files than the starting point; any intentionally retained split must map to source modules.
- Duplicate local fixtures are removed or promoted to shared fixture modules.
- `make test` passes.
- `make lint` passes.
- `git diff --check` passes.

---

## Global Constraints

1. Do not reduce meaningful coverage to make the layout cleaner.
2. Do not change application behavior while reorganizing tests.
3. Do not start or wipe Oracle containers inside pytest. Keep infrastructure lifecycle on existing commands (`make start-infra`, `make migrate`, `make test`).
4. Avoid hidden state coupling. If a test depends on seeded data, name the fixture or case data explicitly.
5. Prefer function-based tests and local parameterized cases over classes unless a class groups a large external-tool surface cleanly.
6. Keep test helper modules private to the test suite; do not add production helpers for test-only convenience.
7. Use common fixtures for repeated setup, but keep fixture scope narrow enough that a test's dependencies remain obvious.
8. If a shared Oracle pool is event-loop bound, document the constraint in `src/tests/integration/conftest.py` and choose the smallest pool reset needed.
9. Use stable, unique test data keys/SKUs to avoid xdist and rerun contamination.
10. Preserve repo-native validation: focused pytest during refactor, then `make test`, `make lint`, and `git diff --check`.

---

## Out of Scope

- Adding new product features or endpoint behavior.
- Rewriting production code to make tests easier.
- Adding a new test runner, database service, or container orchestration tool.
- Increasing coverage targets beyond preserving and clarifying the existing useful coverage.
- Making pytest manage Docker/Podman lifecycle directly.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Moving tests breaks import assumptions or fixture discovery | Move by module path in small batches; run focused `--collect-only` before executing tests. |
| Session-scoped Oracle setup leaks mutable state | Use unique keys/SKUs, opt-in cleanup helpers, and keep mutation-heavy tests function-isolated. |
| SQLSpec Oracle pool is event-loop bound | Separate shared schema/data setup from function-scoped session objects; only pool-reset where verified necessary. |
| Parameterization hides intent | Use descriptive `ids=...` and case dataclasses with explicit expected fields. |
| Layout guard blocks intermediate commits | Start the guard in report/list mode, then make it strict once all chapters land. |
| `make test -n 2 --dist=loadgroup` exposes shared-data races | Keep the `oracle_integration` xdist group and avoid cross-worker shared writes. |

---

## Acceptance (PRD-level)

PRD is complete when:

- `src/tests` has only `unit` and `integration` as behavior categories.
- Every test file path mirrors the module path of the code under test.
- `src/tests/api` is removed.
- Common fixtures/stubs cover Litestar clients, HTMX headers, fake ADK runner events, fake SQLSpec drivers, Oracle seeded data, and unique test identifiers.
- Oracle app DDL and fixture loading run once per integration worker/session, not per test.
- Mutation-heavy Oracle tests use explicit cleanup or unique test data.
- Repeated behavior checks are parameterized where that improves clarity.
- `make test` passes.
- `make lint` passes.
- `git diff --check` passes.

---

## Beads master epic

- **Master**: `oracledb-vertexai-4d6.9`
