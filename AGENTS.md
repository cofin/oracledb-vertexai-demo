# Cymbal Coffee — Oracle 26ai + Vertex AI Demo

Coffee recommendation, store-planning, and Oracle APEX operations demo powered by **Oracle AI Database 26ai** Hybrid Reciprocal Rank Fusion (`CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE` + HNSW `VECTOR(3072, FLOAT32)` `FETCH APPROX`), **Oracle APEX 26.1** (`src/apex/cymbal-coffee-ops/` App `100` + `APEX_AI` Vertex AI grounding), **Vertex AI** (`gemini-embedding-2` + `gemini-3.8-flash`), **Litestar 2**, **SQLSpec `0.69.0`**, **Dishka**, **LitestarMCP `0.15`**, **LitestarA2A**, and **litestar-queues**.

## Quick Reference

- **Operational Rules**: [.agents/AGENTS.md](.agents/AGENTS.md)
- **Test Suite Rules**: [src/tests/AGENTS.md](src/tests/AGENTS.md) ([README](src/tests/README.md), [unit](src/tests/unit/AGENTS.md), [integration](src/tests/integration/AGENTS.md))
- **OKF v0.2 Knowledge Bundle**: [.agents/bundles/index.md](.agents/bundles/index.md)
  - [Product](.agents/bundles/product/index.md) | [Knowledge Index](.agents/bundles/knowledge/index.md) | [Workflow](.agents/bundles/knowledge/workflow.md)
  - [Architecture](.agents/bundles/knowledge/architecture/index.md) | [Domains](.agents/bundles/knowledge/domains/index.md)
  - [Testing](.agents/bundles/knowledge/testing/index.md) | [Patterns](.agents/bundles/knowledge/patterns/index.md) | [Gotchas](.agents/bundles/knowledge/gotchas/index.md)
- **AI Code Review Config**: [AGENTIC_REVIEW](AGENTIC_REVIEW) (`.agents/skills/review-*`)

## Canonical Commands

```bash
# Install & Local Autonomous AI Database Free 26ai Setup (APEX 26.1.5 + ORDS 26.3)
make install
make start-infra
make apex
uv run coffee upgrade
uv run coffee configure-apex-cdn

# Oracle APEX 26.1 + Vertex AI & APEXlang Operations
uv run python manage.py infra apex configure-vertex --mode direct --verify
uv run python manage.py infra apex import --alias cymbal-coffee-ops --app-id 100

# Run Server & Background Queue Worker
uv run coffee run
uv run coffee worker run
uv run coffee worker status
uv run coffee bulk-embed
uv run coffee export-fixtures
uv run coffee clear-cache
uv run coffee model-info

# Docs, Demo Recorders, Static Analysis & Tests
make docs             # Sphinx HTML build (warnings treated as errors)
make docs-demos-shell # deterministic VHS terminal & SQLcl demos (docs/_tapes/*.tape)
make docs-demos-web   # headless Playwright + FFmpeg APEX 26.1 browser demos
make lint             # prek + ruff + mypy + pyright + slotscheck + hygiene + security + review gates + tsc
make test-unit        # fast isolated unit tests + AST meta-guards (no database required)
make test-integration # live Oracle 26ai integration tests (ORACLE_CONTAINER_FLAVOR=free)
make test             # full test suite
```

## Core Invariants

1. Zero inline `#` comments and zero function-scoped imports across `src/app/`, `src/tests/`, `tools/`, and `manage.py` (except lazy CLI subcommand dispatch in `src/app/cli/main.py` and `src/app/cli/commands.py`), enforced by `tools/ci/check_code_hygiene.py` and `src/tests/unit/test_test_suite_guards.py`; use Google-style docstrings, PEP 585/604 typing, `@dataclass(..., slots=True)` for settings/tooling configs, and `FrozenBaseStruct` or `CamelizedFrozenStruct` (`msgspec.Struct(..., frozen=True, gc=False, omit_defaults=True)` in `src/app/lib/schema.py`) for domain and wire schemas.
2. Dishka provider modules in `src/app/ioc/` (`_config.py`, `_database.py`, `_ai.py`, `_domain.py`) must never use `from __future__ import annotations`; construct containers via `create_container()` / `get_providers()`.
3. Never import `app.config` inside `src/app/domain/**`, `src/app/ioc/**`, or `src/app/lib/**`; use `Settings.from_env()`, `OracleLoaderService` (`self.get_sql("<name>")` backed by `default_sql_loader()` in `src/app/lib/service.py`) or `OracleAsyncService`, `build_oracle_text_query` / `build_oracle_proximity_query` from `src/app/lib/text_search.py`, and SQLSpec `sql.insert` / `sql.update` / `sql.delete` builders for simple CRUD.
4. Keep `DatabaseSettings.get_queue_config()` (`min=1, max=4`, `session_key="queue_db_session"`, `"manage_lifespan": True`, `driver_features={"fetch_lobs": False, "enable_session_tracing": True}`) separate from `DatabaseSettings.get_config()` / `create_config()` (`driver_features={"enable_session_tracing": True}`, wire-level `sqlcommenter`, `ObservabilityConfig`, `wallet_zip`) so `OracledbAsyncQueueStore`'s background worker pool and in-place `driver_features` / `extension_config` mutations remain isolated from the primary application pool (`config.db`); in SQLSpec `0.69.0`, `fetch_lobs` defaults to `False`, returning CLOB/BLOB values under 1 GB directly as inline Python `str` / `bytes` across `select` and `select_stream`.
5. Never persist, cache, or log raw user browser coordinates (`latitude`, `longitude`, `radius_miles`).
