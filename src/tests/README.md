# Test Suite Layout

The test tree mirrors `src/app/` packages and `tools/` modules directly under two behavior tiers without an intermediate `app/` directory:

```text
src/tests/
  conftest.py
  fixtures/*.py
  unit/<subsystem>/test_<subject>.py
  integration/<subsystem>/test_<subject>.py
```

Use `unit/` (`make test-unit`) for fast in-memory tests that require no Docker/Podman Oracle container: service and routing logic, `MockOracleAsyncDriver` SQLSpec boundaries, isolated controller and OpenAI-compatible gateway contracts, Dishka provider wiring (`ConfigProvider`, `DBProvider`, `AIProvider`, `DomainServiceProvider`), `Settings` / `DatabaseSettings` / `QueueSettings`, `tools/` CLI/APEX/demo-recorder workflows, and AST/OKF/documentation hygiene meta-guards.

Use `integration/` (`make test-integration`) for tests that exercise Litestar `AsyncTestClient`, app lifespan, real SQLSpec `OracleAsyncDriver` sessions, HNSW `VECTOR(3072, FLOAT32)` search, and seeded `.json.gz` fixtures against an ephemeral `gvenzl/oracle-free:latest` (`ORACLE_CONTAINER_FLAVOR=free`) Oracle 26ai container. End-to-end HTTP and database contract tests live here even when external Vertex AI calls are stubbed.

Examples:

- `app.domain.chat.services._router` -> `src/tests/unit/domain/chat/services/test_hybrid_router.py`
- `app.domain.products.controllers._vector` -> `src/tests/unit/domain/products/controllers/test_vector.py`
- `app.domain.products.controllers._apex_ai` -> `src/tests/unit/domain/products/controllers/test_apex_ai_gateway.py`
- `tools.oracle.apex_vertex` -> `src/tests/unit/tools/test_apex_vertex.py`
- `POST /api/chat/stream` through `AsyncTestClient` -> `src/tests/integration/domain/chat/controllers/test_chat_http.py`

Shared pytest fixture modules and golden datasets live under `src/tests/fixtures/` (such as `src/tests/fixtures/slides.py` and `src/tests/fixtures/routing_golden.jsonl`) and are loaded via `pytest_plugins` in `src/tests/conftest.py`, while `src/tests/support/paths.py` provides repository root path constants. Keep test-only helpers private to `src/tests/`; never add production helpers or fallbacks solely for tests.

Before adding a new test file, look for the existing canonical module test file in [unit/AGENTS.md](unit/AGENTS.md) or [integration/AGENTS.md](integration/AGENTS.md) and extend it. Prefer a new parameterized case, shared fixture, or additional assertion in the existing functional file over one-off bugfix or task-slice files. Follow all placement, conftest-ratchet, and module-layout rules in [AGENTS.md](AGENTS.md).
