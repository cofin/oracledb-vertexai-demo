---
type: Guide
title: Technology Stack
description: Tech stack components for Litestar 2, SQLSpec 0.69.0, Oracle 26ai, APEX 26.1, Vertex AI, Native AgentRuntime, MCP/A2A, and litestar-queues
tags:
  - architecture
  - tech-stack
---

# Technology Stack

<!-- truth: start -->
## Backend
- **Language:** Python 3.12+ (managed via `uv`)
- **Framework:** Litestar 2 (`litestar-autowire`, `litestar-security`, `litestar-htmx`, `litestar-vite`)
- **Schemas & Serialization:** `msgspec>=0.22.0` (`FrozenBaseStruct` and `CamelizedFrozenStruct` with `frozen=True, gc=False, omit_defaults=True` in `src/app/lib/schema.py`, serialized via `src/app/utils/serialization.py`)
- **Server:** Granian (`litestar-granian[uvloop]`)
- **Dependency Injection:** Dishka (`create_container()` / `get_providers()` in `src/app/ioc/__init__.py` composing `ConfigProvider`, `DBProvider`, `AIProvider`, and `DomainServiceProvider`)
- **AI & Protocols:** Google Vertex AI (`google-genai>=1.68.0`, `gemini-3.8-flash`, `gemini-embedding-2`), native `app.domain.ai` `AgentRuntime`, `litestar-mcp[a2a,google-genai,opentelemetry]>=0.15.0`, and OpenAI-compatible `ApexAIController` (`/api/apex/ai/v1`)
- **Background Queues:** `litestar-queues[sqlspec]>=0.12.0` on Oracle 26ai

## Frontend & Low-Code Operations
- **Web Framework:** HTMX 2.x + Jinja2 templates (no React/SPA)
- **Asset Pipeline:** Vite (wired via `litestar-vite`)
- **Styling & Charts:** Tailwind CSS v4 + ApexCharts
- **Oracle APEX 26.1:** Declarative APEXlang application `src/apex/cymbal-coffee-ops/` (App ID `100`, `compatibilityMode: 26.1`, Page 6 `APEX_AI.GENERATE`) served via ORDS 26.3 (`https://localhost:8443/ords/apex`) and provisioned against Vertex AI via `ApexVertexConfigurator` (`tools/oracle/apex_vertex.py`, `--mode direct` `/endpoints/openapi` or `--mode gateway`)

## Persistence & Container Runtimes
- **Database:** Oracle AI Database 26ai (`VECTOR(3072, FLOAT32)`, HNSW `INMEMORY NEIGHBOR GRAPH`, `CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE`)
- **Container Runtimes:** Persistent Autonomous AI Database Free 26ai (`container-registry.oracle.com/database/adb-free:latest-26ai`, `cymbal-adb-free`, `.envs/tns` mTLS wallet on `:1522` service `myatp_low`, pre-bundled Oracle APEX 26.1.5 + ORDS 26.3, workspace `COFFEE`, schema `APP`, Database Actions at `https://localhost:8443/ords/sql-developer`) for `make start-infra`, and ephemeral `gvenzl/oracle-free:latest` (`ORACLE_CONTAINER_FLAVOR=free` on `:1521/freepdb1`) for `make test-integration`
- **Data Access:** SQLSpec `>=0.69.0` (`python-oracledb` and `mypyc`, default `fetch_lobs=False` returning CLOB/BLOB values under 1 GB directly as inline Python `str` / `bytes`, `driver_features={"enable_session_tracing": True}`, wire-level `sqlcommenter`, `ObservabilityConfig`, Autonomous `wallet_zip` via `extract_oracle_wallet_zip` / `parse_tnsnames_ora`, `OracleLoaderService` / `OracleAsyncService` in `src/app/lib/service.py`, and `src/app/lib/text_search.py` Oracle Text builders)
- **Browser Sessions:** Server-side sessions in Oracle (`app_session`)
- **Agent Sessions:** Native SQLSpec `OracleSessionStore` (`agent_session`) and `OracleEventStore` (`agent_event`)
- **Queue Persistence:** `OracledbAsyncQueueStore` with a dedicated `DatabaseSettings.get_queue_config()` pool (`min=1, max=4`, `session_key="queue_db_session"`, `"manage_lifespan": True`, `driver_features={"fetch_lobs": False, "enable_session_tracing": True}`) isolated from `DatabaseSettings.get_config()`

## Tooling & Demo Automation
- **Package & Database Tools:** `uv` (Python), `npm` (JS), Oracle SQLcl 26.1.2+ (`manage.py install sqlcl`), packaged Cloud Run APEX CDN PL/SQL (`uv run coffee configure-apex-cdn` executing `src/app/db/sql/deploy/configure-apex-cdn.sql`, paired with `src/app/db/sql/deploy/revert-apex-cdn.sql`)
- **Demo Video Recorders:** Deterministic VHS terminal/SQLcl recorder (`tools/demos/shell.py`, `docs/_tapes/*.tape`) and headless Playwright + FFmpeg APEX 26.1 browser recorder (`tools/demos/web.py`, `[dependency-groups].demos = ["playwright>=1.50"]`, `tools/scripts/record-live-demos.sh`, `manage.py demos {check,shell,web,all}`, `make docs-demos-{shell,web,live,clean}`)
- **VCS Hook Runner & Static Gates:** `prek`, Ruff, Mypy, Pyright, `slotscheck`, `tools/ci/check_code_hygiene.py`, `tools/ci/check_litestar_security.py`, `validate_agentic_review.py`, TypeScript compiler check (`tsc --noEmit`), Sphinx (`sphinx-build -W`)
<!-- truth: end -->

For detailed component mappings, see [architecture/system-architecture.md](../knowledge/architecture/system-architecture.md).
