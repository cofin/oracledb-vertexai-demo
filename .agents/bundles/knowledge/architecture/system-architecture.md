---
type: Guide
title: System Architecture
description: High-level system architecture, multi-protocol routes, package boundaries, Dishka dependency injection scopes, SQLSpec 0.69.0 pools, background queues, and ADB-Free 26ai + APEX 26.1 runtime
tags:
  - architecture
  - litestar
  - dishka
  - queues
  - apex
---

# System Architecture

## 1. Multi-Protocol Application Surface

Cymbal Coffee is a multi-protocol Litestar 2 application served by Granian (`uv run coffee run`):

- `GET /` & `GET /explore` (`PageController` in `src/app/domain/web/controllers/_pages.py`) — Interactive coffee concierge chat UI (Jinja2 + HTMX + SSE) and vector search laboratory, RRF telemetry dashboard, and Oracle `EXPLAIN PLAN` inspector.
- `POST /api/chat/stream` & `POST /api/chat/session/clear` (`CoffeeChatController` in `src/app/domain/chat/controllers/_chat.py`) — Server-Sent Event (`ServerSentEvent`) conversation stream and browser session reset.
- `POST /api/vector-demo`, `GET /api/explain-plan`, & `GET /api/vector-search` (`VectorController` in `src/app/domain/products/controllers/_vector.py`) — Hybrid RRF / HNSW search endpoint (HTMX partial or JSON), `DBMS_XPLAN.DISPLAY()` execution plan inspection, and `mcp_tool="search_products"` search endpoint.
- `GET /api/products`, `GET /api/products/{product_id}`, `GET /api/stores`, `GET /api/stores/{store_id}/inventory`, & `GET /api/stores/{store_id}/inventory/raw` (`ProductController` and `StoreController` in `src/app/domain/products/controllers/_products.py`) — Paginated REST endpoints, HTMX store inventory partial, and `mcp_tool` handlers (`get_product`, `get_store_inventory`).
- `GET /api/apex/*` & `POST /api/apex/recommendations` (`ApexController` in `src/app/domain/products/controllers/_apex.py`) — JSON endpoints shaped for Oracle APEX REST Source Catalog consumption (`/products`, `/stores`, `/inventory/summary`, `/stores/{store_id}/inventory`, `/products/{product_id}/availability`, `/recommendations`, `/vector/status`, `/openapi/status`).
- `GET /api/apex/ai/v1/models` & `POST /api/apex/ai/v1/chat/completions` (`ApexAIController` in `src/app/domain/products/controllers/_apex_ai.py`) — OpenAI-compatible Vertex AI gateway for Oracle APEX 26.1 Generative AI Services (`COFFEE_VERTEX_AI`), backed by `GeminiModelClient` with optional `APEX_GATEWAY_API_KEY` Bearer authentication.
- `GET /api/metrics/summary`, `GET /api/metrics/charts`, `GET /health`, & `GET /api/system/health` (`MetricsController` and `SystemController` in `src/app/domain/system/controllers/`).
- `POST /mcp` — Stateless Model Context Protocol (`LitestarMCP` 0.15) exposing route-annotated tools, `CoffeeSkillController`, `CoffeePromptController`, and `.agents/skills`.
- `POST /a2a` & `GET /.well-known/agent-card.json` — Agent-to-Agent Protocol (`LitestarA2A` with `CoffeeAgentExecutor` and `build_agent_card`).

## 2. Package & Source Layout

```text
src/
├── apex/
│   └── cymbal-coffee-ops/ # Source-controlled APEX 26.1 APEXlang app (App ID 100)
├── app/
│   ├── cli/
│   │   ├── _helpers/      # CLI workflow helpers (fixtures.py, ords.py)
│   │   ├── commands.py    # Click subcommands (run, upgrade, worker, queues, bulk-embed, configure-apex-cdn)
│   │   ├── main.py        # coffee Click group
│   │   └── utils.py       # @async_inject decorator
│   ├── config.py          # Leaf PEP 562 composition bridge for server/CLI entrypoints only
│   ├── db/
│   │   ├── fixtures/      # Committed fixtures (store, product, store_product_inventory, chat_route)
│   │   ├── migrations/    # SQLSpec baseline migration (0001_cymball_coffee_products.sql)
│   │   └── sql/           # Named SQL (products, stores, inventory, system, ai-runtime, hybrid) + deploy/
│   ├── domain/
│   │   ├── ai/            # Native AgentRuntime, GeminiModelClient, MCP 0.15, A2A 1.0
│   │   ├── chat/          # CoffeeChatController, _session.py, HybridRouteResolver, GroundedRouteService
│   │   ├── products/      # Product, Store, Vector, Apex & ApexAI controllers/services, jobs.py
│   │   ├── system/        # System & Metrics controllers, CacheService, MetricsService, PersonaManager, jobs.py
│   │   └── web/           # PageController and Jinja2 templates/
│   ├── ioc/               # Dishka providers (__init__.py, _config.py, _database.py, _ai.py, _domain.py)
│   ├── lib/               # settings/, di.py, exceptions.py, jobs.py, log/, schema.py, security.py, service.py, text_search.py
│   ├── server/            # Litestar app factory (asgi.py, core.py, plugins.py, mcp/_config.py)
│   └── utils/             # Shared msgspec JSON serialization.py and fixtures.py
├── resources/             # Vite 8, Tailwind CSS v4, HTMX 2, ApexCharts, and vector-calculator.js
└── tests/                 # Flattened unit/ and integration/ pytest suite
tools/
├── ci/                    # AST hygiene (check_code_hygiene.py) and controller security gates
├── cli/                   # Developer manage.py Click groups (main.py, infra.py, database.py, assets.py)
├── demos/                 # VHS terminal (shell.py) and Playwright browser (web.py) recorders (cli.py)
├── deploy/                # Cloud Run Dockerfile, Cloud Build, and Terraform infrastructure
├── lib/                   # Shared developer CLI and subprocess helpers
├── oracle/                # ADB-Free 26ai (adb.py), database.py, wallet.py, apex_lang.py, apex_catalog.py, apex_vertex.py
├── scripts/               # Shell automation helpers (record-live-demos.sh)
└── slides/                # Presentation deck inspection, diffing, highlighting, QR, and validation CLI
```

## 3. Dependency Injection (Dishka)

`src/app/ioc/__init__.py` exports `PROVIDERS = (ConfigProvider, DBProvider, AIProvider, DomainServiceProvider)`, `get_providers(...)`, and `create_container(...)`:

1. **`ConfigProvider` (`src/app/ioc/_config.py`)**:
   - `Scope.APP`: `Settings` (`Settings.from_env()`), typed sub-settings (`AppSettings`, `ServerSettings`, `DatabaseSettings`, `AISettings`, `ChatSettings`, `ViteSettings`, `MapsSettings`, `LogSettings`, `OpenTelemetrySettings`, `QueueSettings`), and `SQLFileLoader` (`default_sql_loader()`).
2. **`DBProvider` (`src/app/ioc/_database.py`)**:
   - `Scope.APP`: `OracleAsyncConfig`, `QueueService`
   - `Scope.REQUEST`: `OracleAsyncDriver` (yielded from `db_config.provide_session()`)
3. **`AIProvider` (`src/app/ioc/_ai.py`)**:
   - `Scope.APP`: `genai.Client` (with mTLS and `gcloud` ADC fallback credentials), `GeminiModelClient`, `AgentRuntime`, `AgentStreamService`, `SpecTree`, `PersonaManager`, `OracleSessionStore`, `OracleEventStore`
4. **`DomainServiceProvider` (`src/app/ioc/_domain.py`)**:
   - `Scope.REQUEST`: `ProductService`, `StoreService`, `CacheService`, `MetricsService`, `HybridRouteResolver`, `VertexAIService`, `GroundedRouteService`, `AgentOrchestrationService`, `OracleVectorSearchService`

> **Note:** Provider modules in `src/app/ioc/` must never use `from __future__ import annotations`; Dishka evaluates provider type annotations at runtime.

## 4. SQLSpec `0.69.0` Pools & Background Queues (`litestar-queues`)

- **Primary Pool (`DatabaseSettings.create_config()` / `get_config()` in `src/app/lib/settings/_database.py`)**: Uses SQLSpec `0.69.0` default `fetch_lobs=False` (returning inline `str` / `bytes` for CLOB/BLOB values under 1 GB without `LOB` locator round-trips), `driver_features={"enable_session_tracing": True}`, wire-level `sqlcommenter` (`enable_sqlcommenter=True`, `sqlcommenter_enable_context=True`, `sqlcommenter_enable_traceparent=True`), `ObservabilityConfig`, and Autonomous Database `wallet_zip` support (`extract_oracle_wallet_zip`, `parse_tnsnames_ora`).
- **Queue Pool (`DatabaseSettings.get_queue_config()`)**: Dedicated `OracleAsyncConfig` (`min=1, max=4`, `session_key="queue_db_session"`, `"manage_lifespan": True`, `driver_features={"fetch_lobs": False, "enable_session_tracing": True}`) backed by Oracle 26ai `FOR UPDATE SKIP LOCKED`, isolating `OracledbAsyncQueueStore` driver/extension mutations from `config.db`.
- **Task Scoping (`src/app/lib/jobs.py`)**: Background tasks (`products.embed_missing` in `src/app/domain/products/jobs.py` and `system.cache_cleanup` in `src/app/domain/system/jobs.py`) resolve request-scoped services via `task_container_scope()`.

## 5. Local ADB-Free 26ai, APEX 26.1 & Demo Tooling

- **ADB-Free 26ai & Test Flavors (`tools/oracle/adb.py`, `tools/oracle/database.py`, `tools/oracle/wallet.py`)**: Interactive local workflows default to `container-registry.oracle.com/database/adb-free:latest-26ai` (`cymbal-adb-free`, bundled ORDS + APEX 26.1 at `https://localhost:8443/ords/apex`, mTLS wallet exported to `.envs/tns` for `myatp_low` on `:1522` via `AdbBootstrap` and `WalletConfigurator`), while `make test-integration` uses `ORACLE_CONTAINER_FLAVOR=free` (`gvenzl/oracle-free:latest`).
- **APEX 26.1 + Vertex AI (`tools/oracle/apex_lang.py`, `tools/oracle/apex_vertex.py`, `src/apex/cymbal-coffee-ops/`)**: `ApexLang` manages SQLcl `26.1.2+` validation/import/export for App ID `100` (Page 6 invokes `APEX_AI.GENERATE` with `COFFEE_VERTEX_AI`), and `ApexVertexConfigurator` provisions `COFFEE_VERTEX_AI` via Method 1 Direct Vertex AI (`/endpoints/openapi` `google/gemini-3.8-flash`) or Method 2 Litestar Gateway (`http://host.docker.internal:8000/api/apex/ai/v1`).
- **Demo Recorders (`tools/demos/cli.py`, `tools/demos/shell.py`, `tools/demos/web.py`)**: `manage.py demos` records deterministic `vhs` terminal tapes and headless Playwright + FFmpeg browser walkthroughs.
