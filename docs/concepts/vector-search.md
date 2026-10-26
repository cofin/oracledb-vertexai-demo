# Vectors in Oracle

Cymbal Coffee stores product names and descriptions (as well as `chat_route`
routing exemplars) as 3072-dimension vectors next to their text columns. A `VECTOR_DISTANCE(..., COSINE)` query, served by an
HNSW index, returns the closest products straight from the same database
that holds the rest of the catalog.

```{mermaid}
flowchart LR
    Q[query embedding<br/>3072 floats] --> H[(HNSW NEIGHBOR GRAPH<br/>in SGA)]
    H --> S["VECTOR_DISTANCE<br/>(embedding, :q, COSINE)"]
    S --> R[top-k product rows]
```

## At a glance

| Setting | Value |
| --- | --- |
| Embedding model | Vertex AI `gemini-embedding-2` |
| Dimensions | `3072` |
| Storage | `VECTOR(3072, FLOAT32)` |
| Distance metric | `COSINE` |
| Index type | HNSW, `ORGANIZATION INMEMORY NEIGHBOR GRAPH` |
| Query embedding input | Query-purpose instruction + user text |
| Document embedding input | Document-purpose instruction + `"{name}: {description}"` (`product`) or `"{route_label} \| {title}: {exemplar_text} ({keywords})"` (`chat_route`) |

The `product`, `chat_route`, and `embedding_cache` tables all store
`VECTOR(3072, FLOAT32)` columns, with HNSW `INMEMORY NEIGHBOR GRAPH` indexes on
`product` (`product_embedding_idx`) and `chat_route`
(`chat_route_embedding_idx`).

## Schema annotations

The baseline DDL also annotates the vector columns with their application
contract: model, dimension count, embedding purpose, and distance metric. These are
Oracle 26ai schema annotations, so they live with the database metadata and can
be queried from `USER_ANNOTATIONS_USAGE` after `coffee upgrade`.

```{literalinclude} ../../src/app/db/migrations/0001_cymball_coffee_products.sql
:language: sql
:start-after: docs:start-schema-annotations
:end-before: docs:end-schema-annotations
:caption: src/app/db/migrations/0001_cymball_coffee_products.sql
```

## The HNSW index

The index is created in the baseline SQLSpec migration alongside the
`product` table — running `coffee upgrade` applies it before any fixtures
load.

```{literalinclude} ../../src/app/db/migrations/0001_cymball_coffee_products.sql
:language: sql
:start-after: docs:start-hnsw-index
:end-before: docs:end-hnsw-index
:caption: src/app/db/migrations/0001_cymball_coffee_products.sql
```

`NEIGHBORS=40` and `EFCONSTRUCTION=500` are sensible defaults for a catalog
on the order of a few thousand rows. `WITH TARGET ACCURACY 95` lets Oracle
pick the search-time `ef` that meets the recall target.

## Vector memory

HNSW INMEMORY indexes need a non-zero `vector_memory_size` allocation
*before* the index DDL runs. Without it migrations fail with `ORA-51962`. The
default managed local container (`adb-free:latest-26ai`, `cymbal-adb-free`,
service `myatp_low`, TLS wallet `.envs/tns`) and cloud Autonomous AI Database
manage vector memory automatically; self-managed Oracle AI Database 26ai Free
(`gvenzl/oracle-free`) configures the pool during initialization
(`tools/oracle/on_init/00_configure_vector_memory.sql`):

```sql
ALTER SYSTEM SET vector_memory_size = 512M SCOPE = SPFILE;
```

`512M` is sized for Oracle Free Edition's constrained SGA. The committed demo
fixtures contain 130 product vectors (`product_embedding_idx`) plus the
`chat_route` routing exemplars (`chat_route_embedding_idx`), leaving ample
headroom in the HNSW pool (`embedding_cache` uses B-tree key lookups on
`(text_hash, model)` rather than an HNSW index). For larger self-managed Oracle
editions, raise `vector_memory_size` on the SPFILE.

Verify the pool with:

```sql
SELECT name, bytes FROM v$sgainfo WHERE name IN ('Vector Memory Area', 'Vector Memory');
```

## The query shape

Every static query in the app lives under `src/app/db/sql/`. Domain services
inherit from `OracleLoaderService` (`src/app/lib/service.py`) and load named
SQL via `self.get_sql("<name>")` (`default_sql_loader()`), without importing
`app.config`.

```{literalinclude} ../../src/app/db/sql/products.sql
:language: sql
:start-after: docs:start-vector-search-sql
:end-before: docs:end-vector-search-sql
:caption: src/app/db/sql/products.sql
```

`1 - VECTOR_DISTANCE(..., COSINE)` flips distance into a similarity score
where higher is better. `:threshold` filters out rows that aren't close
enough; `:limit` caps the top-k.

`ProductService.search_by_vector` (`src/app/domain/products/services/_products.py`)
runs the query above and maps each row to an immutable `ProductMatch`
(`FrozenBaseStruct` in `src/app/lib/schema.py`) — Python hands Oracle a plain
`list[float]`, no manual packing required.

```{literalinclude} ../../src/app/domain/products/services/_products.py
:language: python
:pyobject: ProductService.search_by_vector
:caption: src/app/domain/products/services/_products.py
```

SQLSpec `0.69.0` (`DatabaseSettings.create_config()` in
`src/app/lib/settings/_database.py`) handles native `list[float]` vector
binding, `wallet_zip` extraction, `driver_features={"enable_session_tracing": True}`,
wire-level `sqlcommenter` (`enable_sqlcommenter=True`), default
`fetch_lobs=False` (inline `str`/`bytes` for LOBs under 1 GB), and an isolated
`DatabaseSettings.get_queue_config()` pool (`session_key="queue_db_session"`).
Do not reach for `array.array("f", ...)`.

## Embedding cache

User queries are repeated often. `CacheService`
(`src/app/domain/system/services/_cache.py`) hashes the same text + model to
the same row in `embedding_cache`, which stores the vector itself in a
`VECTOR(3072, FLOAT32)` column. Cache hits skip the Vertex AI call entirely
and feed straight into the HNSW search.

## Understanding performance

The `/explore` page (`http://localhost:8000/explore`, rendered by
`PageController.explore_page` in `src/app/domain/web/controllers/_pages.py` and
powered by `VectorController` in `src/app/domain/products/controllers/_vector.py`
plus `OracleVectorSearchService` in
`src/app/domain/products/services/_vector.py`) surfaces per-query retrieval
telemetry alongside live `DBMS_XPLAN` execution plans:

<details>
<summary>Click to expand Explore Page Screenshot</summary>

```{image} ../screenshots/explore_page.png
:alt: Vector Lab Explore Page
:align: center
```

</details>

- **`embedding_ms` / `embedding_time_ms`** — time spent generating (or hitting
  `embedding_cache` for) the 3072-float query vector;
- **`oracle_ms` / `oracle_time_ms`** — round-trip time for the Oracle 26ai
  Hybrid RRF query (`hybrid-search-products`, combining `PRODUCT_HYBRID_CTX_IDX`
  and HNSW `PRODUCT_EMBEDDING_IDX`, with pure HNSW fallback);
- **RRF, similarity, and lexical scores** — each result card displays its fused
  RRF score (`1/(60 + r_lex) + 1/(60 + r_vec)`), HNSW cosine similarity
  percentage and vector rank, and Oracle Text `SCORE` and lexical rank (while
  `search_metric` records the top row's `similarity_score`).

If `oracle_ms` spikes, check that `vector_memory_size` is non-zero, that
`product_embedding_idx` and `product_hybrid_ctx_idx` are `VALID`, and that the
query metric still matches `COSINE`.

## Where this is used

- **The walkthrough** stitches embedding + HNSW search into one chat
  message: see [the walkthrough](../tour.md).
- **RAG** uses the `ProductMatch` rows returned here as grounding context:
  see [RAG](rag.md).
- **Hybrid routing** fuses route exemplars and product HNSW search into one
  round trip: see [Hybrid RRF Routing and Native AI Runtime](agent-flow.md).
