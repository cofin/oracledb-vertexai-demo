# Oracle Database & SQLSpec Guide

This guide details the Oracle Database 26ai integration, SQLSpec usage, vector search, HNSW index management, and local database lifecycle patterns.

## Database Stack & Types

- **Database:** Oracle Database 26ai (Vector Search, RAG, Graph RAG)
- **Data Access:** SQLSpec (using `python-oracledb` and `mypyc` optimizations)
- **Supported Types:** The baseline schema leverages modern Oracle types:
  - `BOOLEAN`
  - `JSON`
  - `VECTOR(3072, FLOAT32)` (used for product vectors and embedding cache)

## SQLSpec Patterns

Domain services subclass `SQLSpecAsyncService` (from `app.lib.service`) or `OracleAsyncService`.

### 1. Named SQL Files (Mandatory)
All static SQL queries must live in `src/app/db/sql/*.sql` as named queries. Domain services call `db_manager.get_sql("query-name")`. Inline static SQL strings in Python code are rejected.

### 2. Schema Type Mapping
Always pass `schema_type=` when executing reads where a typed msgspec Struct schema exists:
```python
rows = await self.driver.select(
    db_manager.get_sql("list-products"),
    schema_type=Product,
)
```

### 3. Dynamic Writes
Use SQLSpec builders (`sql.update`, `sql.insert_into`) only for dynamic writes to avoid complex string assembly:
```python
result = await self.driver.execute(
    sql.update("product").set(embedding=embedding).where_eq("id", product_id)
)
```

### 4. Vector Binding
SQLSpec handles binding Python `list[float]` directly to Oracle vector columns. **Do not** wrap vectors in `array.array("f", ...)` in Python.

### 5. Bind Parameters
Always use named bind parameters in the format `:name` in SQL files. Never interpolate user input directly into SQL strings.

## Schema Annotations

Oracle 26ai supports database annotations.
- Keep `COMMENT ON` statements for backwards compatibility.
- Use 26ai `ANNOTATIONS(...)` on tables, columns, and indexes.
- Place annotations directly in the baseline DDL (e.g., `0001_cymball_coffee_products.sql`). Do not create separate `ALTER ... ANNOTATIONS(...)` migration steps.
- Annotations are validated using the `USER_ANNOTATIONS_USAGE` dictionary view.

## Vector Search & HNSW Indexing

### 1. Vector Configuration
The application standardized on:
- Model: `gemini-embedding-2`
- Dimensions: `3072`
- Storage: `VECTOR(3072, FLOAT32)`
- Similarity Formula: `1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE)`

### 2. HNSW Index DDL
HNSW indexes use Oracle's `ORGANIZATION INMEMORY NEIGHBOR GRAPH`:
```sql
CREATE VECTOR INDEX product_embedding_idx ON product (embedding)
ORGANIZATION INMEMORY NEIGHBOR GRAPH
DISTANCE COSINE
WITH TARGET ACCURACY 95
PARAMETERS (TYPE HNSW, NEIGHBORS 40, EFCONSTRUCTION 500);
```

### 3. Vector Memory Sizing
Oracle requires a non-zero `vector_memory_size` before creating INMEMORY neighbor graph indexes, otherwise migrations fail with `ORA-51962`.

- **Local Development / Oracle Free:** Constrained SGA/PGA limits require a small size:
  ```sql
  ALTER SYSTEM SET vector_memory_size = 512M SCOPE = SPFILE;
  ```
- **Larger Environments:** Use a 4G target:
  ```sql
  ALTER SYSTEM SET vector_memory_size = 4G SCOPE = SPFILE;
  ```
- **Verification:**
  ```sql
  SELECT name, bytes FROM v$sgainfo WHERE name = 'Vector Memory Area';
  ```
- **HNSW Sizing Formula (Rough Estimate):**
  `1.3 * rows * dimensions * element_size`
  Element sizes:
  - `FLOAT64`: 8 bytes
  - `FLOAT32`: 4 bytes
  - `INT8`: 1 byte
  - `BINARY`: 1/8 byte (1 bit)
  Use `DBMS_VECTOR.INDEX_VECTOR_MEMORY_ADVISOR` for exact sizing.

### 4. EXPLAIN PLAN Verification
The `/explore` page allows executing a query and retrieving its execution plan:
```sql
EXPLAIN PLAN FOR SELECT ...;
SELECT plan_table_output FROM TABLE(DBMS_XPLAN.DISPLAY());
```
Look for `VECTOR` in the output to confirm that the HNSW index is being hit. If it falls back to full table scan, verify index creation, `vector_memory_size`, and stats updates.

## Extension Migrations (Sessions)

SQLSpec configuration wires extension tables for ADK and Litestar:
- `ORACLE_ADK_IN_MEMORY` (default true): enables INMEMORY for `adk_session`, `adk_event`, and optional memory tables.
- `ORACLE_LITESTAR_SESSION_IN_MEMORY` (default true): enables INMEMORY for `app_session`.

## Local Database Lifecycle

The contributor path runs a managed Oracle container. Use these commands to manage it:

```bash
# Start Oracle Free container
make start-infra

# Upgrade database schema (runs SQLSpec migrations)
uv run python manage.py database upgrade --no-prompt

# Load demo fixtures
uv run coffee load-fixtures
```

### Fixture Dependencies
Fixture loading must happen in order:
1. `stores` (coordinates/place_ids)
2. `product` (names, descriptions, stock booleans)
3. dependent semantic rows (embeddings, metrics)

### Maintainer Embedding Regeneration
To regenerate product embeddings:
1. Load new product rows.
2. Run `uv run coffee bulk-embed` to generate vectors via Vertex AI.
3. Run `uv run coffee export-fixtures` to save the updated product embeddings to the committed compressed files (`product.json.gz`).
4. Re-verify by running `uv run coffee load-fixtures` to load the new embeddings.

## Troubleshooting

- **`ORA-51962` during migration:** `vector_memory_size` is zero or too small. Run the SPFILE alteration and restart the container.
- **Slow search / Index not used:** Verify via the EXPLAIN PLAN tool on `/explore`. Check that stats are gathered: `DBMS_STATS.GATHER_TABLE_STATS`.
- **Dimension mismatch:** Confirm no older `768` dimension vectors are present in migrations, fixtures, or code.
