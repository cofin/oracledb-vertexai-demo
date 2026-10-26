---
type: Guide
title: Unit & Integration Test Catalog
description: Flattened test tree layout, complete unit and integration module inventory, AST/tokenize meta-guards, and Oracle 26ai container fixtures
tags:
  - testing
  - pytest
  - anyio
  - oracle-26ai
  - apex
---

# Unit & Integration Test Catalog

## 1. Flattened Directory Layout (`src/tests/`)

The test suite mirrors `src/app/` and `tools/` directly under `src/tests/unit/` and `src/tests/integration/` without redundant `/app/` nesting, using AnyIO (`@pytest.mark.anyio` / session AnyIO mode) and exactly three authorized `conftest.py` files:

```text
src/tests/
├── AGENTS.md
├── README.md
├── conftest.py                # Shared fixtures + pytest_plugins = ["tests.fixtures.slides"]
├── fixtures/
│   ├── routing_golden.jsonl   # Golden Hybrid RRF routing evaluation dataset
│   └── slides.py              # Slide builder test fixtures
├── support/
│   └── paths.py               # Repository root and fixture path helpers
├── unit/
│   ├── AGENTS.md
│   ├── conftest.py
│   ├── test_okf_layout.py         # OKF v0.2 & AGENTIC_REVIEW layout tests
│   ├── test_test_suite_guards.py  # AST/tokenize meta-guards across src/app/ and src/tests/
│   ├── cli/
│   ├── db/
│   ├── domain/
│   ├── ioc/
│   ├── lib/
│   ├── server/
│   ├── tools/
│   │   └── slides/
│   └── utils/
└── integration/
    ├── AGENTS.md
    ├── conftest.py                # Ephemeral gvenzl/oracle-free container + seeded fixtures
    ├── db/
    ├── domain/
    └── server/
```

## 2. Unit Test Module Catalog (`src/tests/unit/`)

- **Root Meta-Guards**: `src/tests/unit/test_okf_layout.py`, `src/tests/unit/test_test_suite_guards.py`.
- **CLI (`src/tests/unit/cli/`)**: `test_commands.py`, `test_fixtures_and_embeddings.py`, `test_surface.py`.
- **Database & Named SQL (`src/tests/unit/db/`)**: `test_named_sql.py`, `test_store_data_foundation.py`.
- **Background Jobs (`src/tests/unit/domain/`)**: `test_background_jobs.py`.
- **AI, MCP & A2A (`src/tests/unit/domain/ai/`)**: `test_agent_orchestration.py`, `test_mcp_controllers.py`, `a2a/test_a2a.py`, `mcp/test_mcp.py`, `runtime/test_loop_stream.py`, `runtime/test_model_store.py`, `runtime/test_tools.py`.
- **Chat & Hybrid Routing (`src/tests/unit/domain/chat/`)**: `test_exceptions.py`, `controllers/test_chat_controller.py`, `services/test_grounded_routes.py`, `services/test_hybrid_router.py`.
- **Products, Stores, Vector & APEX (`src/tests/unit/domain/products/`)**: `controllers/test_apex.py`, `controllers/test_apex_ai_gateway.py`, `controllers/test_explain_plan.py`, `controllers/test_filters.py`, `controllers/test_store_inventory.py`, `controllers/test_vector.py`, `services/test_maps.py`, `services/test_store_service.py`, `services/test_vertex_ai_service.py`.
- **System & Telemetry (`src/tests/unit/domain/system/`)**: `controllers/test_metrics_charts.py`, `controllers/test_metrics_summary_cards.py`, `services/test_cache.py`, `services/test_metrics.py`.
- **Web Pages (`src/tests/unit/domain/web/`)**: `controllers/test_pages.py`.
- **Dishka IoC (`src/tests/unit/ioc/`)**: `test_ioc_and_services.py`, `test_ioc_integrations.py`.
- **Core Library (`src/tests/unit/lib/`)**: `test_log.py`, `test_log_middleware.py`, `test_queue_settings.py`, `test_service_and_serialization.py`, `test_settings.py`, `test_settings_vite.py`.
- **Server & Security (`src/tests/unit/server/`)**: `test_security_and_mcp.py`, `test_security_headers.py`.
- **Oracle, APEX, Docs, Hygiene, Demo & Slides Tooling (`src/tests/unit/tools/`)**: `test_adb_and_wallet.py`, `test_apex_tooling.py`, `test_apex_vertex.py`, `test_apexlang_app_source.py`, `test_cli_and_ords_deploy.py`, `test_code_hygiene_gate.py`, `test_demo_recordings.py`, `test_docs_accuracy.py`, `test_web_recorder.py`, `slides/test_cli.py`, `slides/test_deck.py`, `slides/test_highlight.py`, `slides/test_validate.py`.
- **Utilities (`src/tests/unit/utils/`)**: `test_fixtures.py`.

## 3. Integration Test Module Catalog (`src/tests/integration/`)

- **SQLSpec Oracle Connection (`src/tests/integration/db/`)**: `test_sqlspec_connection.py`.
- **Chat HTTP & SSE (`src/tests/integration/domain/chat/controllers/`)**: `test_chat_http.py`.
- **Products & Vector Search (`src/tests/integration/domain/products/`)**: `controllers/test_vector_http.py`, `services/test_vector_search.py`.
- **Web Views (`src/tests/integration/domain/web/controllers/`)**: `test_pages.py`.
- **Static Assets (`src/tests/integration/server/`)**: `test_static_assets.py`.

## 4. AST & Tokenize Meta-Guards (`src/tests/unit/test_test_suite_guards.py` & `tools/ci/check_code_hygiene.py`)

`src/tests/unit/test_test_suite_guards.py` runs in under 1 second during `make test-unit` alongside `tools/ci/check_code_hygiene.py` (`make lint`) to enforce:
1. Only the three layer-root `conftest.py` files (`conftest.py`, `unit/conftest.py`, `integration/conftest.py`) exist, and `pyproject.toml` sets `testpaths = ["src/tests"]`.
2. `unittest.mock` is never imported anywhere under `src/tests/integration/` or `src/tests/fixtures/`.
3. Zero `class Test*` grouping wrappers or nested classes inside `def test_*` functions exist across `src/tests/`.
4. Zero non-pragma inline `#` comments and zero function-scoped imports exist across `src/app/`, `src/tests/`, `tools/`, and `manage.py` (except lazy CLI dispatch in `src/app/cli/commands.py` and `src/app/cli/main.py`).
5. Every non-`__init__.py` module under `src/app/` defines a module docstring and `__all__`; every non-`__init__.py` module and `def test_*` / `async def test_*` function under `src/tests/` defines a docstring.
6. Test modules place private `_...` helpers before `def test_*` functions; production modules place public symbols before private `_...` helpers, order class methods as `__init__` -> `@property` -> public -> private `_...`, specify `slots=True` on `@dataclass`, and omit `from __future__ import annotations` in `src/app/ioc/`.
7. Deleted legacy shims, squashed migrations, and nested `app/` test directories never return, while reference keep-list test modules remain present.

## 5. Running the Suite

- **`make test-unit`**: Runs `uv run pytest src/tests/unit -p no:cacheprovider` with zero external database or Vertex AI dependencies.
- **`make test-integration`**: Runs `uv run pytest -n 2 --dist=loadgroup src/tests/integration` against an ephemeral `ORACLE_CONTAINER_FLAVOR=free` (`gvenzl/oracle-free:latest`) container managed by `src/tests/integration/conftest.py` (`xdist_group("oracle_integration")`, optional `ORACLE_TEST_REUSE_PORT`), distinct from the local interactive `adb-free:latest-26ai` stack (`make start-infra`).
- **`make test`**: Runs `uv run pytest -n 2 --dist=loadgroup src/tests` across the complete unit and integration test suite.
