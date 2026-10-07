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
- Test files live under strict behavior and module-path buckets: `src/tests/unit/<module path>/test_*.py` or `src/tests/integration/<module path>/test_*.py`. Do not add new top-level issue buckets such as `src/tests/api`, and do not add direct `src/tests/unit/test_*.py` or `src/tests/integration/test_*.py` files.
- Before creating a new test file, find the existing module-path test file and add the behavior there. Prefer parameterized cases, shared fixtures, and existing functional sections over one-file-per-issue coverage.
- Nested test directories are real packages with SPDX-bearing `__init__.py` files so repo ruff checks do not treat moved tests as implicit namespaces.
- Tests should prove application behavior: service logic, controller responses, typed SQL/data contracts, settings parsing, DI resolution, chat payloads, vector telemetry, and HTMX partial behavior.
- Do not add tests whose only subject is repo structure, source ordering, docs text, `pyproject.toml`, workflow YAML, tool scripts, or third-party import surfaces. Use lint, build, smoke checks, or focused tool validation for those concerns instead of growing `src/tests`.
- `coffee upgrade` is the packaged/end-user install command and loads committed fixtures after migrations. Raw SQLSpec developer commands such as downgrade and current stay under `python manage.py database ...`; do not expose `coffee downgrade`.
- Put reusable test constants and repo paths in `src/tests/support/` instead of hardcoding relative parent depths in moved tests.
- Handler tests that hit `Inject[T]` must mock the full DI chain when the test is not meant to construct real services.
- API tests for HTMX partial branches should send `HX-Request: true` or use the repo's HTMX test fixture.
- Real Oracle integration tests use the repo-managed Oracle lifecycle (`make start-infra`, then `uv run python manage.py database upgrade --no-prompt`) and share DDL/fixture loading through integration fixtures. Keep SQLSpec pool resets only where needed for pytest event-loop binding.
- Vector-search tests should assert typed contextual fields and result counts, not only final answer text.
- Keep cache and Oracle mutation tests deterministic under parallel workers by using unique keys/SKUs plus targeted cleanup instead of truncating shared fixture tables per test.
- Use focused tests while editing, then run `make lint` and `make test` before claiming branch-level completion.
<!-- truth: end -->
