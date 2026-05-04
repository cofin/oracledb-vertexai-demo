# Vectors in Oracle

Cymbal Coffee stores product descriptions as 3072-dimension vectors next to
their text columns. A `VECTOR_DISTANCE(..., COSINE)` query, served by an
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
| Embedding model | Vertex AI `gemini-embedding-001` |
| Dimensions | `3072` |
| Storage | `VECTOR(3072, FLOAT32)` |
| Distance metric | `COSINE` |
| Index type | HNSW, `ORGANIZATION INMEMORY NEIGHBOR GRAPH` |
| Query task type | `RETRIEVAL_QUERY` |
| Document task type | `RETRIEVAL_DOCUMENT` |

The product table and the embedding cache both use the same shape.

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
*before* the index DDL runs. Without it migrations fail with `ORA-51962`.

```sql
ALTER SYSTEM SET vector_memory_size = 512M SCOPE = SPFILE;
```

`512M` is intentional for Oracle Free Edition's constrained SGA. The committed
demo fixture has 122 product vectors, so this is generous headroom for the
catalog plus query embeddings saved in `embedding_cache`. For larger Oracle
editions, `tools/oracle/configure_vector_memory.sql` uses a 4G target.

Verify the pool with:

```sql
SELECT name, bytes FROM v$sgainfo WHERE name = 'Vector Memory';
```

## The query shape

The vector search itself is a named SQL file the products service loads by
key — every query in the app lives under `src/app/db/sql/`.

```{literalinclude} ../../src/app/db/sql/products.sql
:language: sql
:start-after: docs:start-vector-search-sql
:end-before: docs:end-vector-search-sql
:caption: src/app/db/sql/products.sql
```

`1 - VECTOR_DISTANCE(..., COSINE)` flips distance into a similarity score
where higher is better. `:threshold` filters out rows that aren't close
enough; `:limit` caps the top-k.

`ProductService.search_by_vector` is the SQLSpec async service method that
runs the query above and maps each row to a typed `ProductMatch` — Python
hands Oracle a plain `list[float]`, no manual packing required.

```{literalinclude} ../../src/app/domain/products/services/services.py
:language: python
:start-after: docs:start-search-by-vector
:end-before: docs:end-search-by-vector
:caption: src/app/domain/products/services/services.py
```

SQLSpec and the Oracle adapter handle the vector binding. Don't reach for
`array.array("f", ...)`.

## Embedding cache

User queries are repeated often. The same text + model hashes to the same
row in `embedding_cache`, which stores the vector itself in a parallel
`VECTOR(3072, FLOAT32)` column. Cache hits skip the Vertex AI call entirely
and feed straight into the HNSW search.

## Understanding performance

The `/explore` page surfaces three timings per query:

<details>
<summary>Click to expand Explore Page Screenshot</summary>

```{image} ../screenshots/explore_page.png
:alt: Vector Lab Explore Page
:align: center
```

</details>

- **embedding_ms** — time spent generating (or hitting the cache for) the
  query vector;
- **oracle_ms** — round-trip time for the HNSW search;
- **similarity score** — the top returned row's score.

If `oracle_ms` spikes, check that `vector_memory_size` is non-zero, that
`product_embedding_idx` exists, and that the query metric still matches
`COSINE`.

## Where this is used

- **The walkthrough** stitches embedding + HNSW search into one chat
  message: see [the walkthrough](../tour.md).
- **RAG** uses the `ProductMatch` rows returned here as grounding context:
  see [RAG](rag.md).
- **Chat routing** decides *whether* to fire this search at all: see
  [Chat routing and Google ADK](agent-flow.md).
