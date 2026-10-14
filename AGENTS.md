# Cymbal Coffee — Oracle 26ai + Vertex AI Demo

Coffee recommendation and store-planning demo powered by **Oracle AI Database 26ai** Hybrid Reciprocal Rank Fusion (`CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE` + HNSW `VECTOR(3072, FLOAT32)` `FETCH APPROX`), **Vertex AI** (`gemini-embedding-2` + `gemini-3.8-flash`), **Litestar 2**, **SQLSpec**, **Dishka**, **LitestarMCP 0.15**, **LitestarA2A**, and **litestar-queues**.

## Quick Reference

- **Operational Rules**: [.agents/AGENTS.md](.agents/AGENTS.md)
- **Test Suite Rules**: [src/tests/AGENTS.md](src/tests/AGENTS.md) ([unit](src/tests/unit/AGENTS.md), [integration](src/tests/integration/AGENTS.md))
- **OKF v0.2 Knowledge Bundle**: [.agents/bundles/index.md](.agents/bundles/index.md)
  - [Knowledge Index](.agents/bundles/knowledge/index.md) | [Workflow](.agents/bundles/knowledge/workflow.md)
  - [Architecture](.agents/bundles/knowledge/architecture/index.md) | [Domains](.agents/bundles/knowledge/domains/index.md)
  - [Testing](.agents/bundles/knowledge/testing/index.md) | [Patterns](.agents/bundles/knowledge/patterns/index.md) | [Gotchas](.agents/bundles/knowledge/gotchas/index.md)
- **AI Code Review Config**: [AGENTIC_REVIEW](AGENTIC_REVIEW) (`.agents/skills/review-*`)

## Canonical Commands

```bash
# Install & Local Oracle Setup
make install
make start-infra
uv run coffee upgrade

# Run Server & Background Queue Worker
uv run coffee run
uv run coffee worker run
uv run coffee worker status
uv run coffee bulk-embed
uv run coffee export-fixtures
uv run coffee clear-cache
uv run coffee model-info

# Static Analysis & Tests
make lint            # ruff + mypy + pyright + slotscheck + hygiene + security + review gates + tsc
make test-unit       # fast isolated unit tests + AST meta-guards (no database required)
make test-integration # live Oracle 26ai integration tests
make test            # full test suite
```

## Core Invariants

1. Zero inline `#` comments and zero function-scoped imports in Python files (except lazy CLI subcommand dispatch in `src/app/cli/main.py` and `src/app/cli/commands.py`); use Google-style docstrings and PEP 585/604 typing.
2. Provider modules in `src/app/ioc/` must never use `from __future__ import annotations`.
3. Never import `app.config` inside `src/app/domain/**`, `src/app/ioc/**`, or `src/app/lib/**`; use `Settings.from_env()`, `db_manager.get_sql("<name>")` / `sql_loader.get_sql("<name>")`, and SQLSpec `sql.insert` / `sql.update` / `sql.delete` builders for simple CRUD.
4. Keep `DatabaseSettings.get_queue_config()` (`session_key="queue_db_session"`) separate from `DatabaseSettings.get_config()` to preserve `enable_AutoLob=True`.
5. Never persist, cache, or log raw user browser coordinates (`latitude`, `longitude`).
