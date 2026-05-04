# For the curious

A handful of short notes for readers who want to know how the demo
*actually* fits together — none are required reading, but each one is the
answer to a question that comes up when you start measuring.

## Why SQLSpec

The data layer is [SQLSpec](https://sqlspec.dev) — a SQL-first data access
layer that keeps the demo close to real SQL while still handing back typed
Python objects. It is deliberately *not* an ORM: queries live in named
`.sql` files, service code asks for them by name, and rows come back as
msgspec structs.

Five things make it the right fit once Oracle 26ai's `VECTOR` type and the
`/explore` page are on the table:

- **AST-based statement handling.** SQLSpec parses every statement into an
  AST, validates it, and normalizes parameter binding *before* it reaches
  the driver. That's how `:bind` parameters, dialect quirks, and rewrites
  like `EXPLAIN` work uniformly — instead of requiring per-driver string
  surgery inside service code.
- **Adapter-neutral service shape.** The demo only uses Oracle, but SQLSpec
  keeps the named-SQL service and Litestar plugin shape separate from the
  driver-specific connection details.
- **`EXPLAIN PLAN` first-class.** The same statement that runs the query
  can produce its plan — which is what `/explore` renders for every
  vector search, so you can see the HNSW path without leaving the app.
- **Native vector binding.** A Python `list[float]` is bound straight
  through to Oracle's `VECTOR(3072, FLOAT32)` parameter. No
  `array.array("f", ...)` wrapping, no manual struct packing, no
  driver-specific shim leaking into service code.
- **Typed result mapping.** `schema_type=ProductMatch` produces msgspec
  structs row-by-row from the cursor, so handlers and tools work with
  real types instead of `dict[str, Any]`. msgspec, Pydantic, and plain
  dataclasses all work the same way.

Named SQL files round it out: every query lives in `src/app/db/sql/*.sql`
under a stable name (e.g. `vector-search-products`). Service code asks
for `db_manager.get_sql("vector-search-products")` rather than embedding
multi-line strings — the SQL stays inspectable, version-controlled, and
EXPLAIN-friendly.

Together that's why `ProductService.search_by_vector` fits on one screen
and reads like a function call: SQLSpec absorbs the binding,
plan-generation, and result-shaping that an Oracle-aware service would
otherwise have to spell out. See <https://sqlspec.dev> for the full
feature set, including the adapter list, migration runner, and Litestar
plugin used by this app.

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

Two construction parameters set the shape:

- **`NEIGHBORS=40`** — out-degree per node. Higher values build a denser
  graph, slower to construct, faster to search.
- **`EFCONSTRUCTION=500`** — candidate list size during build. Higher
  values mean better-quality neighbor selection (and a slower build).

`WITH TARGET ACCURACY 95` lets Oracle pick the search-time `ef` that meets
the recall target dynamically.

The pool itself is configured by `vector_memory_size`. 512 MB is plenty for
the demo's 122 committed product vectors plus query embeddings saved in
`embedding_cache`; budget roughly
`rows × dimensions × 4 bytes × 1.4 (HNSW overhead) × 2 (safety)` for larger
catalogs.

## Deterministic vs ADK latency

Product, store, availability, and unsupported order turns are routed before the
ADK workflow is built, so they avoid speculative LLM deltas entirely. The ADK
workflow still matters for `GENERAL_CONVERSATION`: inside that fallback path,
the classifier and the LLM share `START` with `max_concurrency=2`. The timings
below are illustrative; the important shape is overlap, not the exact numbers.

```{mermaid}
gantt
    dateFormat  X
    axisFormat  %s ms
    title Sequential vs parallel
    section Sequential
    Classifier   :a1, 0, 180
    LLM + tool   :a2, 180, 1100
    section Parallel
    Classifier   :b1, 0, 180
    LLM + tool   :b2, 0, 1100
```

The "LLM + tool" bar dominates because it covers the fallback agent's reasoning,
any closure-bound tool call, and final-event packaging. The classifier's
latency overlaps with that fallback path instead of adding to it.

The deterministic `PRODUCT_RAG` route is stricter: it classifies first, runs the
vector search directly, and formats the final answer from product rows.

## What the live dashboard measures

The chat UI surfaces per-message badges; `/explore` shows the same data
across recent searches. The fields map back to specific call sites:

| Badge / metric | What it measures | Source |
| --- | --- | --- |
| `embedding_ms` | Wall time for `VertexAIService.get_text_embedding()`, including a cache check. | `services.py` |
| `oracle_ms` | Round-trip for the named SQL `vector-search-products` against the HNSW index. | `services.py` |
| `tool_ms` | Total time inside `search_products_by_vector` — embedding + Oracle + result shaping. | `adk.py` |
| `results_count` | Rows returned by HNSW after threshold + `FETCH FIRST :limit`. | `products.sql` |
| `from_cache` | Response cache hit (model + persona + normalized query). | `CacheService` |
| `embedding_cache_hit` | Hit on the Oracle-backed `embedding_cache` table. | `VertexAIService` |
| `intent_detected` | Output of the Flash-Lite classifier, with product lookup fallback normalized to `PRODUCT_RAG`. | `FlashLiteIntentClassifier` / `_adk_telemetry.py` |
| `sql_phases` | Per-phase timing collected during retrieval, used for the colored badges in the chat bubble. | `_adk_telemetry.py` |

If `oracle_ms` spikes:

1. Check the EXPLAIN PLAN at `/explore` still mentions `VECTOR`. A full
   table scan means the index is unavailable.
2. Verify `vector_memory_size` is non-zero — `SELECT name, bytes FROM
   v$sgainfo WHERE name = 'Vector Memory'`.
3. Refresh table/index statistics if the catalog has just grown.

If `embedding_ms` spikes, the embedding cache is missing or full. `coffee
clear-cache` rebuilds it on the next request.
