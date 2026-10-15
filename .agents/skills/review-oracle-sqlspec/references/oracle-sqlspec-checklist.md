# Oracle 26ai & SQLSpec Review Checklist

## SQLSpec & Oracle 26ai Rules

1. **Named SQL & Parameter Binding**:
   - All static domain queries must live in `src/app/db/sql/` with `-- name: <key>` directives and be loaded via `db_manager.get_sql("<key>")` (or `sql_loader.get_sql("<key>")`), while simple CRUD operations may use SQLSpec `sql.insert`, `sql.update`, and `sql.delete` builders.
   - Use Oracle `:name` bind parameters exclusively; never interpolate user strings into SQL or `CONTAINS(...)` clauses without `build_oracle_text_query` token sanitization.
   - Pass Python `list[float]` directly to `VECTOR(3072, FLOAT32)` binds; never manually pack `array.array("f", ...)` or stringify vectors.
2. **HNSW Vector Index Access Path**:
   - Oracle 26ai `INMEMORY NEIGHBOR GRAPH` HNSW indexes only activate when queries order directly by `ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE) FETCH APPROX FIRST :limit ROWS ONLY`. Ordering by `similarity_score DESC` with `FETCH FIRST` forces a full table scan.
3. **Explicit Transaction Commits**:
   - SQLSpec 0.65+ `provide_session` and `driver.execute` do not auto-commit DML; services and stores must call `await driver.commit()` explicitly after `INSERT`, `UPDATE`, `DELETE`, or `MERGE`.
4. **Queue Pool LOB Isolation**:
   - `DatabaseSettings.get_queue_config()` in `src/app/lib/settings/_database.py` must remain a separate `OracleAsyncConfig` (`session_key="queue_db_session"`) from `DatabaseSettings.get_config()` so `OracledbAsyncQueueStore`'s `fetch_lobs=False` mutation never disables `enable_AutoLob=True` on `config.db`.
