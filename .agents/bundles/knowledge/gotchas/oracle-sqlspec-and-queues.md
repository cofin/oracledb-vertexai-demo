---
type: Guide
title: Oracle 26ai, SQLSpec & Queues Gotchas
description: HNSW FETCH APPROX, vector_memory_size, OracledbAsyncQueueStore LOB pool isolation, and Oracle Text token escaping
tags:
  - gotchas
  - oracle-26ai
  - sqlspec
  - queues
---

# Oracle 26ai, SQLSpec & Queues Gotchas

## 1. `OracledbAsyncQueueStore` Disables `enable_AutoLob` (`fetch_lobs=False`)

- **Trap**: `litestar-queues`'s `OracledbAsyncQueueStore` sets `driver_features["fetch_lobs"] = False` on the `OracleAsyncConfig` passed to `SQLSpecBackendConfig`. If `config.db` is shared with `QueuePlugin`, `enable_AutoLob=True` is disabled globally and CLOB/JSON reads in `OracleSessionStore`, `OracleEventStore`, and product queries return raw `AsyncLOB` objects instead of `str`/`dict`.
- **Rule**: Always pass `DatabaseSettings.get_queue_config()` (`session_key="queue_db_session"`) to `SQLSpecBackendConfig`, keeping `DatabaseSettings.get_config()` isolated for application queries.

## 2. Oracle HNSW Vector Indexes Require `FETCH APPROX` and `vector_memory_size`

- **Trap**: Oracle `INMEMORY NEIGHBOR GRAPH` (HNSW) indexes fail with `ORA-51962` during DDL if `vector_memory_size` is `0`, and fall back to full table scans if queries use `FETCH FIRST :k ROWS ONLY` without `APPROX` or re-order by a joined column (`CASE spi.stock_status ...`) in the same query block.
- **Rule**: Configure `ALTER SYSTEM SET vector_memory_size = 512M SCOPE = SPFILE;` (or `4G` on larger instances) and always query with `ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE) FETCH APPROX FIRST :limit ROWS ONLY`. When joining and re-sorting by store inventory status (`vector-search-products-by-store`), isolate the HNSW candidate scan in a `candidate_products` CTE with `FETCH APPROX FIRST 50 ROWS ONLY` before joining `store_product_inventory` and `store`.

## 3. Oracle 26ai Hybrid Vector Indexes Cannot Query External 3072-Dim Vectors

- **Trap**: `CREATE HYBRID VECTOR INDEX` / `DBMS_HYBRID_VECTOR.SEARCH` requires an in-database ONNX vectorizer and cannot accept client-generated 3072-dimension Vertex AI `gemini-embedding-2` vectors.
- **Rule**: Use the pure-SQL CTE Reciprocal Rank Fusion query (`hybrid-search-turn` in `src/app/db/sql/hybrid.sql`) combining `CTXSYS.CONTEXT` (`MULTI_COLUMN_DATASTORE` + `SYNC (ON COMMIT)`) `CONTAINS`/`SCORE(1)` with HNSW `VECTOR_DISTANCE ... FETCH APPROX`.

## 4. Oracle Text `CONTAINS` Operator Injection

- **Trap**: Passing raw user input to `CONTAINS(..., :text_query, 1)` raises `DRG-50901` syntax errors when users type hyphens, braces, or reserved words (`AND`, `OR`, `NOT`, `NEAR`, `SYN`, `ABOUT`).
- **Rule**: Always sanitize user text through `build_oracle_text_query()` in `src/app/domain/chat/services/_router.py` (and `_sanitize_oracle_text_query()` in `src/app/domain/products/services/_products.py`), which strips non-alphanumeric characters, removes Oracle Text operators, and wraps each token in `{token}` braces.

## 5. `DBMS_VECTOR.UTL_TO_EMBEDDING` URL Length Limit and `:predict` Suffix

- **Trap**: In Oracle AI Database 26ai (`23.26.0.0.0`), `SYS.DBMS_VECTOR.UTL_TO_EMBEDDING` concatenates `url || model` directly without appending `:predict`, and buffers the `"url"` JSON parameter in a 128-character PL/SQL variable (raising `ORA-06502: PL/SQL: numeric or value error: character string buffer too small` when long GCP project IDs exceed 128 characters).
- **Rule**: Always include the `:predict` suffix on `"model"` (for example `"text-embedding-004:predict"` or `"gemini-embedding-2:predict"`) and use the numeric GCP project number in `"url"` so the endpoint prefix stays under 128 characters.
