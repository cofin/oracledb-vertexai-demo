# Oracle 26ai & SQLSpec False-Positive Suppressions

DO NOT FLAG any of the following verified Oracle 26ai and SQLSpec patterns:

## `FP-ORA-01` — Pure-SQL Hybrid RRF (`hybrid-search-turn`) Instead of `DBMS_HYBRID_VECTOR.SEARCH`

- **DO NOT FLAG** the pure-SQL CTE Reciprocal Rank Fusion query in `src/app/db/sql/hybrid.sql` (`hybrid-search-turn`) or suggest replacing it with `CREATE HYBRID VECTOR INDEX` / `DBMS_HYBRID_VECTOR.SEARCH`.
- **Rationale**: Oracle 26ai Hybrid Vector Indexes maintain internal `$VR` tables and only support in-database ONNX embedding models; they cannot query external 3072-dimension Vertex AI `gemini-embedding-2` vectors generated client-side.

## `FP-ORA-02` — SQLSpec `0.69.0` Inline LOB Default and Separate `DatabaseSettings.get_queue_config()` Pool

- **DO NOT FLAG** `DatabaseSettings.create_config()` / `DatabaseSettings.get_config()` for omitting explicit LOB flags or `DatabaseSettings.get_queue_config()` in `src/app/lib/settings/_database.py` as a duplicate pool configuration.
- **Rationale**: SQLSpec `0.69.0` defaults `fetch_lobs` to `False`, returning `CLOB` and `BLOB` columns under 1 GB directly as inline Python `str` / `bytes` without `LOB` locator round-trips. `DatabaseSettings.get_queue_config()` (`min=1, max=4`, `session_key="queue_db_session"`, `"manage_lifespan": True`, `driver_features={"fetch_lobs": False, "enable_session_tracing": True}`) isolates `OracledbAsyncQueueStore`'s dedicated background worker pool and in-place `driver_features` / `extension_config` mutations from `config.db`.

## `FP-ORA-03` — Braced `{token}` Escaping in `build_oracle_text_query` and `build_oracle_proximity_query`

- **DO NOT FLAG** `{token}` braces in `src/app/lib/text_search.py`, `src/app/domain/chat/services/_router.py`, or `src/app/domain/products/services/_vector.py` as SQL injection or unparameterized SQL.
- **Rationale**: `build_oracle_text_query` and `build_oracle_proximity_query` in `src/app/lib/text_search.py` strip non-alphanumeric characters, drop Oracle Text reserved words and stopwords, and wrap each sanitized token in `{token}` before binding the result as `:text_query` to `CONTAINS(..., :text_query, 1)`, escaping Oracle Text operators (`AND`, `OR`, `NOT`, `NEAR`, `ACCUM`, `SYN`).

## `FP-ORA-04` — Validated Schema Identifier Substitution in APEX and ADB Provisioning PL/SQL

- **DO NOT FLAG** `__APEX_SCHEMA__` substitution in `tools/oracle/apex_vertex.py` or `DBMS_ASSERT.SIMPLE_SQL_NAME(:schema_name)` DDL execution in `tools/oracle/adb.py` as SQL injection.
- **Rationale**: Oracle PL/SQL does not permit bind variables for package schema qualifiers (`APEX_NNNNNN.wwv_flow_imp`) or `CREATE USER` DDL identifiers. Both provisioning tools validate identifiers strictly against `^[A-Za-z][A-Za-z0-9_$#]*$` (and `DBMS_ASSERT.SIMPLE_SQL_NAME`) while passing all credentials, tokens, hosts, and URLs via `:bind` parameters.
