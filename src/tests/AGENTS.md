# Testing Rulebook

Binding placement and authoring rules for `src/tests/`.

## Placement Ladder

Put each new test at the lowest layer that proves the behavior once:

- `unit/` — pure logic, service/controller/gateway boundary contracts, Dishka provider wiring (`ConfigProvider`, `DBProvider`, `AIProvider`, `DomainServiceProvider`), `FrozenBaseStruct` schemas, `OracleLoaderService`, settings (`DatabaseSettings`, `QueueSettings`), `tools/` workflows (`tools/oracle/*`, `tools/demos/*`, `tools/slides/*`, `tools/ci/*`), and AST/OKF/docs meta-guards with no live Oracle container.
- `integration/` — end-to-end behavior against a real `gvenzl/oracle-free:latest` (`ORACLE_CONTAINER_FLAVOR=free`) Oracle 26ai container through the app: SQLSpec driver contracts, HNSW vector search, schema annotations, HTMX/JSON/SSE HTTP endpoints, and seeded `.json.gz` fixture loading.

Never re-prove an integration-covered path with a mock-echo unit test.

## Conftest Ratchet

Exactly three `conftest.py` files are permitted in the repository:

1. `src/tests/conftest.py` — root AnyIO backend, `.env.testing` settings override, `AsyncTestClient` fixtures (`client`, `htmx_client`), `MockOracleAsyncDriver` (`mock_driver`), and `pytest_plugins` registration (`tests.fixtures.slides`).
2. `src/tests/unit/conftest.py` — unit-tier configuration.
3. `src/tests/integration/conftest.py` — ephemeral `gvenzl/oracle-free:latest` (`ContainerFlavor.FREE`) container lifecycle, schema migration bootstrap, and seeded data fixtures.

Shared domain or tool fixtures belong in `src/tests/fixtures/*.py` registered via `pytest_plugins` in `src/tests/conftest.py`. Never add a fourth `conftest.py`.

## Mocks

- No mock-echo tests whose only assertion is that a mock was called without testing transformation, branching, or error handling.
- `unittest.mock` is banned under `src/tests/integration/` and `src/tests/fixtures/`.

## Test Module Layout

Every `.py` file under `src/tests/` follows this top-to-bottom layout:

1. **Module Docstring**: `"""Unit/Integration tests for <component>."""`
2. **Future Annotations & Top-Level Imports**: `from __future__ import annotations` followed by top-level imports (`stdlib` -> third-party -> `app.*` / `tools.*` -> `tests.*`). Mid-file function-scoped imports are banned.
3. **Module Constants & Markers**: Module-level `pytestmark` and `UPPER_SNAKE_CASE` constants.
4. **Helpers & Local Fixtures**: Module-scoped `_helper` functions/classes followed by local `@pytest.fixture` definitions (private `_...` helpers must precede `def test_*`, and nested classes inside `test_*` functions are banned).
5. **Test Functions**: Function-based `test_*` / `async def test_*` functions (`class Test*` is banned), each with a docstring, grouped by behavior and consolidated with `@pytest.mark.parametrize`.

## Anti-Bloat Rules

- **One Canonical Test File per Subject**: Extend the existing `test_<module>.py` file rather than creating task-slice or bugfix files (`test_<feature>_fix.py`, `test_<feature>_remediation.py`).
- **Zero Inline `#` Comments**: Never write `#` comments in test or fixture `.py` files. Express intent through descriptive function names and concise Google-style docstrings.

## Reference Keep-List

- `unit/domain/chat/services/test_hybrid_router.py`
- `unit/domain/chat/services/test_grounded_routes.py`
- `unit/domain/ai/runtime/test_loop_stream.py`
- `unit/domain/ai/runtime/test_model_store.py`
- `unit/domain/ai/test_agent_orchestration.py`
- `unit/db/test_named_sql.py`
- `unit/lib/test_settings.py`
- `integration/db/test_sqlspec_connection.py`
- `integration/domain/products/services/test_vector_search.py`
