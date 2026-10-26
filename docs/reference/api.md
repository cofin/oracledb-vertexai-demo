# API reference

HTTP route catalog, protocol endpoints, and generated Python API documentation for the controllers, native `google-genai` runtime, Oracle 26ai Hybrid RRF router, `OracleLoaderService` data services, and `msgspec.Struct` wire schemas.

## HTTP routes and protocol endpoints

Every HTTP controller inherits from `litestar_security.PublicController` (enforced in CI by `tools/ci/check_litestar_security.py`). Interactive OpenAPI 3.1 documentation is served by Scalar at `/schema` (`/schema/scalar`) with the raw specification at `/schema/openapi.json`.

### Web pages and streaming chat

| Method & Path | Controller | Purpose |
| --- | --- | --- |
| `GET /` | `PageController` | Render the primary coffee chat page (`pages/chat.html.j2`) with restored session history. |
| `GET /explore` | `PageController` | Render the Hybrid RRF, HNSW vector search, and live `EXPLAIN PLAN` explorer (`pages/explore.html.j2`). |
| `POST /api/chat/stream` | `CoffeeChatController` | Stream Server-Sent Event (`text/event-stream`) frames for a chat turn via `AgentOrchestrationService`. |
| `POST /api/chat/session/clear` | `CoffeeChatController` | Clear the active anonymous browser chat session and its persisted Oracle history. |

### Product catalog, stores, and vector explorer

| Method & Path | Controller | Purpose |
| --- | --- | --- |
| `GET /api/products` | `ProductController` | Paginated product catalog (`ListProducts`) with search and sort filters. |
| `GET /api/products/{product_id:int}` | `ProductController` | Fetch a single product by primary key (`GetProduct`; MCP tool `get_product`). |
| `GET /api/stores` | `StoreController` | Paginated store directory (`ListStores`) with name, address, and city search. |
| `GET /api/stores/{store_id:int}/inventory` | `StoreController` | Render an HTMX partial (`partials/_inventory_list.html.j2`) for one store's inventory (`StoreInventory`). |
| `GET /api/stores/{store_id:int}/inventory/raw` | `StoreController` | Return JSON store inventory availability rows (`StoreInventoryData`; MCP tool `get_store_inventory`). |
| `POST /api/vector-demo` | `VectorController` | Execute Hybrid RRF product search; returns an HTMX partial with out-of-band `EXPLAIN PLAN` or a `VectorDemo` JSON body. |
| `GET /api/explain-plan` | `VectorController` | Return the live Oracle `DBMS_XPLAN` output for `query` (`mode=hybrid` default or `mode=vector`). |
| `GET /api/vector-search` | `VectorController` | Hybrid RRF product search (with HNSW vector fallback) by `query` and `limit` (`1..20`, default `5`; MCP tool `search_products`). |

### Oracle APEX REST Source Catalog and Vertex AI Gateway

| Method & Path | Controller | Purpose |
| --- | --- | --- |
| `GET /api/apex/products` | `ApexController` | APEX-safe product catalog (`ApexListProducts`) with `q`, `category`, `limit`, and `offset`. |
| `GET /api/apex/stores` | `ApexController` | Seeded store directory with safe map metadata (`ApexListStores`). |
| `GET /api/apex/inventory/summary` | `ApexController` | Per-store stock status counts (`ApexInventorySummary`). |
| `GET /api/apex/stores/{store_id:int}/inventory` | `ApexController` | Inventory rows for a single store (`ApexStoreInventory`). |
| `GET /api/apex/products/{product_id:int}/availability` | `ApexController` | Store-by-store pickup availability for one product (`ApexProductAvailability`). |
| `POST /api/apex/recommendations` | `ApexController` | Hybrid/vector recommendations with deterministic catalog fallback (`ApexCreateRecommendations`). |
| `GET /api/apex/vector/status` | `ApexController` | Vertex AI embedding provider and Oracle 26ai vector index readiness (`ApexVectorStatus`). |
| `GET /api/apex/openapi/status` | `ApexController` | APEX REST catalog metadata and exported operation IDs (`ApexOpenAPIStatus`). |
| `GET /api/apex/ai/v1/models` | `ApexAIController` | OpenAI-compatible model card list (`ApexAIListModels`, `src/app/domain/products/controllers/_apex_ai.py`) for APEX 26.1 Generative AI Service (`COFFEE_VERTEX_AI`) connection checks; optional `APEX_GATEWAY_API_KEY` Bearer auth. |
| `POST /api/apex/ai/v1/chat/completions` | `ApexAIController` | OpenAI-compatible Chat Completions gateway (`ApexAIChatCompletions`, JSON or `stream=True` SSE) backed by `GeminiModelClient`; optional `APEX_GATEWAY_API_KEY` Bearer auth. |

### Telemetry, health, MCP, and A2A

| Method & Path | Component | Purpose |
| --- | --- | --- |
| `GET /api/metrics/summary` | `MetricsController` | Summary KPI cards for `/explore` latency and cache hit-rate panels. |
| `GET /api/metrics/charts` | `MetricsController` | Time-series and latency breakdown chart datasets for `/explore`. |
| `GET /health`, `GET /api/system/health` | `SystemController` | Liveness check returning `{"status": "ok"}`. |
| `GET /favicon.ico` | `SystemController` | Serve `favicon.ico` from packaged public assets (`include_in_schema=False`). |
| `POST /mcp` | `LitestarMCP` | Streamable HTTP MCP JSON-RPC endpoint exposing tools (`get_product`, `get_store_inventory`, `search_products`, `describe_barista_capabilities`), `CoffeePromptController`, `CoffeeSkillController`, and `.agents/skills/` (`MCP_API_KEY` optional API-key auth). |
| `POST /a2a` | `LitestarA2A` | A2A 1.0 JSON-RPC endpoint backed by `CoffeeAgentExecutor` (`MCP_API_KEY` optional API-key auth). |
| `GET /.well-known/agent-card.json` | `LitestarA2A` | A2A 1.0 agent card discovery document. |

## Controllers

```{eval-rst}
.. autoclass:: app.domain.products.controllers.ApexController
   :no-members:

.. autoclass:: app.domain.products.controllers.ApexAIController
   :no-members:

.. autoclass:: app.domain.chat.controllers.CoffeeChatController
   :no-members:

.. autoclass:: app.domain.products.controllers.ProductController
   :no-members:

.. autoclass:: app.domain.products.controllers.StoreController
   :no-members:

.. autoclass:: app.domain.products.controllers.VectorController
   :no-members:

.. autoclass:: app.domain.system.controllers.MetricsController
   :no-members:

.. autoclass:: app.domain.system.controllers.SystemController
   :no-members:

.. autoclass:: app.domain.web.controllers.PageController
   :no-members:
```

## Agent orchestration, runtime & hybrid router

The native `google-genai` turn orchestrator, `GeminiModelClient`, and single-query Oracle 26ai Hybrid RRF router that tie the Litestar chat and APEX AI gateway controllers to grounded row-rendered routes, `CallContext`-bound tools (`CoffeeToolContext`), and multi-step `AgentRuntime` conversations.

```{eval-rst}
.. autoclass:: app.domain.ai.services.AgentOrchestrationService
   :members:

.. autoclass:: app.domain.ai.runtime.AgentRuntime
   :members:

.. autoclass:: app.domain.ai.runtime.GeminiModelClient
   :members:

.. autoclass:: app.domain.chat.services.HybridRouteResolver
   :members:

.. autoclass:: app.domain.chat.services.GroundedRouteService
   :members:
```

## Services

`OracleAsyncService` and `OracleLoaderService` subclasses that own the named-SQL queries (`self.get_sql(...)` via `default_sql_loader()`), SQLSpec builder CRUD, Vertex AI embeddings, and `/explore` metrics projections.

```{eval-rst}
.. autoclass:: app.lib.service.OracleAsyncService
   :members:

.. autoclass:: app.lib.service.OracleLoaderService
   :members:

.. autoclass:: app.domain.products.services.ProductService
   :members:

.. autoclass:: app.domain.products.services.StoreService
   :members:

.. autoclass:: app.domain.products.services.OracleVectorSearchService
   :members:

.. autoclass:: app.domain.products.services.VertexAIService
   :members:

.. autoclass:: app.domain.system.services.CacheService
   :members:

.. autoclass:: app.domain.system.services.MetricsService
   :members:
```

## Schemas

Immutable, GC-exempt `msgspec.Struct` types (`FrozenBaseStruct` and `CamelizedFrozenStruct`) used for HTTP request/response bodies, OpenAI-compatible APEX AI gateway payloads (`src/app/domain/products/schemas/_apex_ai.py`), named-SQL row mapping, and tool payloads.

```{eval-rst}
.. automodule:: app.lib.schema
   :members:

.. automodule:: app.domain.chat.schemas
   :members:

.. automodule:: app.domain.products.schemas
   :members:

.. automodule:: app.domain.system.schemas
   :members:
```
