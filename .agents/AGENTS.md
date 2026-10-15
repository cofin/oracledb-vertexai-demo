# Agent Operational Rules (`.agents/AGENTS.md`)

This document defines the authoritative engineering, knowledge-bundle, and verification rules for agents working in the Cymbal Coffee repository.

## 1. OKF v0.2 Knowledge Bundle Navigation

All durable engineering knowledge, specifications, and architectural references live in `.agents/bundles/`:

- [Bundle Index](bundles/index.md)
- [Knowledge Index](bundles/knowledge/index.md)
- [Project Workflow](bundles/knowledge/workflow.md)
- [Architecture Index](bundles/knowledge/architecture/index.md)
- [Domains Index](bundles/knowledge/domains/index.md)
- [Testing Index](bundles/knowledge/testing/index.md)
- [Patterns Index](bundles/knowledge/patterns/index.md)
- [Gotchas Index](bundles/knowledge/gotchas/index.md)
- [Presentation Knowledge](bundles/knowledge/presentation/index.md)

Every markdown file under `.agents/bundles/knowledge/` must begin with valid YAML frontmatter (`type`, `title`, `description`). Operational skills live exclusively under `.agents/skills/`.

## 2. Python 3.12+ & Litestar Architectural Invariants

1. **Zero Inline `#` Comments**: Never write inline `#` comments in Python files (`src/app/`, `src/tests/`, `tools/`). Explain design intent and edge cases in Google-style docstrings.
2. **Top-Level Imports Only**: Never place `import` or `from ... import` inside `def` or `async def` functions (except lazy CLI subcommand dispatch in `src/app/cli/main.py` and `src/app/cli/commands.py`).
3. **Explicit `__all__` & Module Layout**: Every module under `src/app/` must define module docstrings, grouped top-level imports, `__all__`, and public classes/functions before private `_...` helpers.
4. **Class Member Ordering**: Order class members as: class attributes $\rightarrow$ `__init__` $\rightarrow$ `@property` $\rightarrow$ public methods $\rightarrow$ private `_...` methods.
5. **Settings & DI Boundary**:
   - Use `Settings.from_env()` from `app.lib.settings` (cached via `@lru_cache(maxsize=1)`). Never import `app.config` inside `src/app/domain/**`, `src/app/ioc/**`, or `src/app/lib/**`.
   - Provider modules under `src/app/ioc/` (`_database.py`, `_ai.py`, `_domain.py`) must never include `from __future__ import annotations`.
6. **Oracle 26ai & SQLSpec**:
   - All static SQL queries live in `src/app/db/sql/*.sql` and are loaded via `db_manager.get_sql("<name>")` (or `sql_loader.get_sql("<name>")`), while simple CRUD operations may use SQLSpec `sql.insert`, `sql.update`, and `sql.delete` builders.
   - Bind Python `list[float]` directly to `VECTOR(3072, FLOAT32)` columns (`gemini-embedding-2`).
   - HNSW vector indexes (`INMEMORY NEIGHBOR GRAPH`) require `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX FIRST :limit ROWS ONLY`.
   - `DatabaseSettings.get_queue_config()` (`session_key="queue_db_session"`) must remain separate from `DatabaseSettings.get_config()` so `OracledbAsyncQueueStore`'s `fetch_lobs=False` mutation never disables `enable_AutoLob=True` on `config.db`.
7. **Security & Coordinate Privacy**:
   - Every HTTP controller must inherit from `PublicController` or `SecureController` (`litestar_security`), enforced by `tools/ci/check_litestar_security.py`.
   - Browser coordinates (`latitude`, `longitude`, `radius_miles`) are opt-in, request-scoped, and must never be persisted to `agent_session`, `agent_event`, `response_cache`, `search_metrics`, or logs.

## 3. Test Suite & Static Verification Gates

- Read `src/tests/AGENTS.md`, `src/tests/unit/AGENTS.md`, and `src/tests/integration/AGENTS.md` before writing or modifying tests.
- Run `make lint` (`make py-check`) and `make test-unit` before declaring any task complete.
