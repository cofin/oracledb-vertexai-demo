# Oracle 26ai + Vertex AI Demo - Agent Configuration

This file gives agents a current project context for the Cymbal Coffee demo.
Keep it short, code-grounded, and aligned with `.agents/bundles/index.md`.

## Project Overview

**Purpose**: Coffee recommendation demo using Oracle 26ai Hybrid RRF search
(BM25-style lexical `CONTAINS`/`SCORE` + HNSW `VECTOR(3072, FLOAT32)`),
Google Vertex AI embeddings (`gemini-embedding-2`), native dynamic agent
orchestration (`Gemini 3.8 Flash`), `LitestarMCP`, `LitestarA2A`,
`litestar-queues` on Oracle 26ai, and store-aware planning for locations,
inventory, and maps.

**Current stack**:

- **Framework**: Litestar 2 with HTMX, Jinja templates, and `litestar-vite` template mode.
- **Server**: Granian via `uv run coffee run`.
- **Database**: Oracle 26ai with SQLSpec, named SQL files, JSON, BOOLEAN, `CTXSYS.CONTEXT` (`MULTI_COLUMN_DATASTORE`), and `VECTOR(3072, FLOAT32)` (`FETCH APPROX`).
- **AI & Retrieval**: Vertex AI `gemini-embedding-2` (3072 dims), single-query Oracle 26ai Hybrid RRF routing (`hybrid-search-turn` + `hybrid-term-hits`), and `Gemini 3.8 Flash` (`google-genai`) chat/tool turns.
- **Agent runtime**: Native `domain/ai` runtime with re-entrant `AgentRuntime`, `GeminiModelClient`,
  and Oracle-backed session/event stores (`agent_session`, `agent_event`).
- **Protocols**: `LitestarMCP` 0.15 (`POST /mcp` with `CoffeeMCPController`, `CoffeeSkillController`, `CoffeePromptController`) and `LitestarA2A` (`POST /a2a`, `GET /.well-known/agent-card.json`).
- **Queues**: `litestar-queues[sqlspec]>=0.12.0` on Oracle 26ai `FOR UPDATE SKIP LOCKED` with a dedicated LOB-isolated `DatabaseSettings.get_queue_config()` pool (`session_key="queue_db_session"`).
- **DI**: Dishka with three modular provider modules in `src/app/ioc/` (`_database.py`, `_ai.py`, `_domain.py`).
- **Security & Tracing**: `litestar-security` with `PublicController` (CSRF re-enabled on cookie-session POSTs, optional `MCP_API_KEY` on `/mcp` and `/a2a`) and OpenTelemetry enabled by default.

## Project Context

The active agent context lives under `.agents/bundles/`:

- [Bundle index](.agents/bundles/index.md)
- [Workflow](.agents/bundles/knowledge/workflow.md)
- [Patterns index](.agents/bundles/knowledge/patterns/index.md)
- [Architecture guide](.agents/bundles/knowledge/guides/architecture.md)
- [Oracle database guide](.agents/bundles/knowledge/guides/oracle-database.md)
- [Hybrid search & RRF guide](.agents/bundles/knowledge/guides/hybrid-search.md)
- [Native AI runtime guide](.agents/bundles/knowledge/guides/agentic-ai-runtime.md)
- [Store, inventory & maps guide](.agents/bundles/knowledge/guides/store-inventory-maps.md)

Durable lessons must live in `.agents/bundles/knowledge/` or `.agents/bundles/knowledge/patterns/`.

## Development Commands

```bash
# Setup
make install
uv run python manage.py init --run-install

# Local Oracle
make start-infra
uv run coffee upgrade

# App & Background Workers
uv run coffee run
uv run coffee worker run
uv run coffee worker status
uv run coffee bulk-embed
uv run coffee export-fixtures
uv run coffee clear-cache
uv run coffee model-info

# Verification
make lint
make test
make coverage
```

`coffee` is the hand-rolled app CLI. `coffee upgrade` is the packaged/end-user
install command; it applies migrations and loads committed fixtures. Keep raw
SQLSpec developer commands such as downgrade/current on `python manage.py
database ...`, not on `coffee`. Keep `bulk-embed` and `export-fixtures` on
`coffee`; they are maintainer lifecycle commands for committed demo data. Keep
large command workflows under `app.cli._helpers`; keep small command-local
helpers in `commands.py`. Do not add compatibility shim or facade modules. Use
`@async_inject` for async Click commands.

## Project Structure

```text
src/app/
├── cli/
│   ├── _helpers/          # substantial private CLI workflow helpers
│   ├── commands.py        # click command declarations (incl. worker/queues)
│   ├── main.py            # coffee click group
│   └── utils.py           # async_inject
├── db/
│   ├── fixtures/          # committed demo fixture data
│   ├── migrations/        # SQLSpec migrations (0001 baseline, 0002 agent & hybrid RRF)
│   └── sql/               # named SQL files (products, stores, inventory, system, ai-runtime, hybrid)
├── domain/
│   ├── ai/
│   │   ├── a2a/           # LitestarA2A card & CoffeeAgentExecutor
│   │   ├── mcp/           # LitestarMCP 0.15 controllers (tools, skills, prompts)
│   │   ├── runtime/       # AgentRuntime, GeminiModelClient, OracleSessionStore/EventStore, SSE stream
│   │   └── services/      # AgentOrchestrationService
│   ├── chat/
│   │   ├── controllers/
│   │   ├── schemas/
│   │   └── services/      # HybridRouteResolver, grounded composers, closure tools, telemetry
│   ├── products/
│   │   ├── controllers/
│   │   ├── jobs.py        # @task("products.embed_missing")
│   │   ├── schemas/
│   │   └── services/
│   ├── system/
│   │   ├── controllers/
│   │   ├── jobs.py        # @task("system.cache_cleanup")
│   │   ├── schemas/
│   │   └── services/
│   └── web/
│       ├── controllers/
│       ├── static/
│       └── templates/
├── ioc/                   # Dishka providers (_database.py, _ai.py, _domain.py)
├── lib/                   # modular settings/, di.py, jobs.py, log/, service.py
├── server/                # Litestar app factory and plugin wiring
└── utils/                 # shared helpers

src/tests/
├── api/
├── integration/
└── unit/

tools/
├── cli/
└── oracle/
```

## Core Patterns

### SQLSpec Services & HNSW Vector Search

Use named SQL from `db/sql/*.sql` and typed result mapping. Do not reintroduce
manual vector packing; SQLSpec Oracle handles Python `list[float]` values.
Oracle HNSW indexes (`INMEMORY NEIGHBOR GRAPH`) require `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX FIRST :limit ROWS ONLY`:

```python
from app.config import db_manager
from app.domain.products.schemas import ProductMatch
from app.lib.service import OracleAsyncService


class ProductService(OracleAsyncService):
    async def search_by_vector(
        self, query_embedding: list[float], similarity_threshold: float = 0.7, limit: int = 5
    ) -> list[ProductMatch]:
        return await self.driver.select(
            db_manager.get_sql("vector-search-products"),
            query_vector=query_embedding,
            threshold=similarity_threshold,
            limit=limit,
            schema_type=ProductMatch,
        )
```

### Dishka DI

Use handler-argument injection. `setup_dishka` and `AutowirePlugin(AutowireConfig(domain_packages=["app.domain"], integrations=["dishka", "queues"]))`
resolve dependencies; route-level `@inject` decorators are not the local pattern.

```python
from app.domain.products.services import ProductService
from app.lib.di import Inject


async def list_products(products_service: Inject[ProductService]) -> ProductList:
    products, total = await products_service.list_with_count()
    return ProductList(items=products, total=total)
```

Provider modules under `src/app/ioc/` must not use `from __future__ import annotations`; Dishka reads
provider annotations at runtime.

### Vertex AI & Single-Query Hybrid RRF

Pass `embedding_purpose="query"` for user search queries and
`embedding_purpose="document"` for product/route embeddings. Runtime settings use
`gemini-embedding-2` with `EMBEDDING_DIMENSIONS = 3072`.

Turn routing and candidate retrieval use a single Oracle 26ai Hybrid RRF query (`hybrid-search-turn` in `src/app/db/sql/hybrid.sql`) combining BM25-style lexical ranking (`CONTAINS`/`SCORE` over `MULTI_COLUMN_DATASTORE`) and HNSW vector similarity (`VECTOR_DISTANCE ... FETCH APPROX`) at $k=60$, plus `hybrid-term-hits` (`JSON_TABLE` + `CONTAINS`) for off-menu brand detection.

### Native AI Runtime, MCP, A2A & Background Queues

AI conversation state is stored through `OracleSessionStore` (`agent_session`)
and `OracleEventStore` (`agent_event`). Litestar browser sessions are separate
and bridged only at the chat controller boundary when deriving `session_id`.

Tools are closure-bound per turn with `CallContext`, accessing the active Dishka
request services. Streaming responses use `/api/chat/stream` adapted by
`AgentStreamService`, emitting structured event frames (`session`, `tool_call`,
`tool_end`, `delta`, `ping`, `final`) with 5s keep-alive pings and the full `ChatResponse` telemetry contract.

Background jobs use `litestar-queues` with a dedicated `OracleAsyncConfig` from `DatabaseSettings.get_queue_config()` (`session_key="queue_db_session"`) so `OracledbAsyncQueueStore`'s `fetch_lobs=False` mutation never disables `enable_AutoLob=True` on `config.db`.

### Store, Inventory, And Maps

Store/location work stays in the products domain. `STORE_LOCATION` and
`PRODUCT_AVAILABILITY` are deterministic grounded routes like `PRODUCT_RAG`;
`ORDER_STATUS` stays explicit but unsupported until order data exists. Browser
coordinates require user opt-in, stay request-scoped, and must not be persisted
in history, cache, metrics, or logs.

### Settings

Settings are modularized under `src/app/lib/settings/` (`_base.py`, `_app.py`, `_database.py`, `_ai.py`, `_vite.py`, `_maps.py`, `_mcp.py`, `_queue.py`) with cached `Settings.from_env()`.

## Testing Patterns

Prefer AnyIO tests for async code:

```python
import pytest


@pytest.mark.anyio
async def test_vector_search(product_service: ProductService) -> None:
    results = await product_service.search_by_vector([0.1] * 3072, limit=5)
    assert len(results) <= 5
```

## Important Notes

1. Oracle uses `:name` bind parameters and `VECTOR(3072, FLOAT32)`.
2. HNSW INMEMORY vector indexes require `vector_memory_size` before index DDL and `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST :limit ROWS ONLY` at query time.
3. `ORACLE_AGENT_IN_MEMORY` and `ORACLE_LITESTAR_SESSION_IN_MEMORY` default to true.
4. Placeholder Vertex project IDs fail as typed 503 responses (`AIServiceUnconfigured`), not generic 500s.
5. Store/maps work must preserve no-key Maps URL behavior and coordinate privacy.
6. `DatabaseSettings.get_queue_config()` must remain separate from `DatabaseSettings.get_config()` so `enable_AutoLob=True` is preserved on `config.db`.
7. `make lint` and `make test` are the aggregate gates before calling work complete.

## Workflow

Use Flow OKF bundle state under `.agents/bundles/` as the task source of truth. Read the relevant
`.agents/bundles/specs/<flow>/spec.md` and authoritative worksheets under `tasks/`, update `learnings.md` when a durable lesson is
found, and keep `.agents/bundles/knowledge/patterns/` current when the convention should survive
the task.
