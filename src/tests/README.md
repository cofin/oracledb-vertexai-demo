# Test Suite Layout

The test tree mirrors the code under test after the repository import root.
Only two behavior categories are allowed:

```text
src/tests/
  unit/<module path>/test_<behavior>.py
  integration/<module path>/test_<behavior>.py
```

Use `unit/` for tests that do not boot the Litestar app, enter app lifespan, or
require live Oracle state. Mocked SQLSpec drivers, source-shape checks,
controller `.fn` calls, schema checks, CLI import checks, and JavaScript source
contract tests belong in `unit/`.

Use `integration/` for tests that exercise Litestar `AsyncTestClient`, app
lifespan, real SQLSpec Oracle sessions, local infrastructure helpers, or other
multi-module runtime wiring. HTTP contract tests live here even when expensive
services such as ADK or Vertex AI are stubbed.

Examples:

- `app.domain.chat.services.adk` -> `unit/app/domain/chat/services/test_adk.py`
- `app.domain.products.controllers._vector` -> `unit/app/domain/products/controllers/test_vector.py`
- `/api/chat` through `AsyncTestClient` -> `integration/app/domain/chat/controllers/test_chat_http.py`
- `tools.oracle.database` -> `integration/tools/oracle/test_database.py`

Shared test-only helpers belong under `src/tests/support/`. Keep helper modules
private to the suite; do not add production helpers solely for tests.

