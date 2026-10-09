# Oracle 26ai + Vertex AI Demo - Agent Configuration

This file gives agents a current project context for the Cymbal Coffee demo.
Keep it short, code-grounded, and aligned with `.agents/index.md`.

## Project Overview

**Purpose**: Coffee recommendation demo using Oracle 26ai vector search,
Google Vertex AI embeddings, native dynamic agent orchestration (Gemini 3.8 Flash),
LitestarMCP, LitestarA2A agent protocol, and store-aware planning for locations,
inventory, and maps.

**Current stack**:

- **Framework**: Litestar 2 with HTMX, Jinja templates, and litestar-vite template mode.
- **Server**: Granian via `uv run coffee run`.
- **Database**: Oracle 26ai with SQLSpec, named SQL files, JSON, BOOLEAN, and `VECTOR(3072, FLOAT32)`.
- **AI**: Vertex AI `gemini-embedding-2` embeddings, Gemini 3.8 Flash chat/intent calls.
- **Agent runtime**: Native `domain/ai` runtime with re-entrant `AgentRuntime`, `GeminiModelClient`,
  and Oracle-backed session/event stores (`AGENT_SESSION`, `AGENT_EVENT`).
- **Protocols**: LitestarMCP (`POST /mcp`) and LitestarA2A (`POST /a2a`, `GET /.well-known/agent-card.json`).
- **DI**: Dishka with three app providers in `src/app/ioc.py`.
- **Security & Tracing**: `litestar-security` with `PublicController` and OpenTelemetry enabled by default.
- **Shipped components**: store coordinates/inventory, deterministic store and
  product-availability chat routes, browser location opt-in, and no-key Maps
  URLs.
- **Forward-looking components**: optional Maps Embed and settings contract
  cleanup.

## Project Context

The active agent context lives under `.agents/bundles/`:

- [Bundle index](.agents/bundles/index.md)
- [Workflow](.agents/bundles/knowledge/workflow.md)
- [Patterns index](.agents/bundles/knowledge/patterns/index.md)
- [Architecture guide](.agents/bundles/knowledge/guides/architecture.md)
- [Oracle database guide](.agents/bundles/knowledge/guides/oracle-database.md)
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

# App
uv run coffee run
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
│   ├── commands.py        # click command declarations
│   ├── main.py            # coffee click group
│   └── utils.py           # async_inject
├── db/
│   ├── fixtures/          # committed demo fixture data
│   ├── migrations/        # SQLSpec migrations
│   └── sql/               # named SQL files
├── domain/
│   ├── chat/
│   │   ├── controllers/
│   │   ├── schemas/
│   │   └── services/
│   ├── products/
│   │   ├── controllers/
│   │   ├── schemas/
│   │   └── services/
│   ├── system/
│   │   ├── controllers/
│   │   ├── schemas/
│   │   └── services/
│   └── web/
│       ├── controllers/
│       ├── static/
│       └── templates/
├── lib/                   # settings, DI, logging, SQLSpec service exports
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

### SQLSpec Services

Use named SQL from `db/sql/*.sql` and typed result mapping. Do not reintroduce
manual vector packing; SQLSpec Oracle handles Python `list[float]` values.

```python
from app.config import db_manager
from app.domain.products.schemas import ProductMatch
from app.lib.service import OracleAsyncService


class ProductService(OracleAsyncService):
    async def search_by_vector(self, query_embedding: list[float]) -> list[ProductMatch]:
        return await self.driver.select(
            db_manager.get_sql("vector-search-products"),
            query_vector=query_embedding,
            threshold=0.5,
            limit=5,
            schema_type=ProductMatch,
        )
```

### Dishka DI

Use handler-argument injection. `setup_dishka` and `DomainPlugin(use_dishka_router=True)`
resolve dependencies; route-level `@inject` decorators are not the local pattern.

```python
from app.domain.products.services import ProductService
from app.lib.di import Inject


async def list_products(products_service: Inject[ProductService]) -> ProductList:
    products, total = await products_service.list_with_count()
    return ProductList(items=products, total=total)
```

`src/app/ioc.py` must not use `from __future__ import annotations`; Dishka reads
provider annotations at runtime.

### Vertex AI

Pass `embedding_purpose="query"` for user search queries and
`embedding_purpose="document"` for product/document embeddings. The value
selects a text instruction prefix from `EMBEDDING_PURPOSE_INSTRUCTIONS` that is
prepended to the content; no `task_type` parameter is sent. Runtime settings use
`gemini-embedding-2` with `EMBEDDING_DIMENSIONS = 3072`.

### Native AI Runtime & Chat

AI conversation state is stored through `OracleSessionStore` (`AGENT_SESSION`)
and `OracleEventStore` (`AGENT_EVENT`). Litestar browser sessions are separate
and bridged only at the chat controller boundary when deriving `session_id`.

Tools are closure-bound per turn with `CallContext`, accessing the active Dishka
request services. Streaming responses use `/api/chat/stream` adapted by
`AgentStreamService`, emitting structured event frames (`session`, `tool_call`,
`tool_end`, `delta`, `ping`, `final`) with 5s keep-alive pings.

Multi-protocol machine interfaces are exposed simultaneously:
- **MCP (`LitestarMCP`)**: `POST /mcp` with route tools (`mcp_tool="search_coffee_products"`).
- **A2A (`LitestarA2A`)**: `POST /a2a` with JSON-RPC agent execution and `GET /.well-known/agent-card.json`.

### Store, Inventory, And Maps

Store/location work stays in the products domain. The baseline `0001` migration
ships the supporting data: store coordinates/timezone/place IDs, Dallas fixture
data, explicit product stock booleans, and curated `store_product_inventory`
rows. Query behavior uses named SQL and typed service boundaries.

`STORE_LOCATION` and `PRODUCT_AVAILABILITY` are deterministic grounded routes
like `PRODUCT_RAG`; `ORDER_STATUS` stays explicit but unsupported until order
data exists. Browser coordinates require user opt-in, stay request-scoped,
and must not be persisted in history, cache, metrics, or logs.

Google Maps URLs are the default and require no key. Embedded maps require
`MAPS_ENABLE_EMBED=true`, a separate restricted `GOOGLE_MAPS_EMBED_API_KEY`, and
security headers that do not grant geolocation to the iframe.

### Settings

Settings remain dataclass-based with cached `Settings.from_env()`. The
consolidation plan is to remove unused future knobs, make settings quiet and
effectively immutable, let shell env override `.env`, and keep optional Maps
settings only when the maps implementation wires them.

## Testing Patterns

Prefer AnyIO tests for async code:

```python
import pytest


@pytest.mark.anyio
async def test_vector_search(product_service: ProductService) -> None:
    results = await product_service.search_by_vector([0.1] * 3072, limit=5)
    assert len(results) <= 5
```

Integration tests use real Oracle through the repo-managed Oracle lifecycle
(`make start-infra` and `uv run python manage.py database upgrade --no-prompt`).
Keep unit tests deterministic with service mocks where the handler can return
before database work but Litestar still resolves DI parameters.

## Important Notes

1. Oracle uses `:name` bind parameters and `VECTOR(3072, FLOAT32)`.
2. HNSW INMEMORY vector indexes require `vector_memory_size` before index DDL.
3. `ORACLE_ADK_IN_MEMORY` and `ORACLE_LITESTAR_SESSION_IN_MEMORY` default to true.
4. Placeholder Vertex project IDs should fail as typed 503 responses, not generic 500s.
5. Store/maps work must preserve no-key Maps URL behavior and coordinate privacy.
6. Settings cleanup should delete unused knobs instead of preserving placeholders.
7. `make lint` and `make test` are the aggregate gates before calling work complete.

## Workflow

Use Flow OKF bundle state under `.agents/bundles/` as the task source of truth. Read the relevant
`.agents/bundles/specs/<flow>/spec.md` and authoritative worksheets under `tasks/`, update `learnings.md` when a durable lesson is
found, and keep `.agents/bundles/knowledge/patterns/` current when the convention should survive
the task.
