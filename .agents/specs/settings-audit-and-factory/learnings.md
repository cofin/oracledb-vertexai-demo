# Learnings: settings-audit-and-factory

> Synced from Beads epic `oracledb-vertexai-mzm.3`.

## Dead-knob verification (grep-confirmed, 0 production readers)

- `ServerSettings`/`settings.server`, `AgentSettings`/`settings.agent`,
  `CacheSettings`/`settings.cache`: 0 readers across `src/app` + `src/tests`
  (excluding `lib/settings.py`). The `server.asgi`/`server.core` grep matches are
  the `app.server` module path, not the deleted `ServerSettings` class.
- `EMBEDDING_CACHE_ENABLED`/`CACHE_EMBEDDING_ENABLED`: 0 readers. Deleted with
  `CacheSettings`; the embedding cache stays unconditionally on (no bypass branch).
- Vertex dead fields `CACHE_TTL_SECONDS`, `CACHE_PREFIX`, `STREAM_BUFFER_SIZE`,
  `STREAM_TIMEOUT_SECONDS`: 0 readers. mzm.8 had NOT landed (no `AISettings`/
  `ChatSettings` present), so the four dead fields were removed here rather than
  deferred to the broader Vertex rewrite.
- `LogSettings.HTTP_EVENT`: 0 readers (only this LogSettings field was dead).
- `DatabaseSettings.POOL_TIMEOUT`, `POOL_RECYCLE`, `ECHO` (`DATABASE_ECHO`): 0
  readers — never passed to `OracleAsyncConfig`.
- `AppSettings.URL`/`_default_app_url()`: only consumed by `setup_litestar_env()`;
  the `_default_app_url()` logic was inlined into `setup_litestar_env()` so `APP_URL`
  still derives from `LITESTAR_PORT`, then both were deleted.

## What was kept (and why)

- `MapsSettings`/`Settings.maps`: WIRED via `src/app/lib/log/_security.py:18`
  (`get_settings().maps`) for embed CSP headers. Not a future knob.
- All `LogSettings` log-extraction fields read by `_middleware.py`:
  `EXCLUDE_PATHS`, `REQUEST_FIELDS`, `RESPONSE_FIELDS`, `OBFUSCATE_COOKIES`,
  `OBFUSCATE_HEADERS`, `INCLUDE_COMPRESSED_BODY`. Only `HTTP_EVENT` was dead.

## Patterns established

- Single typed-parser path: `_env_bool`/`_env_int`/`_env_str`/`_env_cors` replace
  every ad-hoc `os.getenv(...) in TRUE_VALUES` check. `_env_bool` lower-cases and
  matches `{true,1,yes,y,t,on}`.
- CORS is parsed at field-default time (`_env_cors` returns `list[str]` for both
  JSON-list and comma-list forms), eliminating the `AppSettings.__post_init__`
  mutate-after-init step. `ALLOWED_CORS_ORIGINS` is now strictly `list[str]`, so the
  `cast("list[str]", ...)` in `config.py` was dropped as redundant.
- All settings dataclasses are `frozen=True` (effectively immutable). The one
  necessary post-init mutation — `VertexAISettings.API_KEY = None` when a project is
  configured — uses `object.__setattr__(self, "API_KEY", None)` to stay compatible
  with frozen dataclasses. Wallet `os.environ` writes remain inside `create_config()`.
- The factory is quiet: `Settings.from_env()` no longer calls `console.print`.
- Shell env wins over `.env`: `load_dotenv(env_file, override=False)`. Locked by the
  RED-then-GREEN drift test `test_shell_env_wins_over_dotenv`.

## Deferred

- Lower-case internal field rename (Phase 5) DEFERRED — lowest priority, highest
  churn. Consumers reference UPPER-CASE field names heavily (`config.py` ~10,
  `ioc.py` 8, `commands.py` 4, `_middleware.py` 20+, `_security.py`). Renaming would
  risk the green gate with no functional gain. Public env var names are preserved
  regardless of the rename. Defer to a follow-up flow.

## TDD record

- Phase 1 RED confirmed: `test_shell_env_wins_over_dotenv` failed
  (`assert '9999' == '8123'`) under the old `override=True`; 26 other locking tests
  passed GREEN. After the `override=False` + quiet-factory refactor, all 27 settings
  tests pass GREEN.

## Gate results

- `make lint`: PASS (ruff + mypy/pyright + frontend).
- `uv run pytest src/tests/unit`: 243 passed; the only 2 failures
  (`test_database.py::test_database_remove_is_idempotent_when_container_missing`,
  `::test_database_start_loads_env_file`) are pre-existing — caused by the unrelated
  dirty `tools/oracle/cli/database.py`, confirmed by stashing this chapter's 3 files
  and reproducing the same 2 failures. `test_database.py` imports no settings.
