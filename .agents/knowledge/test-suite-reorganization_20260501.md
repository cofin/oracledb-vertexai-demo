# Knowledge Entry: test-suite-reorganization_20260501

- **Flow ID:** `test-suite-reorganization_20260501`
- **Description:** Corrective PRD — reorganize the pytest suite into strict `unit` and `integration` module-path buckets with a layout guard and shared Oracle fixtures.
- **Completed:** 2026-05-01
- **Beads Epic:** `oracledb-vertexai-4d6.9`
- **Topics:** testing, pytest, oracle-fixtures, layout-guard, ruff

<!-- truth: start -->
## Summary

Rebuilt the pytest suite into strict `src/tests/unit/<module path>/` and
`src/tests/integration/<module path>/` buckets. Removed the legacy
`src/tests/api` bucket. Added a layout guard test that fails on top-level
test buckets or direct `src/tests/{unit,integration}/test_*.py` files. Shared
Oracle DDL and fixture loading happen once per integration worker/session;
function-scoped driver/session fixtures stay small.

## Patterns Elevated (see patterns.md for full list)

- Test files mirror the source module path under `src/tests/unit/` or
  `src/tests/integration/`. Do not add new top-level buckets such as
  `src/tests/api`, and do not add direct `src/tests/{unit,integration}/test_*.py`.
- Nested test directories need SPDX-bearing `__init__.py` files so the repo
  ruff configuration does not flag implicit namespace packages.
- Repo-shared test constants and path helpers live in `src/tests/support/`,
  not duplicated per test module.
- `make lint` only checks tracked files through pre-commit, so after moving
  tests into untracked directories run `uv run ruff check src/tests`
  directly before claiming the suite is clean.
- Oracle integration: keep expensive DDL and fixture loading shared per
  integration worker/session. Function-scoped driver/session fixtures stay
  small. Tests that mutate products use unique SKUs plus targeted cleanup
  (do not rely on transactional rollback when the schema spans multiple
  connections).
- Integration tests serialize on the shared Oracle pool via
  `pytest_collection_modifyitems` applying
  `xdist_group(name="oracle_integration")`; otherwise `-n 2 --dist=loadgroup`
  produces concurrent-pool errors.

## Key Files

- `src/tests/README.md` — layout rules and conventions.
- `src/tests/support/` — repo path helpers and shared constants.
- `src/tests/unit/` — pure-Python unit tests, mirrored by source module path.
- `src/tests/integration/` — Oracle-backed integration tests, mirrored by source module path.
- `src/tests/integration/conftest.py` — shared per-worker DDL + fixture loading; function-scoped driver fixtures.
<!-- truth: end -->
