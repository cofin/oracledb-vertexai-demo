# Oracle 26ai & SQLSpec False-Positive Suppressions

DO NOT FLAG any of the following verified Oracle 26ai and SQLSpec patterns:

## `FP-ORA-01` — Pure-SQL Hybrid RRF (`hybrid-search-turn`) Instead of `DBMS_HYBRID_VECTOR.SEARCH`

- **DO NOT FLAG** the pure-SQL CTE Reciprocal Rank Fusion query in `src/app/db/sql/hybrid.sql` (`hybrid-search-turn`) or suggest replacing it with `CREATE HYBRID VECTOR INDEX` / `DBMS_HYBRID_VECTOR.SEARCH`.
- **Rationale**: Oracle 26ai Hybrid Vector Indexes maintain internal `$VR` tables and only support in-database ONNX embedding models; they cannot query external 3072-dimension Vertex AI `gemini-embedding-2` vectors generated client-side.

## `FP-ORA-02` — Separate `DatabaseSettings.get_queue_config()` Pool

- **DO NOT FLAG** `DatabaseSettings.get_queue_config()` in `src/app/lib/settings/_database.py` as a duplicate of `DatabaseSettings.get_config()`.
- **Rationale**: `litestar-queues`'s `OracledbAsyncQueueStore` mutates `driver_features["fetch_lobs"] = False` on its `OracleAsyncConfig`. Sharing the primary config breaks CLOB/JSON auto-materialization across `OracleSessionStore`, `OracleEventStore`, and product queries.

## `FP-ORA-03` — Braced `{token}` Escaping in `build_oracle_text_query`

- **DO NOT FLAG** `{token}` braces in `src/app/domain/chat/services/_router.py` as SQL injection or unparameterized SQL.
- **Rationale**: `build_oracle_text_query` strips non-alphanumeric characters and wraps each sanitized token in `{token}` before binding the result as the `:text_query` bind parameter to `CONTAINS(..., :text_query, 1)`, escaping Oracle Text operators (`AND`, `OR`, `NOT`, `NEAR`, `ACCUM`, `SYN`).
