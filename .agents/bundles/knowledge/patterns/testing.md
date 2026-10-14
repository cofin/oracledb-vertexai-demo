---
type: Pattern
title: Testing Patterns
description: Conventions for pytest AnyIO async tests, mock boundaries, and parallel worker safety
tags:
  - testing
  - pytest
  - anyio
---

# Testing Patterns

<!-- truth: start -->
- Prefer `@pytest.mark.anyio` for async tests.
- Test files live under strict behavior and module-path buckets mirroring `src/app/` without redundant `/app/` nesting: `src/tests/unit/{cli,db,domain,ioc,lib,server,tools/slides,utils}/test_*.py` or `src/tests/integration/{db,domain,server}/test_*.py`. Only approved meta-test files (`conftest.py`, `test_okf_layout.py`, `test_test_suite_guards.py`) may live directly in `src/tests/unit/`.
- Exactly three `conftest.py` files are permitted (`src/tests/conftest.py`, `src/tests/unit/conftest.py`, `src/tests/integration/conftest.py`); shared domain or tool fixtures belong in `src/tests/fixtures/*.py` registered via `pytest_plugins` in `src/tests/conftest.py`.
- Before creating a new test file, find the existing module-path test file and add the behavior there. Prefer parameterized cases, shared fixtures, and existing functional sections over one-file-per-issue coverage.
- Nested test directories are real packages with SPDX-bearing `__init__.py` files so repo ruff checks do not treat moved tests as implicit namespaces.
- Every test file follows the 5-section layout (`src/tests/AGENTS.md`): module docstring, `from __future__ import annotations` + top-level imports, module constants/markers, helpers/fixtures, and function-based `test_*` / `async def test_*` functions (`class Test*` wrappers, function-scoped imports, and inline `#` comments are banned; `unittest.mock` is banned in `src/tests/integration/` and `src/tests/fixtures/`).
- Tests should prove application behavior: service logic, controller responses, typed SQL/data contracts, settings parsing, DI resolution, chat payloads, vector telemetry, and HTMX partial behavior.
- Do not add mock-echo tests or tests whose only subject is repo structure, source ordering, docs text, `pyproject.toml`, workflow YAML, tool scripts, or third-party import surfaces. Use lint, build, smoke checks, or focused tool validation (`test_test_suite_guards.py`, `test_okf_layout.py`) for those concerns.
- `coffee upgrade` is the packaged/end-user install command and loads committed fixtures after migrations. Raw SQLSpec developer commands such as downgrade and current stay under `python manage.py database ...`; do not expose `coffee downgrade`.
- Put reusable repo paths in `src/tests/support/paths.py` instead of hardcoding relative parent depths in moved tests.
- Handler tests that hit `Inject[T]` must mock the full DI chain when the test is not meant to construct real services.
- API tests for HTMX partial branches should send `HX-Request: true` or use the repo's HTMX test fixture.
- Real Oracle integration tests use the repo-managed Oracle lifecycle (`make start-infra`, then `uv run python manage.py database upgrade --no-prompt`) and share DDL/fixture loading through integration fixtures. Keep SQLSpec pool resets only where needed for pytest event-loop binding.
- Vector-search tests should assert typed contextual fields and result counts, not only final answer text.
- Keep cache and Oracle mutation tests deterministic under parallel workers by using unique keys/SKUs plus targeted cleanup instead of truncating shared fixture tables per test.
- Use focused tests while editing, then run `make lint` and `make test` before claiming branch-level completion.
<!-- truth: end -->
