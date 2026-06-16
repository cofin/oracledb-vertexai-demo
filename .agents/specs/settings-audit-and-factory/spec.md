# Flow: settings-audit-and-factory

*Beads: oracledb-vertexai-mzm.3*

## Specification

Absorbs and compresses old PRD Chapters 1 (contract-audit), 2 (core-factory),
and the field-level dead-knob deletions. This is the foundation chapter: it
locks current behavior with a test suite, then makes the settings factory quiet,
typed, and effectively immutable, and deletes verified-dead settings branches and
fields. Lower-case field renaming is the lowest-priority item and is deferrable
(see trade-off note in Phase 4).

### Requirements

1. TEST-FIRST. Extend `src/tests/unit/app/lib/test_settings.py` to lock today's
   observable behavior before any production change. The suite must cover:
   - `.env` loading and shell-env precedence (shell wins over `.env`).
   - Boolean parsing of common true/false spellings (`True/true/1/yes/Y/T` vs
     `False/false/0/no/n/empty`).
   - `ALLOWED_CORS_ORIGINS` parsing: JSON-list form (`["*"]`) and comma-list form
     (`a.com,b.com`).
   - `SECRET_KEY` behavior: explicit env value is honored; absent value yields a
     stable non-empty generated key within a single settings instance.
   - `DatabaseSettings.create_config()` for local mode and wallet/autonomous mode.
   - `get_settings()` caching plus the documented reset hook
     (`Settings.from_env.cache_clear()`), so tests can re-read env.
2. Replace ad-hoc `os.getenv(...) in TRUE_VALUES` checks with small typed parser
   helpers (`_env_bool`, `_env_int`, `_env_str`, `_env_list`/CORS parser). One
   parsing path, used by every field.
3. Replace `AppSettings.__post_init__` mutation of `ALLOWED_CORS_ORIGINS` with
   parse-time conversion so the field is a `list[str]` from construction and the
   dataclass holds no mutate-after-init step.
4. Make settings effectively immutable. Handlers and services must not be able to
   mutate a resolved settings object. Use `frozen=True` dataclasses (or an
   equivalent guard) where it does not break wallet `os.environ` side effects that
   must stay in `create_config()`, not in `__post_init__`.
5. Stop printing during settings construction. `Settings.from_env()` must not call
   `console.print`. CLI commands may print that config loaded; the factory stays
   quiet and testable.
6. Switch dotenv loading to `override=False` so shell env wins over `.env`
   (reverses the current `override=True`). Cover with a precedence test.
7. DELETE verified-dead settings (0 production readers confirmed via grep on
   `src/app`, excluding `lib/settings.py` and JS asset bundles):
   - `ServerSettings` class and `Settings.server` field.
   - `AgentSettings` class and `Settings.agent` field (all fields:
     `INTENT_THRESHOLD`, `VECTOR_SEARCH_THRESHOLD`, `VECTOR_SEARCH_LIMIT`,
     `CONVERSATION_HISTORY_LIMIT`, `SESSION_EXPIRE_HOURS`). Live chat defaults move
     to `ChatSettings` in flow `settings-ai-chat-web-log` (mzm.8), not here.
   - `CacheSettings` class and `Settings.cache` field (`RESPONSE_TTL_MINUTES`,
     `EMBEDDING_CACHE_ENABLED`). Live response-cache TTL moves to `ChatSettings`
     in mzm.8.
   - `VertexAISettings.CACHE_TTL_SECONDS`, `CACHE_PREFIX`, `STREAM_BUFFER_SIZE`,
     `STREAM_TIMEOUT_SECONDS` (the broader `VertexAISettings -> AISettings` rewrite
     happens in mzm.8; this flow only removes the four dead fields if mzm.8 has not
     yet landed, otherwise mzm.8 subsumes them).
   - `LogSettings.HTTP_EVENT` (only this LogSettings field is dead).
   - `DatabaseSettings.POOL_TIMEOUT`, `POOL_RECYCLE`, `ECHO` (never passed to
     `OracleAsyncConfig`).
   - `AppSettings.URL` plus the `_default_app_url()` helper, IF nothing depends on
     it. NOTE: `Settings.setup_litestar_env()` currently seeds `APP_URL` from
     `self.app.URL`, and `test_litestar_env_defaults_app_url_from_litestar_port`
     asserts that. Keep `setup_litestar_env()` deriving `APP_URL` directly from
     `LITESTAR_PORT` (inline the helper) rather than dropping the behavior.
8. KEEP `MapsSettings` and `Settings.maps`. It is WIRED via
   `src/app/lib/log/_security.py:18` (`get_settings().maps`) for embed CSP headers.
   Do not delete it as a "future knob".
9. Preserve all PUBLIC env var names already documented/used:
   `DATABASE_*`, `WALLET_*`, `TNS_ADMIN`, `SECRET_KEY`, `LITESTAR_*`,
   `VERTEX_AI_*`, `GOOGLE_*`, `VITE_*`, `ASSET_URL`. Renaming is internal field
   names only, never env keys.
10. Project rules: dataclasses only (no `pydantic-settings`); no compat shims or
    re-export stubs for removed classes; behavior-only docstrings; never log
    secrets, wallet passwords, or connection URLs.

### Code Analysis Summary

- `src/app/lib/settings.py` is the single settings module.
  - `TRUE_VALUES` set + `os.getenv(...) in TRUE_VALUES` repeated across
    `DatabaseSettings`, `AppSettings`, `MapsSettings`, `VertexAISettings`,
    `ViteSettings` (lines 81, 83, 85, 88, 213, 281, 319, 412, 421, etc.).
  - `AppSettings.__post_init__` (lines 298-312) mutates `ALLOWED_CORS_ORIGINS`
    in place from str to list.
  - `VertexAISettings.__post_init__` (lines 358-368) mutates global `os.environ`
    and sets `self.API_KEY = None`. (Side-effect relocation is mzm.8 scope; this
    flow keeps it working but should not depend on field-name casing for it.)
  - `Settings.from_env()` (lines 478-502) is `@lru_cache(maxsize=1)`, calls
    `console.print` (line 489), and uses `load_dotenv(env_file, override=True)`
    (line 494). `get_settings()` (lines 505-506) delegates to it.
  - `Settings.setup_litestar_env()` (lines 470-476) seeds `APP_URL`,
    `LITESTAR_APP`, `LITESTAR_APP_NAME`, Granian defaults via `os.environ.setdefault`.
- Dead-knob verification (grep `src/app --include=*.py`, minus `lib/settings.py`):
  - `ServerSettings`/`settings.server`: 0 readers.
  - `AgentSettings`/`settings.agent`: 0 readers.
  - `CacheSettings`/`settings.cache`: 0 readers.
  - `POOL_TIMEOUT`, `POOL_RECYCLE`, `.ECHO`, `HTTP_EVENT`, `CACHE_TTL_SECONDS`,
    `CACHE_PREFIX`, `STREAM_BUFFER_SIZE`, `STREAM_TIMEOUT_SECONDS`,
    `INTENT_THRESHOLD`, `VECTOR_SEARCH_*`, `CONVERSATION_HISTORY_LIMIT`,
    `SESSION_EXPIRE_HOURS`, `RESPONSE_TTL_MINUTES`, `EMBEDDING_CACHE_ENABLED`,
    `set_static_files`, `VITE_HOT_RELOAD`, `AppSettings.URL`: 0 readers.
  - CORRECTION to old PRD: `LogSettings.EXCLUDE_PATHS`, `REQUEST_FIELDS`,
    `RESPONSE_FIELDS`, `OBFUSCATE_COOKIES`, `OBFUSCATE_HEADERS`,
    `INCLUDE_COMPRESSED_BODY` are NOT dead — `src/app/lib/log/_middleware.py`
    (lines 76-101, 147, 170) reads all of them, and `StructlogMiddleware` is wired
    at `src/app/server/core.py:30`. Only `HTTP_EVENT` is dead. Do NOT delete the
    logging extraction fields here.
- `MapsSettings` wired at `src/app/lib/log/_security.py:16-21` (`embed_enabled`).
- Call sites that must keep working after field changes:
  - `src/app/config.py`: `settings.db.create_config()`, `settings.app.SECRET_KEY`,
    `CSRF_*`, `ALLOWED_CORS_ORIGINS`, `settings.log.LEVEL/SQLSPEC_LEVEL/GRANIAN_*`,
    `settings.vite.get_config()`.
  - `src/app/ioc.py`: `settings.vertex_ai.*` (mzm.8 touches these).
  - `src/app/cli/commands.py:118-121`: `model-info` reads `vertex_ai.*` (mzm.8).
- Existing tests already in `src/tests/unit/app/lib/test_settings.py` reference
  `DatabaseSettings`, `Settings`, `VertexAISettings`, `ViteSettings` and the
  UPPER-CASE field names (`EMBEDDING_MODEL`, `WALLET_LOCATION`, `SERVICE_NAME`).
  A lower-case rename must update these in lockstep.

## Implementation Plan

### Phase 1: Lock current behavior with tests (TEST-FIRST)

- [x] 1.1 In `src/tests/unit/app/lib/test_settings.py`, add `test_shell_env_wins_over_dotenv`:
      write a temp `.env` with `LITESTAR_PORT=9999`, set `LITESTAR_PORT=8123` via
      monkeypatch, call `Settings.from_env.cache_clear()` then
      `Settings.from_env(<tmp .env path>)`, assert the shell value wins. (This test
      FAILS today because `override=True`; it is the required failing drift test.)
- [x] 1.2 Add `test_env_bool_parsing` covering `True/true/1/yes/Y/T` -> True and
      `False/false/0/no/n/""` -> False against a representative bool field
      (e.g. `DATABASE_ADK_IN_MEMORY`/`ORACLE_ADK_IN_MEMORY`).
- [x] 1.3 Add `test_allowed_cors_origins_json_list` (`["*"]` -> `["*"]`) and
      `test_allowed_cors_origins_comma_list` (`a.com,b.com` -> `["a.com","b.com"]`).
- [x] 1.4 Add `test_secret_key_honors_env` (explicit `SECRET_KEY` preserved) and
      `test_secret_key_generated_when_absent` (non-empty, stable within one instance).
- [x] 1.5 Add `test_create_config_local_mode` (no URL/wallet -> `connection_config`
      has `user/password/dsn/min/max`, no wallet keys) and reuse/extend the
      existing wallet test (`test_wallet_location_resolves_to_absolute_path`).
- [x] 1.6 Add `test_get_settings_cache_and_reset`: two `get_settings()` calls return
      the same object; after `Settings.from_env.cache_clear()` + env change, a new
      object reflects the change.
- [x] 1.7 Run the suite; confirm 1.1 (and any other drift assertions) fail RED while
      the rest pass GREEN. Record the RED list in the Beads note.

### Phase 2: Typed parser helpers + parse-time CORS

- [x] 2.1 Add module-level helpers in `settings.py`: `_env_bool(name, default)`,
      `_env_int(name, default)`, `_env_str(name, default)`, and a CORS parser that
      accepts JSON-list or comma-list and returns `list[str]`.
- [x] 2.2 Replace every `os.getenv(...) in TRUE_VALUES` with `_env_bool(...)`; remove
      the `TRUE_VALUES` set once unused.
- [x] 2.3 Replace `AppSettings.__post_init__` CORS mutation (lines 298-312) with the
      CORS parser applied at field default/parse time so `ALLOWED_CORS_ORIGINS` is a
      `list[str]` from construction; delete `__post_init__`.
- [x] 2.4 Re-run tests from Phase 1; 1.2 and 1.3 stay GREEN against the new helpers.

### Phase 3: Quiet, immutable factory + shell-env precedence

- [x] 3.1 Remove the `console.print` from `Settings.from_env()` (line 489).
- [x] 3.2 Change `load_dotenv(env_file, override=True)` to `override=False`
      (line 494); update the inline comment to state shell env wins.
- [x] 3.3 Make the settings dataclasses effectively immutable (`frozen=True` where
      feasible). Keep wallet `os.environ` writes inside `create_config()` only;
      ensure no field assignment happens after construction in non-create paths.
- [x] 3.4 Keep one cached `get_settings()` path and the documented reset hook
      (`Settings.from_env.cache_clear()`); confirm `src/app/config.py:_reset()` and
      `src/app/config.py:274` still call it. Re-run Phase 1 tests: 1.1 and 1.6 GREEN.

### Phase 4: Delete dead settings branches and fields

- [x] 4.1 Delete `ServerSettings` (lines 200-221) and `Settings.server` (line 462).
      Inline `_default_app_url()` logic into `setup_litestar_env()` so `APP_URL`
      still derives from `LITESTAR_PORT`; then delete `_default_app_url()` and
      `AppSettings.URL` (line 279).
- [x] 4.2 Delete `AgentSettings` (lines 385-402) and `Settings.agent` (line 465).
      (Live chat defaults are reintroduced as `ChatSettings` in mzm.8.)
- [x] 4.3 Delete `CacheSettings` (lines 405-414) and `Settings.cache` (line 466).
- [x] 4.4 Delete `VertexAISettings.CACHE_TTL_SECONDS`, `CACHE_PREFIX`,
      `STREAM_BUFFER_SIZE`, `STREAM_TIMEOUT_SECONDS` (lines 370-382) ONLY if mzm.8
      has not already replaced `VertexAISettings`; if mzm.8 landed first, this is a
      no-op.
- [x] 4.5 Delete `LogSettings.HTTP_EVENT` (line 234) ONLY. Leave `EXCLUDE_PATHS`,
      `REQUEST_FIELDS`, `RESPONSE_FIELDS`, `OBFUSCATE_*`, `INCLUDE_COMPRESSED_BODY`
      in place — they are read by `_middleware.py`.
- [x] 4.6 Delete `DatabaseSettings.POOL_TIMEOUT`, `POOL_RECYCLE`, `ECHO`
      (lines 77-82).
- [x] 4.7 `grep -rn` each removed name across `src/app` and `src/tests` (excluding
      JS assets); confirm 0 remaining references; fix any test that referenced a
      removed knob.

### Phase 5: Lower-case field rename (LOWEST PRIORITY — deferrable)

> TRADE-OFF: This rename is the lowest-value, highest-churn item. If it threatens
> the chapter's scope or timeline, SKIP it and ship Phases 1-4 (dead-knob deletion,
> immutability, quiet factory, shell-env precedence) as the chapter deliverable.
> Defer the rename to a follow-up flow and flag it in the Beads note. Public env
> var names are NEVER renamed regardless.

- [-] 5.1 DEFERRED. If proceeding: rename internal dataclass field names to lower-case
      (`SECRET_KEY` field -> `secret_key`, etc.) WITHOUT changing the env keys read
      by `default_factory`.
- [-] 5.2 DEFERRED. Update all app call sites in one pass: `src/app/config.py`,
      `src/app/ioc.py`, `src/app/cli/commands.py`, `src/app/lib/log/_middleware.py`,
      `src/app/lib/log/_security.py`, `src/app/domain/chat/services/adk.py`.
- [-] 5.3 DEFERRED. Update `src/tests/unit/app/lib/test_settings.py` and any other tests
      asserting UPPER-CASE field names.

### Phase 6: Verify

- [x] 6.1 `uv run pytest src/tests/unit/app/lib` passes (all new + existing).
- [x] 6.2 `make lint` passes for `settings.py` and updated call sites.
- [x] 6.3 `git diff --check` clean; record deferred-rename decision in the Beads note.

## Acceptance

- [x] `src/tests/unit/app/lib/test_settings.py` covers: dotenv load + shell-env
      precedence, bool parsing, CORS JSON/comma parsing, SECRET_KEY behavior,
      `create_config()` local + wallet modes, and `get_settings()` cache + reset.
- [x] At least one drift test (shell-env-wins) was RED before the `override=False`
      change and GREEN after.
- [x] `Settings.from_env()` no longer prints during construction.
- [x] Shell env overrides `.env` (e.g. `LITESTAR_PORT` shell value wins).
- [x] Settings objects cannot be mutated by handlers/services after construction.
- [x] No `os.getenv(...) in TRUE_VALUES` remains; one typed parser path is used.
- [x] `ServerSettings`, `AgentSettings`, `CacheSettings`, and the listed dead fields
      are gone, with 0 dangling references and no compat shim/re-export.
- [x] `MapsSettings` and `Settings.maps` are retained and still resolve in
      `_security.py`.
- [x] `LogSettings` log-extraction fields read by `_middleware.py` are retained;
      only `HTTP_EVENT` removed.
- [x] Public env var names unchanged. Lower-case rename explicitly DEFERRED and noted
      (Phase 5 marked deferred; public env var names preserved regardless).

## Verification

```bash
uv run pytest src/tests/unit/app/lib
make lint
git diff --check
```

```bash
# Confirm dead knobs are gone and nothing references them
grep -rn "ServerSettings\|AgentSettings\|CacheSettings\|POOL_TIMEOUT\|POOL_RECYCLE\|HTTP_EVENT" src/app src/tests --include="*.py"
# Confirm no print in the factory and override=False
grep -n "console.print\|override=" src/app/lib/settings.py
```
