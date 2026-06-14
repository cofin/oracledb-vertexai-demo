# Cymbal Coffee Architecture

Current as of the ADK 2.0 reset branch.

## System Shape

Cymbal Coffee is a two-page Litestar application:

- `/` is the streamed coffee chat.
- `/explore` is the vector search and EXPLAIN PLAN explorer.
- `/api/chat/stream` streams Server-Sent Events from the ADK workflow.
- `/api/vector-demo` returns either HTMX partials or JSON vector-search results.
- `/api/explain-plan` returns Oracle `DBMS_XPLAN.DISPLAY()` output for the vector query.

The backend stack is Litestar, Granian, Dishka, SQLSpec, Oracle Database 26ai,
Google GenAI/Vertex AI, and Google ADK 2.0. The frontend is server-rendered
Jinja/HTMX with Vite, Tailwind v4, vanilla JavaScript, ApexCharts, and a small
`src/resources/main.js` streaming client.

```text
browser
  -> Litestar controllers
  -> Dishka request scope
  -> domain services
  -> SQLSpec Oracle driver and Google GenAI client
  -> Oracle 26ai, Vertex AI, ADK session store
```

## Source Layout

```text
src/app/
  cli/                  # coffee CLI and manage.py command modules
  db/
    migrations/         # SQLSpec migrations
    sql/                # named SQL files loaded by db_manager
    fixtures/           # committed gzipped demo data
  domain/
    chat/
      controllers/      # chat JSON, HTMX, and SSE endpoints
      schemas/          # msgspec API schemas
      services/         # ADK runner, Workflow factory, intent classifier
    products/
      controllers/      # product, store, vector/explain endpoints
      schemas/
      services/         # ProductService, StoreService, VertexAIService
    system/
      controllers/      # health, metrics
      schemas/
      services/         # cache, metrics, persona manager
    web/
      controllers/      # page routes
      templates/        # Jinja pages and partials
  ioc.py                # Dishka providers
  config.py             # lazy Litestar, SQLSpec, session, log config
  server/               # app factory and plugins
```

## Dependency Injection

`src/app/ioc.py` uses three application providers plus `LitestarProvider`:

- `LitestarPersistenceProvider`
  - APP: `OracleAsyncConfig`
  - REQUEST: `OracleAsyncDriver` from `db_manager.provide_session(db)`
- `IntegrationsProvider`
  - APP: Google GenAI `Client`
  - APP: `OracleAsyncADKStore`
  - APP: `SQLSpecSessionService`
  - APP: `FlashLiteIntentClassifier`, `PersonaManager`, `ADKRunner`
- `DomainServiceProvider`
  - REQUEST: product, store, cache, metrics, ADK tool services
  - REQUEST: `VertexAIService` and `OracleVectorSearchService`

Keep `from __future__ import annotations` out of provider modules where Dishka
needs runtime annotations. Normal consumer modules can use postponed annotations.

Handlers request dependencies with `Inject[T]` from `app.lib.di`:

```python
async def vector_search_demo(
    vector_search_service: Inject[OracleVectorSearchService],
) -> Response:
    ...
```

## SQLSpec And Oracle

`app.config` creates one `SQLSpec` manager, adds the Oracle config, and loads
named SQL from `src/app/db/sql`. Domain services call `db_manager.get_sql(...)`
instead of embedding long static SQL strings in Python.

Important patterns:

- Use `schema_type=` for typed results.
- Use `db_manager.get_sql("name")` for static queries.
- Use SQLSpec's builder only for small dynamic additions.
- Pass Python `list[float]` vectors directly; do not wrap them in `array.array`.
- Keep Oracle binds named with `:name`.

Example:

```python
return await self.driver.select(
    db_manager.get_sql("vector-search-products"),
    query_vector=query_embedding,
    threshold=similarity_threshold,
    limit=limit,
    schema_type=ProductMatch,
)
```

The SQLSpec Oracle config also owns extension migrations and storage tables:

```python
extension_config={
    "adk": {
        "session_table": "adk_sessions",
        "events_table": "adk_events",
        "memory_table": "adk_memory_entries",
        "enable_memory": settings.db.ADK_ENABLE_MEMORY,
        "include_memory_migration": settings.db.ADK_ENABLE_MEMORY,
        "in_memory": settings.db.ADK_IN_MEMORY,
    },
    "litestar": {
        "session_table": "app_session",
        "in_memory": settings.db.LITESTAR_SESSION_IN_MEMORY,
    },
}
```

The ADK session backend and the Litestar server-side session backend are related
but separate. The chat controller stores `adk_session_id` and `adk_user_id` in
the Litestar session, then passes those identifiers to ADK's SQLSpec session
service.

## Chat Flow

```text
POST /api/chat/stream
  -> app.domain.chat.session.adk_session_identity()
  -> ADKRunner.stream_request()
  -> SQLSpecSessionService get/create session
  -> response cache lookup
  -> FlashLiteIntentClassifier
  -> PRODUCT_RAG direct vector search and grounded final event
     OR ADK workflow stream for conversational turns:
        START -> intent FunctionNode -> JoinNode
        START -> LlmAgent coffee_turn -> JoinNode
        JoinNode -> classify_and_respond FunctionNode
  -> final event with answer, intent, SQL/query metadata, cache, timing, and session id
```

The LLM tools are closure-bound per request. The closures call
`AgentToolsService`, which holds the request-scoped SQLSpec driver plus product,
cache, metrics, store, and Vertex services. This keeps database sessions aligned
with Litestar request scope while ADK owns only orchestration.

Product RAG turns do not stream speculative model deltas. They classify first,
search the live menu, format a grounded answer only from returned products,
persist display history into ADK session state, cache the final response, and
emit a single final SSE event.

## Store, Inventory, And Maps Expansion

Active store-aware chat planning extends the existing product domain rather than
adding a separate store app. The planned components are:

- store data foundation in the baseline migration and fixtures: coordinates,
  timezone, optional Google place IDs, Dallas store data, explicit product stock
  booleans, and curated `store_product_inventory` rows;
- store and inventory query services behind named SQL and typed schemas;
- closure-bound ADK tools for store lookup, hours, nearest stores, and product
  availability;
- deterministic `STORE_LOCATION` and `PRODUCT_AVAILABILITY` routes beside the
  existing deterministic `PRODUCT_RAG` path;
- HTMX/Jinja chat rendering for store cards, inventory cards, directions links,
  and optional one-at-a-time Maps Embed output.

Maps URLs are the default integration and need no API key. Browser coordinates
are request-scoped and require explicit consent. Embedded maps require separate
settings and a restricted Maps Embed key; do not reuse Gemini or Vertex keys.

## Vector Search Flow

```text
POST /api/vector-demo
  -> VectorController.validate_message()
  -> OracleVectorSearchService.similarity_search()
  -> VertexAIService.get_text_embedding(embedding_purpose="query")
  -> ProductService.search_by_vector()
  -> src/app/db/sql/products.sql:vector-search-products
  -> HTMX partial or JSON response
```

Product and embedding-cache rows store `VECTOR(3072, FLOAT32)` values generated
by `gemini-embedding-2`. HNSW indexes use Oracle 26ai `ORGANIZATION INMEMORY
NEIGHBOR GRAPH`.

## Frontend

Templates live under `src/app/domain/web/templates`.

- `pages/chat.html.j2` posts to `/api/chat/stream`.
- `pages/explore.html.j2` posts vector search requests and fetches plans.
- `partials/_chat_response.html.j2` and `partials/search_result_list.html.j2`
  are the HTMX swap targets.
- `src/resources/main.js` reads SSE manually with `fetch()` and a stream reader.

Do not reintroduce a React SPA. The Vite build exists for static assets and the
small browser helper, not for client-side routing.

## CLI Boundary

Use `coffee` for demo operations:

- `coffee run`
- `coffee upgrade`
- `coffee load-fixtures`
- `coffee bulk-embed`
- `coffee export-fixtures`
- `coffee clear-cache`
- `coffee model-info`

Use `coffee upgrade` as the packaged/end-user install path. It applies SQLSpec
migrations and loads committed fixtures. Use `python manage.py database ...` for
developer SQLSpec commands such as downgrade/current, and `python manage.py init
--run-install` for bootstrap. The Litestar SQLSpec plugin intentionally does not
auto-mount a `db` group onto `coffee`.

## Test Database Lifecycle

Oracle lifecycle belongs to the repo management commands:

```bash
make start-infra
uv run python manage.py database upgrade --no-prompt
uv run coffee load-fixtures
```

The pytest fixtures connect to that configured Oracle database. Integration
setup then makes the test data deterministic:

1. `src/tests/conftest.py` patches app settings for the test DSN.
2. `src/tests/integration/conftest.py` closes any stale SQLSpec pool.
3. The integration `driver` fixture bootstraps required tables idempotently.
4. Fixture-owned tables are truncated.
5. Checked-in fixture data is loaded through the app fixture loader.
6. A deterministic marker product is upserted for older integration assertions.
7. The SQLSpec pool is closed after each test to avoid event-loop reuse issues.

If an integration test cannot connect, start the managed Oracle container and
run the migration command above. Keep lifecycle ownership in `manage.py` and
`make`; pytest should only prepare deterministic schema/data inside the already
configured database.

## Operational Notes

- Local Oracle startup configures `vector_memory_size` before HNSW INMEMORY
  indexes are created.
- `ORACLE_ADK_IN_MEMORY` and `ORACLE_LITESTAR_SESSION_IN_MEMORY` default to true
  and control Oracle INMEMORY storage for SQLSpec extension tables.
- Placeholder Vertex project IDs are rejected before ADK starts so expected
  local misconfiguration returns a clean 503.
- `app.config` builds `StructlogConfig` from
  `app.lib.log.structlog_processors()` and `stdlib_logger_processors()`.
  Settings set Litestar / Granian logging env defaults. Static assets are
  excluded from request logs, and `app.config.setup_logging()` filters only
  known ADK/Authlib warning noise so real runtime exceptions stay visible.
