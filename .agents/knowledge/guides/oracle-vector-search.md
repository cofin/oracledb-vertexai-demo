# Oracle Vector Search Guide

Current guide for the Cymbal Coffee Oracle 26ai vector stack.

## Current Contract

The demo uses one embedding model and one vector shape everywhere:

- Model: `gemini-embedding-001`
- Dimensions: `3072`
- Storage: `VECTOR(3072, FLOAT32)`
- Query task type: `RETRIEVAL_QUERY`
- Product/document task type: `RETRIEVAL_DOCUMENT`
- Similarity formula: `1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE)`

Do not reintroduce 768-dimensional examples. The committed product fixtures,
`embedding_cache`, migration DDL, and Vertex settings all assume 3072 dimensions.

## Schema

`src/app/db/migrations/0001_cymball_coffee_products.sql` owns the demo schema.
The vector-bearing tables are:

```sql
CREATE TABLE product (
    ...
    embedding VECTOR(3072, FLOAT32),
    ...
) INMEMORY PRIORITY HIGH;

CREATE TABLE embedding_cache (
    ...
    embedding VECTOR(3072, FLOAT32) NOT NULL,
    model VARCHAR2(100) NOT NULL,
    ...
) INMEMORY PRIORITY HIGH;
```

Both tables have HNSW INMEMORY indexes:

```sql
CREATE VECTOR INDEX product_embedding_idx ON product (embedding)
ORGANIZATION INMEMORY NEIGHBOR GRAPH
DISTANCE COSINE
WITH TARGET ACCURACY 95
PARAMETERS (TYPE HNSW, NEIGHBORS 40, EFCONSTRUCTION 500);
```

The embedding cache index uses the same recipe.

## Vector Memory

Oracle must have a non-zero `vector_memory_size` before `ORGANIZATION INMEMORY
NEIGHBOR GRAPH` indexes can be created. Without it, migrations fail with
`ORA-51962`.

Local container startup handles this in `tools/oracle/on_init/00_configure_vector_memory.sql`:

```sql
ALTER SYSTEM SET vector_memory_size = 512M SCOPE = SPFILE;
```

That value is intentionally small because Oracle Free Edition has a constrained
SGA. For larger non-Free environments, `tools/oracle/configure_vector_memory.sql`
uses a 4G target:

```sql
ALTER SYSTEM SET vector_memory_size = 4G SCOPE = SPFILE;
```

After restart, verify the pool:

```sql
SELECT name, bytes FROM v$sgainfo WHERE name = 'Vector Memory';
```

If HNSW builds exhaust the pool, use this estimate:

```text
rows * dimensions * 4 bytes * 1.4 HNSW overhead * 2 safety factor
```

## Query Shape

The product vector query lives in `src/app/db/sql/products.sql`:

```sql
-- name: vector-search-products
SELECT id,
       name,
       description,
       price,
       1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) AS similarity_score
FROM product
WHERE 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) > :threshold
ORDER BY similarity_score DESC
FETCH FIRST :limit ROWS ONLY;
```

The Python service passes a normal `list[float]`:

```python
return await self.driver.select(
    db_manager.get_sql("vector-search-products"),
    query_vector=query_embedding,
    threshold=similarity_threshold,
    limit=limit,
    schema_type=ProductMatch,
)
```

SQLSpec and the Oracle adapter handle vector binding. Do not add manual
`array.array("f", ...)` conversion.

## Embedding Generation

`VertexAIService.get_text_embedding()` wraps the Google GenAI async client:

```python
response = await self.client.aio.models.embed_content(
    model=self.embedding_model,
    contents=text,
    config=EmbedContentConfig(
        task_type=task_type,
        output_dimensionality=self.embedding_dimensions,
    ),
)
```

Use task types deliberately:

- Product fixture embeddings: `RETRIEVAL_DOCUMENT`
- User search queries: `RETRIEVAL_QUERY`
- One-off semantic cache lookups: use the same task type as the text role

Embeddings are cached by text hash and model in the Oracle `embedding_cache`
table. The cache table stores vectors too, so the same vector-memory rules apply.

## EXPLAIN PLAN

The explore page shows the plan for the exact vector search SQL. The service
runs:

```sql
EXPLAIN PLAN FOR
SELECT ...

SELECT plan_table_output FROM TABLE(DBMS_XPLAN.DISPLAY());
```

The UI looks for plan lines mentioning `VECTOR` as the quick signal that Oracle
is using the vector access path. If the plan degrades to full table scan, check:

- `vector_memory_size` is non-zero.
- Migrations created `product_embedding_idx`.
- The query matches the indexed distance metric (`COSINE`).
- Table/index statistics are current after large fixture changes.

## In-Memory Extension Flags

The app also uses SQLSpec extension tables for ADK and Litestar sessions. Their
Oracle INMEMORY settings are separate from vector indexes:

| Environment variable | Target |
| --- | --- |
| `ORACLE_ADK_IN_MEMORY` | Defaults true; ADK `adk_sessions`, `adk_events`, and optional memory table |
| `ORACLE_LITESTAR_SESSION_IN_MEMORY` | Defaults true; Litestar server-side `app_session` table |
| `ADK_ENABLE_MEMORY` | Includes SQLSpec ADK memory migration/table |

Enable these only when the target Oracle edition and memory budget support them.
They do not replace `vector_memory_size`, which is required for HNSW INMEMORY
vector indexes.

## Maintainer Regeneration

The contributor path uses committed fixture files. Regenerating embeddings is a
maintainer operation:

1. Start Oracle with `make start-infra`.
2. Apply migrations with `uv run python manage.py database upgrade --no-prompt`.
3. Load or refresh product rows.
4. Generate product embeddings with `uv run coffee bulk-embed`.
5. Export fixtures with 3072-dimensional vectors via `uv run coffee export-fixtures`.
6. Reload with `uv run coffee load-fixtures` and run `/explore` plus EXPLAIN PLAN.

`bulk-embed` and `export-fixtures` are intentionally retained on the `coffee`
app CLI. They are app lifecycle commands, not disposable development scripts.

## Troubleshooting

`ORA-51962` during migration:
Check `vector_memory_size` and restart the database after changing it.

Slow vector search:
Use `/explore`, open the EXPLAIN PLAN panel, and verify the vector index appears.

Dimension mismatch:
Search for stale `768` references in fixtures, SQL, and docs. Runtime settings
must use `EMBEDDING_DIMENSIONS = 3072`.

Unexpected empty results:
Lower the threshold temporarily, then confirm product rows have non-null
embeddings and the query embedding call returned values.
