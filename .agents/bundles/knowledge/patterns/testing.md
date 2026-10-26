---
type: Pattern
title: Testing Patterns
description: Conventions for pytest AnyIO async tests, canonical module layout, mock boundaries, and parallel Oracle worker safety
tags:
  - testing
  - pytest
  - anyio
---

# Testing Patterns

<!-- truth: start -->
- Prefer `@pytest.mark.anyio` for async tests.
- Test files live under module-path buckets mirroring `src/app/` and `tools/` without redundant `/app/` nesting: `src/tests/unit/{cli,db,domain,ioc,lib,server,tools,utils}/test_*.py` (including `src/tests/unit/tools/slides/test_*.py`) or `src/tests/integration/{db,domain,server}/test_*.py`. Only approved meta-test files (`conftest.py`, `test_okf_layout.py`, `test_test_suite_guards.py`) may live directly in `src/tests/unit/`.
- Only root and tier `conftest.py` files are permitted (`src/tests/conftest.py`, `src/tests/unit/conftest.py`, `src/tests/integration/conftest.py`); shared domain or tool fixtures belong in `src/tests/fixtures/*.py` registered via `pytest_plugins` in `src/tests/conftest.py`.
- Before creating a new test file, locate the existing canonical module-path test file and add coverage there. Prefer `@pytest.mark.parametrize`, shared fixtures, and existing functional sections over standalone bugfix or audit test files.
- Nested test directories are real packages with SPDX-bearing `__init__.py` files so Ruff `INP001` checks never treat test directories as implicit namespace packages.
- Every test file follows the canonical test module layout in `src/tests/AGENTS.md` (enforced by `src/tests/unit/test_test_suite_guards.py`): SPDX headers and module docstring, `from __future__ import annotations` plus top-level imports, module constants and `pytestmark`, private `_helper` functions/classes and local `@pytest.fixture` definitions, and top-level `def test_*` / `async def test_*` functions with Google-style docstrings (`class Test*` wrappers, nested classes inside tests, function-scoped imports, and inline `#` comments are banned; `unittest.mock` is banned in `src/tests/integration/` and `src/tests/fixtures/`).
- Tests should prove application behavior: service logic, controller responses, typed `FrozenBaseStruct` / `CamelizedFrozenStruct` SQL and wire contracts, settings parsing, Dishka container resolution, chat SSE payloads, vector telemetry, and HTMX partial behavior.
- Do not add mock-echo tests whose only assertion is that a mock was called, or one-off tests asserting static file existence; structural repository gates live in `tools/ci/check_code_hygiene.py`, `tools/ci/check_litestar_security.py`, `src/tests/unit/test_test_suite_guards.py`, `src/tests/unit/test_okf_layout.py`, and `src/tests/unit/tools/test_docs_accuracy.py`.
- `coffee upgrade` is the packaged end-user install command and loads committed fixtures after migrations. Raw SQLSpec developer commands such as `downgrade` and `current` stay under `uv run python manage.py database ...`; do not expose `coffee downgrade`.
- Put reusable repository path constants in `src/tests/support/paths.py` instead of hardcoding relative parent depths in nested test files.
- Handler unit tests that exercise `Inject[T]` override or provide dependencies via Dishka test containers (`create_container(*extra_providers)`).
- API tests for HTMX partial branches send `HX-Request: true` (or use the repository HTMX test helpers) and enter `AsyncTestClient` via `async with AsyncTestClient(app) as client:`.
- Live Oracle 26ai integration tests (`make test-integration`) run against lightweight `gvenzl/oracle-free:latest` (`ORACLE_CONTAINER_FLAVOR=free`, booted on an ephemeral free host port via `src/tests/integration/conftest.py` or reused on `:1521/freepdb1` via `ORACLE_CONTAINER_FLAVOR=free uv run python manage.py infra start` followed by `uv run python manage.py database upgrade --no-prompt`), pinning all integration tests to one worker group (`xdist_group(name="oracle_integration")` under `pytest -n 2 --dist=loadgroup`) to share DDL and seeded fixtures safely.
- Vector-search and Hybrid RRF tests assert typed contextual fields (`similarity_score`, `rrf_score`, `stock_status`) and result counts rather than only final answer strings.
- Keep cache and Oracle mutation tests deterministic under parallel `pytest-xdist` workers by using unique keys or SKUs plus targeted cleanup instead of truncating shared fixture tables per test.
- Run focused unit tests while iterating, then verify `make lint` and `make test-unit` (plus `make test-integration` when touching SQL or Oracle adapters) before declaring work complete.
<!-- truth: end -->
