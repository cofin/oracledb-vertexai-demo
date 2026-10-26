# Oracle 26ai & SQLSpec Review Checklist

## SQLSpec `0.69.0`, Oracle 26ai & APEX 26.1 Rules

1. **Named SQL, Service Bases & Text Query Sanitization**:
   - Static domain queries live in `src/app/db/sql/` with `-- name: <key>` directives. Data services inherit from `OracleLoaderService` (`self.get_sql("<key>")` backed by `default_sql_loader()`) or `OracleAsyncService` in `src/app/lib/service.py`, while simple CRUD operations may use SQLSpec `sql.insert`, `sql.update`, and `sql.delete` builders.
   - Use Oracle `:name` bind parameters exclusively; never interpolate user strings into SQL or `CONTAINS(...)` clauses without `build_oracle_text_query` or `build_oracle_proximity_query` from `src/app/lib/text_search.py`.
   - Pass Python `list[float]` directly to `VECTOR(3072, FLOAT32)` binds; never manually pack `array.array("f", ...)` or stringify vectors.
2. **SQLSpec `0.69.0` Inline LOBs, Tracing & Wallet Config (`src/app/lib/settings/_database.py`)**:
   - SQLSpec `0.69.0` defaults `fetch_lobs` to `False`, returning `CLOB` and `BLOB` columns under 1 GB directly as inline Python `str` / `bytes` across `select` and `select_stream` without `LOB` locator round-trips.
   - `DatabaseSettings.create_config()` (aliased by `DatabaseSettings.get_config()`) in `src/app/lib/settings/_database.py` configures `driver_features={"enable_session_tracing": True}`, wire-level `sqlcommenter` (`enable_sqlcommenter=True`, `sqlcommenter_enable_context=True`, `sqlcommenter_enable_traceparent=True`), `ObservabilityConfig`, and Autonomous Database mTLS `"wallet_zip"` / `"wallet_password"` `connection_config` keys (resolved by SQLSpec's `extract_oracle_wallet_zip` and `parse_tnsnames_ora`, which are also called directly in `src/app/cli/_helpers/ords.py` and `tools/oracle/`).
3. **Queue Pool Isolation (`DatabaseSettings.get_queue_config()`)**:
   - `DatabaseSettings.get_queue_config()` in `src/app/lib/settings/_database.py` must remain a dedicated `OracleAsyncConfig` (`min=1, max=4`, `session_key="queue_db_session"`, `"manage_lifespan": True`, `driver_features={"fetch_lobs": False, "enable_session_tracing": True}`), isolating `OracledbAsyncQueueStore`'s background worker pool and in-place `driver_features` and `extension_config` mutations from `config.db`.
4. **HNSW Vector Index Access Path & Explicit Transaction Commits**:
   - Oracle 26ai `INMEMORY NEIGHBOR GRAPH` HNSW indexes only activate when queries order directly by `ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE) FETCH APPROX FIRST :limit ROWS ONLY` (isolated inside a CTE before relational joins or stock-status re-sorting). Ordering by `similarity_score DESC` with `FETCH FIRST` forces a full table scan.
   - SQLSpec `provide_session` and `driver.execute` do not auto-commit DML; services and stores must call `await driver.commit()` explicitly after `INSERT`, `UPDATE`, `DELETE`, or `MERGE`.
5. **APEX 26.1 Provisioning, PL/SQL Bind Safety & Packaged CDN SQL**:
   - Packaged Cloud Run ORDS static-asset scripts live in `src/app/db/sql/deploy/configure-apex-cdn.sql` and `src/app/db/sql/deploy/revert-apex-cdn.sql` so wheel and PyApp deployments remain self-contained, and declarative APEXlang application sources live under `src/apex/cymbal-coffee-ops/`.
   - Oracle and APEX provisioning modules (`tools/oracle/adb.py`, `tools/oracle/cli/apex.py`, `tools/oracle/apex_vertex.py`) must pass secrets, OAuth2 tokens, gateway keys, hosts, URLs, and workspace names through PL/SQL bind parameters in `DBMS_NETWORK_ACL_ADMIN`, `APEX_CREDENTIAL`, `APEX_INSTANCE_ADMIN`, and `APEX_AI` blocks, validate schema identifiers strictly (`_ORACLE_IDENTIFIER_RE` / `DBMS_ASSERT.SIMPLE_SQL_NAME`), and never interpolate unescaped secrets into SQL or error strings.
