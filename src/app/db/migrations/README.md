# SQLSpec Migrations

This directory contains database migration files.

## File Format

Migration files use SQLFileLoader's named query syntax with versioned names:

```sql
-- name: migrate-20251011120000-up
CREATE TABLE example (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

-- name: migrate-20251011120000-down
DROP TABLE example;
```

## Naming Conventions

### File Names

Format: `{version}_{description}.sql`

- Version: Timestamp in YYYYMMDDHHmmss format (UTC)
- Description: Brief description using underscores
- Example: `20251011120000_create_users_table.sql`

### Query Names

- Upgrade: `migrate-{version}-up`
- Downgrade: `migrate-{version}-down`

## Version Format

Migrations use **timestamp-based versioning** (YYYYMMDDHHmmss):

- **Format**: 14-digit UTC timestamp
- **Example**: `20251011120000` (October 11, 2025 at 12:00:00 UTC)
- **Benefits**: Eliminates merge conflicts when multiple developers create migrations concurrently

### Creating Migrations

Use the local SQLSpec management entrypoint to generate timestamped migrations:

```bash
uv run python manage.py database create-migration "add user table"
# Creates: 20251011120000_add_user_table.sql
```

The timestamp is automatically generated in UTC timezone.

## Migration Execution

Migrations are applied in chronological order based on their timestamps.
The database tracks both version and execution order separately to handle
out-of-order migrations gracefully (e.g., from late-merging branches).

## Current Baseline Schema (0001)

The initial Oracle 26ai schema in this project includes:

- `product` table (`INMEMORY PRIORITY HIGH`) with `BOOLEAN` stock flag, `JSON` metadata, and `VECTOR(3072, FLOAT32)` embeddings produced by `gemini-embedding-2-preview`.
- `store` table for location data with `JSON`-encoded business hours.
- `store_product_inventory` table for curated store-level product availability.
- `response_cache`, `embedding_cache`, and `search_metric` support tables.
- HNSW vector indexes (`ORGANIZATION INMEMORY NEIGHBOR GRAPH`, `NEIGHBORS=40`, `EFCONSTRUCTION=500`, `TARGET ACCURACY=95`, `DISTANCE COSINE`) on `product` and `embedding_cache`.

## Schema Annotations

The baseline DDL demonstrates Oracle AI Database 26ai schema annotations
inline in the existing `CREATE TABLE`, column definition, and supported
`CREATE INDEX` statements. `COMMENT ON` statements remain in place for
compatibility with older tooling; annotations carry richer application metadata
such as embedding model, dimensions, distance metric, cache role, and the
privacy boundary for store coordinates.

Inspect the applied metadata through Oracle's annotation dictionary views:

```sql
SELECT object_name,
       object_type,
       column_name,
       annotation_name,
       annotation_value
FROM user_annotations_usage
WHERE object_name IN (
    'PRODUCT',
    'STORE',
    'STORE_PRODUCT_INVENTORY',
    'EMBEDDING_CACHE',
    'PRODUCT_IN_STOCK_IDX'
)
ORDER BY object_name, column_name, annotation_name;
```

## Vector Memory Pool

Oracle 26ai requires a non-zero `vector_memory_size` allocation before HNSW INMEMORY indexes can be built. Without it, `CREATE VECTOR INDEX ... ORGANIZATION INMEMORY NEIGHBOR GRAPH` fails with `ORA-51962`.

Configure the pool once per database (the change is persisted in SPFILE and requires a restart). On **Oracle Free Edition**, `sga_max_size`/`sga_target` are locked (ORA-56752 if you try to bump them) — the vector pool has to fit inside the existing ~1.5 GB SGA. 512 MB is plenty for the 122 committed product vectors at 3072 dims plus query embeddings saved in `embedding_cache`:

```sql
ALTER SYSTEM SET vector_memory_size = 512M SCOPE=SPFILE;
SHUTDOWN IMMEDIATE;
STARTUP;
```

For Oracle Standard / Enterprise / Autonomous (no Free SGA cap), scale up — e.g. 6 GB SGA / 4 GB vector pool. The standalone script `tools/oracle/configure_vector_memory.sql` ships with the Standard/Enterprise values; use the Free-friendly values above if you reuse it on Free.

For the dev container the pool is set automatically: `tools/oracle/on_init/00_configure_vector_memory.sql` runs once on first DB creation (executes the `ALTER SYSTEM ... SCOPE=SPFILE` and bounces the instance), and `tools/oracle/on_startup/00_verify_vector_memory.sql` confirms the allocation on every container restart (visible via `make infra-logs`). For autonomous DB or other shared instances, run `tools/oracle/configure_vector_memory.sql` as SYSDBA.

Verify the pool is allocated:

```sql
SELECT NAME, BYTES FROM V$SGAINFO WHERE NAME LIKE '%Vector%';
```

A non-zero `Vector Memory` row confirms the pool is live. The standalone script uses a 4G target for larger Oracle editions; keep the Free-friendly 512 MB value above when using Oracle Free Edition. Bump higher if `bulk-embed` runs report `ORA-51963` (pool exhausted) — Oracle's rough HNSW pool estimate is `1.3 × rows × dim × element size`; use `DBMS_VECTOR.INDEX_VECTOR_MEMORY_ADVISOR` for exact sizing.
