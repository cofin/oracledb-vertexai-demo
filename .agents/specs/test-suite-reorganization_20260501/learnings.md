# Learnings: test-suite-reorganization_20260501

## 2026-05-01 - Test Suite Reorganization

- **Implemented:** Reworked the pytest suite into strict `unit` and
  `integration` module-path buckets, removed `src/tests/api`, added a layout
  guard, shared repo path helpers, and reduced Oracle integration bootstrap work
  by separating shared seed/schema setup from function-scoped sessions.
- **Files changed:** `.agents/specs/test-suite-reorganization_20260501/`,
  `.agents/flows.md`, `.agents/patterns.md`, `src/tests/README.md`,
  `src/tests/support/`, nested `src/tests/unit/`, nested
  `src/tests/integration/`, and `src/tests/integration/conftest.py`.
- **Validation:** `uv run ruff check src/tests`, `uv run pytest src/tests/unit
  --collect-only`, `uv run pytest src/tests/integration --collect-only`,
  `make test`, `make lint`, and `git diff --check` all passed.
- **Patterns:** Test files should mirror the source module path under
  `src/tests/unit/` or `src/tests/integration/`; nested test directories need
  SPDX-bearing `__init__.py` files so the repo ruff configuration does not flag
  implicit namespace packages.
- **Gotchas:** `make lint` only checks tracked files through the pre-commit
  path, so after moving tests into untracked directories run
  `uv run ruff check src/tests` directly before claiming the suite is clean.
- **Oracle fixtures:** Keep expensive DDL and fixture loading shared per
  integration worker/session, while function-scoped driver/session fixtures stay
  small and tests that mutate products use unique SKUs plus targeted cleanup.
