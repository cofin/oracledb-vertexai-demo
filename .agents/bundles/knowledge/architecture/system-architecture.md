---
type: Guide
title: System Architecture
description: High-level system architecture, package boundaries, Dishka dependency injection scopes, and background queue architecture
tags:
  - architecture
  - litestar
  - dishka
  - queues
---

# System Architecture

## 1. Multi-Protocol Application Surface

Cymbal Coffee is a multi-protocol Litestar 2 application served by Granian (`uv run coffee run`):

- `GET /` — Primary interactive coffee concierge chat UI (Jinja2 + HTMX + SSE).
- `GET /explore` — Vector search laboratory, RRF telemetry dashboard, and Oracle `EXPLAIN PLAN` inspector.
- `POST /api/chat/stream` — Server-Sent Event (`ServerSentEvent`) stream emitted by `AgentStreamService`.
- `POST /api/vector-demo` — Vector search endpoint returning HTMX HTML partials or JSON results.
- `POST /api/explain-plan` — Oracle `DBMS_XPLAN.DISPLAY()` execution plan inspection for HNSW queries.
- `GET /api/stores/{store_id}/inventory` — Store inventory modal partial.
- `POST /mcp` — Stateless Model Context Protocol (`LitestarMCP` 0.15) exposing tools, skills, and prompts.
- `POST /a2a` & `GET /.well-known/agent-card.json` — Agent-to-Agent Protocol (`LitestarA2A`).

## 2. Package & Source Layout

```text
src/app/
├── cli/
│   ├── _helpers/          # CLI workflow helpers (embeddings, fixtures, upgrade)
│   ├── commands.py        # Click command declarations (run, upgrade, worker, bulk-embed)
│   ├── main.py            # coffee Click group
│   └── utils.py           # @async_inject decorator
├── config.py              # Leaf composition bridge for server/CLI entrypoints only
├── db/
│   ├── fixtures/          # Committed compressed JSON fixtures (store, product, inventory, chat_route)
│   ├── migrations/        # SQLSpec baseline migration (0001_cymball_coffee_products.sql)
│   └── sql/               # Named SQL files (products, stores, inventory, system, ai-runtime, hybrid)
├── domain/
│   ├── ai/                # Native AgentRuntime, GeminiModelClient, MCP 0.15, A2A 1.0
│   ├── chat/              # Chat controller, HybridRouteResolver, grounded composers, telemetry
│   ├── products/          # Product & Store services, VertexAIService, @task("products.embed_missing")
│   ├── system/            # Health, CacheService, MetricsService, @task("system.cache_cleanup")
│   └── web/               # PageController, Jinja2 templates
├── ioc/                   # Dishka providers (_database.py, _ai.py, _domain.py)
├── lib/                   # Modular settings/, di.py, jobs.py, log/, schema.py, service.py, sql.py
├── server/                # Litestar app factory (asgi.py, core.py, plugins.py)
└── utils/                 # Shared serialization helpers
```

## 3. Dependency Injection (Dishka)

Four modular Dishka providers are registered in `src/app/ioc/`:

1. **`ConfigProvider` (`src/app/ioc/_database.py`)**:
   - `Scope.APP`: `Settings` (`Settings.from_env()`)
2. **`DBProvider` (`src/app/ioc/_database.py`)**:
   - `Scope.APP`: `SQLSpec`, `OracleAsyncConfig`, `QueueService`
   - `Scope.REQUEST`: `OracleAsyncDriver` (yielded from `sqlspec.provide_session(db_config)`)
3. **`AIProvider` (`src/app/ioc/_ai.py`)**:
   - `Scope.APP`: `genai.Client`, `GeminiModelClient`, `OracleSessionStore`, `OracleEventStore`, `AgentRuntime`, `SpecTree`, `CoffeeAgentExecutor`
4. **`DomainServiceProvider` (`src/app/ioc/_domain.py`)**:
   - `Scope.REQUEST`: `ProductService`, `StoreService`, `CacheService`, `MetricsService`, `VertexAIService`, `OracleVectorSearchService`, `HybridRouteResolver`, `GroundedRouteService`, `AgentOrchestrationService`, `AgentStreamService`

> [!IMPORTANT]
> Provider modules in `src/app/ioc/` must never use `from __future__ import annotations`; Dishka evaluates provider type annotations at runtime.

## 4. Background Task Queues (`litestar-queues`)

Background jobs run on `litestar-queues[sqlspec]` backed by Oracle 26ai `FOR UPDATE SKIP LOCKED`:
- Dedicated pool: `DatabaseSettings.get_queue_config()` (`session_key="queue_db_session"`) isolates `OracledbAsyncQueueStore`'s `fetch_lobs=False` driver mutation from the primary `config.db` pool.
- Tasks (`products.embed_missing` and `system.cache_cleanup`) resolve request-scoped services via `create_task_container()` in `src/app/lib/jobs.py`.
