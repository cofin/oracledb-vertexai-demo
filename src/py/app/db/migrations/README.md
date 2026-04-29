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

Use the CLI to generate timestamped migrations:

```bash
sqlspec create-migration "add user table"
# Creates: 20251011120000_add_user_table.sql
```

The timestamp is automatically generated in UTC timezone.

## Migration Execution

Migrations are applied in chronological order based on their timestamps.
The database tracks both version and execution order separately to handle
out-of-order migrations gracefully (e.g., from late-merging branches).

## Current Baseline Schema (0001)

The initial Oracle 23ai schema in this project includes:

- `product` table (`INMEMORY PRIORITY HIGH`) with `BOOLEAN` stock flag, `JSON` metadata, and `VECTOR(3072, FLOAT32)` embeddings produced by `gemini-embedding-001`.
- `store` table for location data with `JSON`-encoded business hours.
- `response_cache`, `embedding_cache`, `intent_exemplar`, and `search_metric` support tables.
- HNSW vector indexes (`ORGANIZATION INMEMORY NEIGHBOR GRAPH`, `NEIGHBORS=40`, `EFCONSTRUCTION=500`, `TARGET ACCURACY=95`, `DISTANCE COSINE`) on `product`, `intent_exemplar`, and `embedding_cache`.

## Vector Memory Pool

Oracle 23ai requires a non-zero `vector_memory_size` allocation before HNSW INMEMORY indexes can be built. Without it, `CREATE VECTOR INDEX ... ORGANIZATION INMEMORY NEIGHBOR GRAPH` fails with `ORA-51962`.

Configure the pool once per database (the change is persisted in SPFILE and requires a restart):

```sql
ALTER SYSTEM SET vector_memory_size = 4G SCOPE=SPFILE;
SHUTDOWN IMMEDIATE;
STARTUP;
```

For the dev container, see `tools/oracle/configure_vector_memory.sql` and the matching `make` target.

Verify the pool is allocated:

```sql
SELECT NAME, BYTES FROM V$SGAINFO WHERE NAME LIKE '%Vector%';
```

A non-zero `Vector Memory` row confirms the pool is live. `4G` is the project floor; bump higher if `bulk-embed` runs report `ORA-51963` (pool exhausted) — the rule of thumb is `2 × (rows × dim × 4 bytes × HNSW overhead ~1.4×)`.
