# Test Suite Layout

The test tree mirrors the code under test after the repository import root.
Only two behavior categories are allowed:

```text
src/tests/
  unit/<module path>/test_<behavior>.py
  integration/<module path>/test_<behavior>.py
```

Use `unit/` for tests that do not boot the Litestar app, enter app lifespan, or
require live Oracle state. Mocked SQLSpec drivers, controller `.fn` calls,
settings parser checks, and pure service behavior belong in `unit/`.

Use `integration/` for tests that exercise Litestar `AsyncTestClient`, app
lifespan, real SQLSpec Oracle sessions, or other multi-module runtime wiring.
HTTP contract tests live here even when expensive services such as ADK or
Vertex AI are stubbed.

Examples:

- `app.domain.chat.services.adk` -> `unit/app/domain/chat/services/test_adk.py`
- `app.domain.products.controllers._vector` -> `unit/app/domain/products/controllers/test_vector.py`
- `/api/chat/stream` through `AsyncTestClient` -> `integration/app/domain/chat/controllers/test_chat_http.py`

Shared test-only helpers belong under `src/tests/support/`. Keep helper modules
private to the suite; do not add production helpers solely for tests.

Do not add tests whose only subject is repository structure, documentation text,
tool scripts, project configuration files, workflow YAML, or dependency import
surfaces. Those belong to lint/build/smoke checks or direct tool validation,
not the application behavior test suite.

Before adding a new test file, look for the existing module-path test file and
extend it. Prefer a new parameterized case, shared fixture, or additional
assertion in the current functional section over one-off files for individual
issues or features. Create a new test file only when the source module has no
matching test file yet, or when the new module behavior deserves a separate
module-owned contract file.
