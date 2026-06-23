# Cymbal Coffee Project Knowledge Guide

Current guide for agent work in the Cymbal Coffee Oracle 26ai + Vertex AI demo.
This file synthesizes reusable knowledge from completed work so active docs do
not need to link into `.agents/archive/`.

## Source Of Truth

- Start with `.agents/patterns.md` for mandatory current conventions.
- Use `guides/architecture.md` for service boundaries and request flow.
- Use `guides/oracle-vector-search.md` for Oracle vector, HNSW, embedding, and
  EXPLAIN PLAN behavior.
- Use `guides/adk-agent-patterns.md` for ADK sessions, runner flow, tools,
  streaming, cache, and chat result contracts.
- Use `.agents/flows.md` only to find active specs and current Flow state.
- Use `guides/architecture.md` for the store/location/inventory/maps component
  boundaries; those features ship in source.
- Do not rely on `.agents/archive/`; it is ignored disposable history.

## Application Shape

Cymbal Coffee is a Litestar app served by Granian. It has a streamed chat page,
an Oracle vector-search explorer, SQLSpec migrations/fixtures, and a small
Vite-built browser helper. Frontend behavior is HTMX/Jinja/Tailwind v4 with
vanilla JavaScript and ApexCharts, not React, TanStack Router, Bun, Biome, or a
client-side SPA.

The app also ships store-aware chat, store-level inventory, browser location
opt-in, Google Maps URL actions, and the narrowed dataclass settings contract
as first-class components. Optional Maps Embed remains forward-looking. Keep
all shipped components current in knowledge updates.

Domain behavior belongs under `src/app/domain/<domain>/controllers`,
`schemas`, and `services`. Cross-domain use should go through public package
exports or request-scoped services, not deep imports into private modules.

## Data And SQL

SQLSpec owns Oracle access through the configured `db_manager` and named SQL in
`src/app/db/sql`. Static reads should use `db_manager.get_sql("name")`; dynamic
writes should use SQLSpec builders where they reduce string assembly. Bind
parameters by name and never interpolate user input into SQL strings.

Use typed `schema_type=` reads when a schema exists. Response-cache hot reads
should stay typed `select_one_or_none()` calls with expiration filtering in SQL;
maintenance deletion belongs in explicit cache cleanup commands.

The schema baseline uses modern Oracle types, including `BOOLEAN`, `JSON`, and
`VECTOR(3072, FLOAT32)`. Fixture loading must keep dependency order stable:
stores before dependent semantic/product rows, product rows before embeddings or
search metrics.

## Store, Inventory, And Maps Components

Store-aware chat is built from five linked components:

- Data foundation: the baseline `0001` migration carries store
  latitude/longitude/timezone/place-id fields plus a normalized
  `store_product_inventory` table, the Dallas Arts District store, explicit
  product `in_stock` booleans, and curated inventory fixtures.
- Query services: store, hours, nearest-store, inventory, and product
  availability lookups sit behind named SQL and product-domain service methods.
  Nearest-store ranking uses seeded coordinates plus Haversine
  (`_location.haversine_miles`); chat never calls Google geocoding, Places,
  Distance Matrix, or Routes APIs. Availability queries resolve target products
  using exact match, falling back to pronoun resolution from session state, and
  finally Vertex AI vector search for partial or imprecise names.
- ADK tools and intent routing: deterministic `STORE_LOCATION` and
  `PRODUCT_AVAILABILITY` routes gather store/product/inventory facts before
  answering. `ORDER_STATUS` stays explicit but unsupported until order data
  exists.
- Browser UI: location is opt-in from a user click, never page load. Coordinates
  stay in memory for the page session and are sent only with consent. The chat
  shell renders store cards, inventory status, hours, phone/address, distance
  when available, and Maps actions in the current HTMX/Jinja chat shell.
- Maps and security: Google Maps URLs (`maps.build_store_search_url` /
  `build_store_directions_url`) are the no-key baseline for search and
  directions. Embedded maps are optional and require `MAPS_ENABLE_EMBED=true`
  plus a separate restricted `GOOGLE_MAPS_EMBED_API_KEY`. Responses always send
  `Permissions-Policy: geolocation=(self)`; the map iframe `frame-src` CSP is
  added only when embed is enabled (`build_security_headers`).

Do not persist raw browser coordinates in display history, response cache,
metrics, SQL telemetry, or logs. Coordinate-bearing requests should avoid
response caching unless a rounded-location cache strategy is explicitly reviewed.

## AI And Chat

ADK and Litestar sessions are separate. Litestar server-side session state only
stores the ADK user/session bridge keys; ADK session, event, and optional memory
tables own chat history. Clearing chat deletes the current ADK session/events
and bridge keys, not products, metrics, response cache, or embedding cache.

`ADKRunner` is app-scoped and receives request-scoped `AgentToolsService`
instances for database-backed work. Product RAG is classifier-first and emits a
single grounded final event. It may ask Gemini for structured selection among
retrieved product ids, but Python validates that selection and renders the final
answer from returned Cymbal Coffee rows. It also persists the names of
recommended products in the ADK session state under `last_products` to support
subsequent context-aware availability queries. Non-RAG turns may stream model
deltas through ADK Workflow.

Final chat responses must preserve intent, vector query, product/store result
context, timing phases, response-cache state, and embedding-cache state through
service, controller, template, and frontend rendering.

## Oracle Vector And Embeddings

The only supported embedding shape is `gemini-embedding-2-preview` at 3072 dimensions
stored as `VECTOR(3072, FLOAT32)`. Prefix product fixture text with a
document-purpose instruction and user search text with a query-purpose
instruction before embedding. Pass Python
`list[float]` vectors directly to SQLSpec; do not use `array.array`.

Oracle HNSW `ORGANIZATION INMEMORY NEIGHBOR GRAPH` indexes require non-zero
`vector_memory_size` before migration. The local Oracle startup configures it;
larger environments can use the 4G helper script when memory allows. Use the
explore page and `DBMS_XPLAN.DISPLAY()` to verify the vector access path.

## Testing And Verification

Unit tests should prove application behavior and runtime contracts: service
logic, controller responses, settings parsing, DI resolution, SQL/data
contracts, chat payload shape, vector telemetry, and HTMX partial behavior.
Async tests use AnyIO. Do not grow `src/tests` with checks that only pin repo
layout, source ordering, docs text, project config files, tool scripts, or
third-party import surfaces.

Oracle integration tests assume the repo-managed database lifecycle:

```bash
make start-infra
uv run python manage.py database upgrade --no-prompt
uv run coffee load-fixtures
```

Fixtures may prepare deterministic schema/data inside that configured database,
but they should not own container startup. Keep parallel tests deterministic with
unique keys and targeted cleanup, not broad truncation of shared fixture tables.

Use focused tests while editing. Before claiming branch-level completion, use the
repo's canonical aggregate gates, normally `make lint` and `make test`.

## Operations And CLI

Use `coffee` for app lifecycle commands: `run`, `upgrade`, `load-fixtures`,
`bulk-embed`, `export-fixtures`, `clear-cache`, and `model-info`. Use
`python manage.py` for SQLSpec migrations, assets, infra helpers, and bootstrap.

Public CLI modules should stay mostly declarative: define Click commands and
delegate behavior to private helpers. Async Click commands should use
`@async_inject`, not nested async runners or direct `sqlspec.utils.sync_tools.run_`
calls.

Expected local AI misconfiguration should return clean 503 responses before ADK
starts. Keep placeholder Vertex project checks on the typed
`AIServiceUnconfigured` path.

## Settings Component

Settings are dataclass-based with a cached `Settings.from_env()` factory. Keep
the contract narrow instead of adding placeholder settings or adopting another
settings library.

Current behavior:

- settings construction is quiet and testable;
- shell environment values win over `.env` values;
- settings objects are immutable or effectively immutable with typed parser
  helpers;
- app, database, AI, chat, Vite, and logging settings are explicit and wired;
- future-feature branches are removed until the feature exists;
- optional Maps Embed settings (`MAPS_ENABLE_EMBED`, `GOOGLE_MAPS_EMBED_API_KEY`)
  are wired and read by `build_security_headers`.

Do not keep unused server, agent, cache, or Maps knobs merely as placeholders.
If a setting remains, there should be a live production read or an accepted
feature chapter wiring it in.

## Flow Memory Policy

Archive is no longer durable project memory. Before moving or removing Flow
material, extract the current-state lesson into `.agents/patterns.md`, this
guide, or one of the topic guides. Active indexes, workflows, specs, and guides
must not require archive links to understand the project.
