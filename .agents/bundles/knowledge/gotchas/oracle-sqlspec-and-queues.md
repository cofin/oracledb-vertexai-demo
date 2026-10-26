---
type: Guide
title: Oracle 26ai, SQLSpec & Queues Gotchas
description: SQLSpec 0.69.0 inline LOB defaults, OracledbAsyncQueueStore pool isolation, HNSW FETCH APPROX, and Oracle Text token sanitization
tags:
  - gotchas
  - oracle-26ai
  - sqlspec
  - queues
---

# Oracle 26ai, SQLSpec & Queues Gotchas

## 1. SQLSpec `0.69.0` Inline LOB Defaults (`fetch_lobs=False`) and Queue Pool Isolation

- **Trap**: Sharing `config.db` (`DatabaseSettings.get_config()`) directly with `QueuePlugin` (`SQLSpecQueueBackend`) couples background worker polling with request traffic and allows `OracledbAsyncQueueStore` to mutate `driver_features` and `extension_config` in place on the primary application `OracleAsyncConfig`. Conversely, overriding `fetch_lobs` to `True` forces `python-oracledb` to return `AsyncLOB` locators requiring extra round-trips on every CLOB/BLOB column.
- **Rule**: In SQLSpec `0.69.0` (`src/app/lib/settings/_database.py`), `fetch_lobs` defaults to `False`, so `python-oracledb` bypasses `LOB` locator objects and returns CLOB/BLOB payloads under 1 GB directly as inline Python `str` and `bytes` values across both `select` and `select_stream`. Keep `DatabaseSettings.create_config()` / `get_config()` (`driver_features={"enable_session_tracing": True}`, wire-level `sqlcommenter` via `enable_sqlcommenter=True`, `sqlcommenter_enable_context=True`, `sqlcommenter_enable_traceparent=True`, `ObservabilityConfig`, and Autonomous mTLS `wallet_zip` backed by `extract_oracle_wallet_zip` and `parse_tnsnames_ora`) isolated from `DatabaseSettings.get_queue_config()` (`min=1, max=4`, `session_key="queue_db_session"`, `"manage_lifespan": True`, `driver_features={"fetch_lobs": False, "enable_session_tracing": True}`).

## 2. `OracleAsyncConfig` Connection Config Key and `OracleLoaderService` Inheritance

- **Trap**: Passing legacy `pool_config=` to `OracleAsyncConfig` silently drops credentials and surfaces as `DPY-4001`, and instantiating raw SQL strings or ad-hoc `SQLFileLoader` instances inside services bypasses cached named-SQL resolution.
- **Rule**: Always configure `OracleAsyncConfig(connection_config=...)` in `src/app/lib/settings/_database.py`, and inherit domain database services from `OracleLoaderService` (`self.get_sql("<name>")` backed by `default_sql_loader()`) or `OracleAsyncService` in `src/app/lib/service.py`.

## 3. Oracle HNSW Vector Indexes Require `FETCH APPROX` and Vector Memory

- **Trap**: Oracle `INMEMORY NEIGHBOR GRAPH` (HNSW) indexes fail with `ORA-51962` during DDL if `vector_memory_size` is `0` on `gvenzl/oracle-free:latest`, and fall back to full table scans when queries use `FETCH FIRST :k ROWS ONLY` without `APPROX` or re-order by a joined column (`CASE spi.stock_status ...`) in the same query block.
- **Rule**: `adb-free:latest-26ai` manages vector memory automatically, whereas `ORACLE_CONTAINER_FLAVOR=free` (`gvenzl/oracle-free:latest`) configures `ALTER SYSTEM SET vector_memory_size = 512M SCOPE = SPFILE` in `tools/oracle/on_init/00_configure_vector_memory.sql` (within Oracle Free Edition's 2 GB SGA+PGA cap). Always query HNSW indexes with `ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE) FETCH APPROX FIRST :limit ROWS ONLY`. When joining and re-sorting by store inventory status (`vector-search-products-by-store` in `src/app/db/sql/products.sql`), isolate the HNSW scan inside a `candidate_products` CTE with `FETCH APPROX FIRST 50 ROWS ONLY` before joining `store_product_inventory` and `store`.

## 4. Oracle 26ai Hybrid Vector Indexes Cannot Query External 3072-Dim Vectors

- **Trap**: `CREATE HYBRID VECTOR INDEX` and `DBMS_HYBRID_VECTOR.SEARCH` require an in-database ONNX vectorizer and cannot accept client-generated 3072-dimension Vertex AI `gemini-embedding-2` vectors.
- **Rule**: Use the pure-SQL CTE Reciprocal Rank Fusion queries (`hybrid-search-turn` and `hybrid-search-products` in `src/app/db/sql/hybrid.sql`) combining `CTXSYS.CONTEXT` (`MULTI_COLUMN_DATASTORE` + `SYNC (ON COMMIT)`) `CONTAINS` / `SCORE(1)` with HNSW `VECTOR_DISTANCE ... FETCH APPROX`.

## 5. Oracle Text `CONTAINS` Operator Injection

- **Trap**: Passing raw user input to `CONTAINS(..., :text_query, 1)` raises `DRG-50901` syntax errors when users enter hyphens, apostrophes, braces, or Oracle Text reserved operators (`AND`, `OR`, `NOT`, `NEAR`, `ACCUM`, `SYN`, `ABOUT`, `FUZZY`, `WITHIN`).
- **Rule**: Always sanitize user search phrases through `build_oracle_text_query()` or `build_oracle_proximity_query()` (backed by `extract_search_tokens()`) in `src/app/lib/text_search.py`, which strips non-token characters, removes reserved operators and stopwords, and wraps each searchable term in `{token}` braces.

## 6. `DBMS_VECTOR.UTL_TO_EMBEDDING` URL Length Limit and `:predict` Suffix

- **Trap**: In Oracle AI Database 26ai (`23.26.0.0.0`), `SYS.DBMS_VECTOR.UTL_TO_EMBEDDING` concatenates `url || model` directly without appending `:predict`, and buffers the `"url"` JSON parameter in a 128-character PL/SQL variable (raising `ORA-06502: PL/SQL: numeric or value error: character string buffer too small` when long GCP project IDs push the endpoint URL past 128 characters).
- **Rule**: Always include the `:predict` suffix on `"model"` (for example `"gemini-embedding-2:predict"`) and use the numeric GCP project number in `"url"` so the endpoint prefix stays under 128 characters.
