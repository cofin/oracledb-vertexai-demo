# For the curious

A handful of short notes for readers who want to know how the demo
*actually* fits together — none are required reading, but each one is the
answer to a question that comes up when you start measuring.

## Why SQLSpec (`0.69.0`)

The data layer is [SQLSpec](https://sqlspec.dev) (`>=0.69.0`) — a SQL-first data
access layer that keeps the demo close to real SQL while still handing back
typed Python objects. It is deliberately *not* an ORM: multi-join and analytical
queries live in named `.sql` files, simple CRUD uses `sql.insert` /
`sql.update` / `sql.delete` builders, and rows come back as immutable
`msgspec.Struct` instances.

Several capabilities make it the right fit once Oracle 26ai's `VECTOR` type,
`CTXSYS.CONTEXT`, and the `/explore` page are on the table:

- **Statement-aware query handling.** SQLSpec normalizes named SQL and
  parameter binding before it reaches the driver. That is how `:bind`
  parameters, dialect quirks, and rewrites like `EXPLAIN` work uniformly —
  instead of requiring per-driver string surgery inside service code.
- **Adapter-neutral service hierarchy (`OracleLoaderService`).** Domain services
  in `src/app/domain/**/services/` subclass `OracleLoaderService`
  (`src/app/lib/service.py`), which attaches a cached `SQLFileLoader`
  (`default_sql_loader()`) over `src/app/db/sql/*.sql`. Service methods call
  `self.get_sql("vector-search-products")` (delegating to `self._loader.get_sql(...)`)
  rather than embedding multi-line SQL strings in Python modules.
- **`EXPLAIN PLAN` first-class.** The same statement that runs the query
  can produce its plan — which is what `/explore` renders for every
  hybrid or vector search, so you can verify the HNSW and Domain Index paths
  without leaving the app.
- **Native vector binding.** A Python `list[float]` is bound straight
  through to Oracle's `VECTOR(3072, FLOAT32)` parameter. No
  `array.array("f", ...)` wrapping, no manual struct packing, and no
  driver-specific shim leaking into service code.
- **Typed result mapping.** `schema_type=ProductMatch` produces `msgspec`
  structs row-by-row from the cursor, so handlers and tools work with
  typed models instead of `dict[str, Any]`.
- **Inline LOB reads by default (`fetch_lobs=False`).** SQLSpec `0.69.0`
  defaults `fetch_lobs` to `False`, returning LOB columns under 1 GB directly as
  inline `str` / `bytes` values across both `select` and `select_stream` without
  extra locator round-trips. `DatabaseSettings.create_config()` configures
  `driver_features={"enable_session_tracing": True}` on the primary pool.
- **Wire-level `sqlcommenter` and OpenTelemetry.** `DatabaseSettings` enables
  `enable_sqlcommenter=True`, `sqlcommenter_enable_context=True`, and
  `sqlcommenter_enable_traceparent=True` alongside `ObservabilityConfig`
  (`TelemetryConfig` and `LoggingConfig(include_trace_context=True, include_sql_hash=True)`),
  appending W3C trace context comments to executed Oracle statements.
- **Native mTLS wallet handling (`wallet_zip`).** Autonomous Database pool
  configurations pass `wallet_zip` directly to `OracleAsyncConfig`, while CLI
  and APEX helpers reuse `extract_oracle_wallet_zip` and `parse_tnsnames_ora`
  from `sqlspec.adapters.oracledb`.

Together that is why `ProductService.search_by_vector` fits on one screen
and reads like a function call: SQLSpec absorbs the binding,
plan-generation, wallet extraction, and result-shaping that an Oracle-aware
service would otherwise have to spell out. See <https://sqlspec.dev> for the
full feature set, including the adapter list, migration runner, and Litestar
plugin used by this app.

### Isolated background queue pool (`queue_db_session`)

`DatabaseSettings.get_queue_config()` (`src/app/lib/settings/_database.py`)
constructs a dedicated `OracleAsyncConfig` (`min=1, max=4`,
`session_key="queue_db_session"`) for `QueuePlugin` and `SQLSpecQueueBackend`.
Keeping the queue pool separate from `DatabaseSettings.get_config()` isolates
`OracledbAsyncQueueStore`'s in-place `driver_features` and `extension_config`
mutations from the primary application pool (`app.config.db`).

### Schema annotations in migrations

Oracle AI Database 26ai schema annotations are authored directly in the
baseline migration DDL. SQLSpec loads the migration as named SQL and executes
the migration body as a script, so new Oracle DDL such as `ANNOTATIONS(...)`
can remain inline with the `CREATE TABLE`, column definition, and supported
`CREATE INDEX` statements.

The app does not read annotations at runtime; they are demo metadata for
database inspection and tooling. After `coffee upgrade`, inspect them with
`USER_ANNOTATIONS_USAGE` alongside the existing `COMMENT ON` metadata.

## Runtime architecture: schemas, DI, and code hygiene

- **GC-exempt `msgspec.Struct` schemas (`src/app/lib/schema.py`).**
  `FrozenBaseStruct` and `CamelizedFrozenStruct` inherit from
  `msgspec.Struct(..., frozen=True, gc=False, omit_defaults=True)`. Omitting
  CPython's cyclic garbage-collector header reduces per-instance allocation and
  GC pause overhead across database row mapping, cached payloads, and SSE frames.
- **Dishka container composition (`src/app/ioc/__init__.py`).**
  `create_container()` assembles `ConfigProvider`, `DBProvider`, `AIProvider`,
  and `DomainServiceProvider` into an `AsyncContainer` shared by Litestar
  request scopes (via `litestar-autowire`) and `coffee` CLI commands
  (`@async_inject`). Provider modules under `src/app/ioc/` omit
  `from __future__ import annotations` so Dishka resolves dependency type
  annotations directly at runtime.
- **Repository-wide AST hygiene gate (`tools/ci/check_code_hygiene.py`).**
  `make lint` runs token and AST checks across `src/app/`, `tools/`, and
  `manage.py` to enforce module docstrings, top-level imports, slotted
  dataclasses, public-before-private symbol ordering, Dishka annotation rules,
  and zero non-directive inline `#` comments.

## The HNSW neighbor graph in the SGA

The product index is `ORGANIZATION INMEMORY NEIGHBOR GRAPH`. That name is
load-bearing: the index lives in Oracle's vector memory pool inside the
SGA as a small-world graph of vectors and their nearest neighbors. A query
walks down through the graph from a sparse top layer toward the densest
bottom layer, refining the candidate set at each step.

```{mermaid}
flowchart TD
    Q[query vector] -.-> L0
    subgraph L2[layer 2 · sparse]
        N0((·)) --- N1((·)) --- N2((·))
    end
    subgraph L1[layer 1]
        M0((·)) --- M1((·)) --- M2((·)) --- M3((·))
    end
    subgraph L0[layer 0 · dense]
        P0((·)) --- P1((·)) --- P2((·)) --- P3((·)) --- P4((·)) --- P5((·))
    end
    L2 -.-> L1
    L1 -.-> L0
    L0 --> R[top-k]
```

Graph construction parameters set the shape:

- **`NEIGHBORS 40`** — out-degree per node. Higher values build a denser
  graph, slower to construct, faster to search.
- **`EFCONSTRUCTION 500`** — candidate list size during build. Higher
  values mean better-quality neighbor selection (and a slower build).

`WITH TARGET ACCURACY 95` lets Oracle pick the search-time `ef` that meets
the recall target dynamically.

The pool itself is configured by `vector_memory_size`. 512 MB is plenty for
the demo's 130 committed `product` vectors and 25 committed `chat_route`
exemplar vectors indexed in HNSW neighbor graphs; budget roughly
`rows × dimensions × 4 bytes × 1.4 (HNSW overhead) × 2 (safety)` for larger
catalogs.

## Single-Query Hybrid RRF and Oracle Text sanitization

Previously, every chat turn executed a separate LLM intent-classification call
before running product or store retrieval. Today, `HybridRouteResolver.resolve_turn`
fuses BM25-style lexical ranking (`CONTAINS`/`SCORE`) and HNSW vector distance
(`FETCH APPROX`) across `chat_route` and `product` alongside lexical `store`
matching in a single Oracle 26ai SQL round trip (`hybrid-search-turn`, plus
`hybrid-term-hits` when quoted or capitalized product terms appear), cutting
routing + retrieval latency down to ~15–25 ms inside Oracle. Deterministic
`STORE_LOCATION`, `PRODUCT_AVAILABILITY`, and `ORDER_STATUS` turns render
directly from Oracle rows, deterministic `PRODUCT_RAG` turns use a single
structured `Gemini 3.8 Flash` selection call (or an off-menu refusal guard),
and only `GENERAL_CONVERSATION` or low-confidence/ambiguous turns enter the
multi-step `AgentRuntime` tool loop.

Before binding `:text_query` into `CONTAINS(..., :text_query, 1)`,
`build_oracle_text_query` and `build_oracle_proximity_query`
(`src/app/lib/text_search.py`) extract deduplicated alphanumeric tokens via
`extract_search_tokens`, strip Oracle Text reserved operators (`ACCUM`, `NEAR`,
`FUZZY`, `WITHIN`, `ABOUT`, etc.) and conversational stopwords, and wrap each
surviving token in `{...}` braces (`{token1} ACCUM {token2}`) so raw user
punctuation never triggers `DRG-50901` parser errors.

## What the live dashboard measures

The chat UI surfaces per-message badges; `/explore` shows the same data
across recent searches. The fields map back to specific call sites:

| Badge / metric | What it measures | Source |
| --- | --- | --- |
| `embedding_ms` | Wall time for `VertexAIService.get_text_embedding()`, including a cache check. | `_embedding.py` |
| `oracle_ms` | Round-trip for `hybrid-search-turn` (plus optional `hybrid-term-hits`) on chat turns or `hybrid-search-products` / `vector-search-products` on `/explore`. | `_router.py` / `_vector.py` |
| `ai_ms` | Time spent in `AgentRuntime` generation or structured `PRODUCT_RAG` selection (`0 ms` on deterministic store, availability, and order routes). | `_agent.py` / `_grounded.py` |
| `results_count` | Matched product, store, or inventory rows returned for the turn (persisted as `search_metric.result_count`). | `_telemetry.py` / `_grounded.py` |
| `from_cache` | Response cache hit (model + persona + normalized query). | `CacheService` |
| `embedding_cache_hit` | Hit on the Oracle-backed `embedding_cache` table. | `VertexAIService` |
| `intent_detected` | Route resolved by `HybridRouteResolver.resolve_turn` (`PRODUCT_RAG`, `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, `ORDER_STATUS`, or `GENERAL_CONVERSATION`). | `_router.py` |
| `sql_phases` | Per-phase timing collected during retrieval, used for the colored badges in the chat bubble. | `_telemetry.py` |

If `oracle_ms` spikes:

1. Check the EXPLAIN PLAN at `/explore` still mentions `VECTOR`. A full
   table scan means the index is unavailable.
2. Verify `vector_memory_size` is non-zero — `SELECT name, bytes FROM
   v$sgainfo WHERE name IN ('Vector Memory Area', 'Vector Memory')`.
3. Refresh table/index statistics if the catalog has just grown.

If `embedding_ms` spikes, the query missed `embedding_cache` and called Vertex AI
`embed_content` live (storing the new vector automatically via `MERGE INTO embedding_cache`).
Use `coffee clear-cache` only when you want to purge `response_cache` and
`embedding_cache` and force fresh Vertex AI calls.
