# Agent Operational Rules (`.agents/AGENTS.md`)

This document defines the authoritative engineering, knowledge-bundle, and verification rules for agents working in the Cymbal Coffee repository.

## 1. OKF v0.2 Knowledge Bundle Navigation

All durable engineering knowledge, specifications, and architectural references live in `.agents/bundles/`:

- [Bundle Index](bundles/index.md)
- [Product Index](bundles/product/index.md)
- [Knowledge Index](bundles/knowledge/index.md)
- [Project Workflow](bundles/knowledge/workflow.md)
- [Architecture Index](bundles/knowledge/architecture/index.md)
- [Domains Index](bundles/knowledge/domains/index.md)
- [Testing Index](bundles/knowledge/testing/index.md)
- [Patterns Index](bundles/knowledge/patterns/index.md)
- [Gotchas Index](bundles/knowledge/gotchas/index.md)
- [Presentation Knowledge](bundles/knowledge/presentation/index.md)

Every markdown file under `.agents/bundles/product/` and `.agents/bundles/knowledge/` must begin with valid YAML frontmatter (`type`, `title`, `description`). Operational skills live exclusively under `.agents/skills/`.

## 2. Python 3.12+ & Litestar Architectural Invariants

1. **Zero Inline `#` Comments**: Never write inline `#` comments in Python files (`src/app/`, `src/tests/`, `tools/`, `manage.py`), enforced by `tools/ci/check_code_hygiene.py` and `src/tests/unit/test_test_suite_guards.py`. Explain design intent and edge cases in Google-style docstrings.
2. **Top-Level Imports Only**: Never place `import` or `from ... import` inside `def` or `async def` functions across `src/app/`, `src/tests/`, `tools/`, and `manage.py` (except lazy CLI subcommand dispatch in `src/app/cli/main.py` and `src/app/cli/commands.py`).
3. **Explicit `__all__`, Schemas & Module Layout**: Every module under `src/app/` must define module docstrings, grouped top-level imports, sorted `__all__`, and public classes/functions before private `_...` helpers (`tools/` and `manage.py` also enforce module docstrings, public-before-private ordering, and `@dataclass(..., slots=True)`). Domain and wire schemas inherit from `FrozenBaseStruct` or `CamelizedFrozenStruct` (`msgspec.Struct(..., frozen=True, gc=False, omit_defaults=True)` in `src/app/lib/schema.py`).
4. **Class Member Ordering**: Order class members as: class attributes $\rightarrow$ `__init__` $\rightarrow$ `@property` $\rightarrow$ public methods $\rightarrow$ private `_...` methods.
5. **Settings & DI Boundary**:
   - Use `Settings.from_env()` from `app.lib.settings` (cached via `@lru_cache(maxsize=1)`). Never import `app.config` inside `src/app/domain/**`, `src/app/ioc/**`, or `src/app/lib/**`.
   - Build the Dishka container through `create_container()` / `get_providers()` in `src/app/ioc/__init__.py` (`ConfigProvider`, `DBProvider`, `AIProvider`, `DomainServiceProvider`). Provider modules under `src/app/ioc/` (`_config.py`, `_database.py`, `_ai.py`, `_domain.py`) must never include `from __future__ import annotations`.
6. **Oracle 26ai, SQLSpec `0.69.0` & APEX 26.1**:
   - All static SQL queries live in `src/app/db/sql/*.sql` (with packaged deployment PL/SQL in `src/app/db/sql/deploy/configure-apex-cdn.sql` and `src/app/db/sql/deploy/revert-apex-cdn.sql`, executed via `uv run coffee configure-apex-cdn`). Data services inherit from `OracleLoaderService` (`self.get_sql("<name>")` backed by `default_sql_loader()` in `src/app/lib/service.py`) or `OracleAsyncService`, build Oracle Text expressions via `build_oracle_text_query` / `build_oracle_proximity_query` (`src/app/lib/text_search.py`), and use SQLSpec `sql.insert`, `sql.update`, and `sql.delete` builders for simple CRUD.
   - Bind Python `list[float]` directly to `VECTOR(3072, FLOAT32)` columns (`gemini-embedding-2`).
   - HNSW vector indexes (`INMEMORY NEIGHBOR GRAPH`) require `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX FIRST :limit ROWS ONLY`.
   - In SQLSpec `0.69.0`, `fetch_lobs` defaults to `False`, so `python-oracledb` bypasses `LOB` locators and returns CLOB/BLOB values under 1 GB directly as inline Python `str` / `bytes` across both `select` and `select_stream`. `DatabaseSettings.create_config()` / `get_config()` configures `driver_features={"enable_session_tracing": True}`, wire-level `sqlcommenter` (`enable_sqlcommenter=True`, `sqlcommenter_enable_context=True`, `sqlcommenter_enable_traceparent=True`), `ObservabilityConfig`, and Autonomous mTLS `wallet_zip` (`extract_oracle_wallet_zip`, `parse_tnsnames_ora`).
   - `DatabaseSettings.get_queue_config()` (`min=1, max=4`, `session_key="queue_db_session"`, `"manage_lifespan": True`, `driver_features={"fetch_lobs": False, "enable_session_tracing": True}`) must remain separate from `DatabaseSettings.get_config()` so `OracledbAsyncQueueStore`'s background worker pool and in-place `driver_features` / `extension_config` mutations remain isolated from the primary application pool (`config.db`).
   - Managed local development infrastructure (`make start-infra` / `manage.py infra start`) runs `container-registry.oracle.com/database/adb-free:latest-26ai` (`cymbal-adb-free`, `.envs/tns` mTLS wallet on `:1522` service `myatp_low`, pre-bundled Oracle APEX 26.1.5 + ORDS 26.3 at `https://localhost:8443/ords/apex`, workspace `COFFEE`, schema `APP`, Database Actions at `https://localhost:8443/ords/sql-developer`), while `ORACLE_CONTAINER_FLAVOR=free` (`gvenzl/oracle-free:latest` on `:1521/freepdb1`) powers ephemeral `make test-integration` runs.
   - APEX 26.1 connects to Vertex AI (`tools/oracle/apex_vertex.py` `ApexVertexConfigurator`, `manage.py infra apex configure-vertex`) via primary direct Vertex AI `/endpoints/openapi` (`--mode direct`, `model="google/gemini-3.8-flash"`, `DBMS_NETWORK_ACL_ADMIN`, `VERTEX_AI_CRED`, `COFFEE_VERTEX_AI`, `--refresh-token`) or secondary Litestar OpenAI-compatible gateway (`--mode gateway`, `ApexAIController` at `/api/apex/ai/v1/models` and `/api/apex/ai/v1/chat/completions`), powering `src/apex/cymbal-coffee-ops/` (App ID `100`, `compatibilityMode: 26.1`, Page 6 `APEX_AI.GENERATE`).
7. **Security & Coordinate Privacy**:
   - Every HTTP controller must inherit from `PublicController` or `SecureController` (`litestar_security`), enforced by `tools/ci/check_litestar_security.py`.
   - Browser coordinates (`latitude`, `longitude`, `radius_miles`) are opt-in, request-scoped, and must never be persisted to `agent_session`, `agent_event`, `response_cache`, `search_metric`, or logs.

## 3. Test Suite, Docs & Static Verification Gates

- Read `src/tests/README.md`, `src/tests/AGENTS.md`, `src/tests/unit/AGENTS.md`, and `src/tests/integration/AGENTS.md` before writing or modifying tests.
- Automated demo video recorders live in `tools/demos/cli.py`, `tools/demos/shell.py`, and `tools/demos/web.py` (`docs/_tapes/*.tape`, `tools/scripts/record-live-demos.sh`, `manage.py demos {check,shell,web,all}`, `make docs-demos-{shell,web,live,clean}`).
- Run `make lint` (`make py-check`) and `make test-unit` (plus `make docs` when editing documentation) before declaring any task complete.
