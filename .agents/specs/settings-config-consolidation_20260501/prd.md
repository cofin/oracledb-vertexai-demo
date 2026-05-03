# Master PRD: Settings and Configuration Consolidation

*PRD ID: `settings-config-consolidation_20260501`*
*Created: 2026-05-01*
*Status: Draft for user review - planning only*
*Beads: not created - review gate before implementation*

---

## North Star

Reduce `src/app/lib/settings.py` from an accumulated set of future knobs,
duplicated runtime concepts, and partially wired dataclasses into a small,
typed configuration contract that reflects what the app actually uses.

The end state should make it obvious where each runtime decision lives:

- Oracle connection, SQLSpec extension, fixture, and migration settings.
- Litestar app, session, CORS, CSRF, template, and static asset settings.
- Google AI credential and model settings.
- Chat workflow, ADK namespace, product RAG defaults, history, and cache policy.
- Logging levels and warning suppression.
- Optional maps/embed settings only when the maps chapters need them.

This PRD is a planning artifact only. Source changes remain out of scope until
the review is accepted.

---

## Current State Reviewed

Reviewed live code on 2026-05-01:

- `src/app/lib/settings.py`
- `src/app/config.py`
- `src/app/server/plugins.py`
- `src/app/server/core.py`
- `src/app/server/asgi.py`
- `src/app/ioc.py`
- `src/app/domain/chat/services/adk.py`
- `src/app/domain/products/services/services.py`
- `src/app/domain/system/services/services.py`
- `src/app/cli/_helpers/*.py`
- `tools/lib/utils.py`
- `tools/oracle/database.py`
- `tools/oracle/connection.py`
- `README.md`
- existing specs that mention settings or pending maps settings

The repo already uses the Litestar-friendly pattern of dataclasses plus a
cached `Settings.from_env()` factory. The issue is not the pattern itself. The
issue is that `settings.py` now mixes:

- actively wired runtime settings
- unused settings branches
- constants that should belong to chat/domain code
- `.env` generation concerns owned by tools
- side-effectful env mutation during settings construction
- historical future-feature knobs that are not implemented

---

## Live Usage Findings

### Actively used settings

These settings are live and should remain, though some should move or be
renamed:

| Current surface | Live users | Notes |
|---|---|---|
| `settings.db.create_config()` | `src/app/config.py` | Central SQLSpec Oracle config path. Keep it, but narrow unused pool fields. |
| `settings.db.FIXTURE_PATH` | fixture load/export helpers and integration tests | Keep as data path config, probably lower-case. |
| `settings.app.DEBUG` | app factory and CSRF enablement | Keep. |
| `settings.app.SECRET_KEY` | CSRF config | Keep and fail early if missing outside local dev. |
| `settings.app.ALLOWED_CORS_ORIGINS` | CORS config | Keep, but parse without mutating a non-frozen dataclass. |
| `settings.app.CSRF_*` | CSRF config | Keep. |
| `settings.log.LEVEL`, `SQLSPEC_LEVEL`, `GRANIAN_*_LEVEL` | logging config | Keep. |
| `settings.vertex_ai.PROJECT_ID`, `LOCATION`, `API_KEY` | GenAI client and credential guard | Keep, but stop mutating global env from `__post_init__` if possible. |
| `settings.vertex_ai.CHAT_MODEL` | `VertexAIService`, ADK `LlmAgent`, `coffee model-info` | Keep as primary generation model. |
| `settings.vertex_ai.INTENT_MODEL` | `FlashLiteIntentClassifier` | Consolidate to optional override, not a required second model knob. |
| `settings.vertex_ai.EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` | embedding service and CLI | Keep separate because dimensions are coupled to Oracle `VECTOR(3072)`. |
| `settings.vite.get_config()` | Litestar Vite plugin | Keep, with focused tests. |

### Settings branches with no live reads

`rg` found no production reads of these top-level settings branches:

| Current surface | Recommendation |
|---|---|
| `settings.server` / `ServerSettings` | Remove from `Settings` unless `coffee run` will actually use it. The Granian/Litestar CLI env path already owns host/port/reload options. |
| `settings.agent` / `AgentSettings` | Replace with a smaller `ChatSettings` only for values the chat workflow actually consumes. |
| `settings.cache` / `CacheSettings` | Fold into `ChatSettings` or wire it directly. Current cache TTL settings are not used. |

### Field-level unused or drifted settings

These fields appear unused or misleading today:

| Current field | Evidence / concern | Recommendation |
|---|---|---|
| `DatabaseSettings.POOL_TIMEOUT` | Defined but not passed to `OracleAsyncConfig`. | Remove unless SQLSpec/oracledb supports the exact kwarg and tests prove it is wired. |
| `DatabaseSettings.POOL_RECYCLE` | Defined but not passed to `OracleAsyncConfig`. | Same as above. |
| `ServerSettings.APP_LOC` | Value is `app.asgi:app`, but actual app path is `app.server.asgi:create_app`; class is unused. | Delete with `ServerSettings`. |
| `LogSettings.EXCLUDE_PATHS` | Logging middleware config hardcodes request/response fields and does not read this. | Remove or wire intentionally. Default recommendation: remove. |
| `LogSettings.HTTP_EVENT`, `INCLUDE_COMPRESSED_BODY`, `OBFUSCATE_*`, `REQUEST_FIELDS`, `RESPONSE_FIELDS` | No live reads. | Remove unless the logging config is changed to consume them. |
| `AppSettings.URL` | No live reads. | Remove unless a maps/link feature needs a base URL. Do not keep as a future knob. |
| `VertexAISettings.CACHE_TTL_SECONDS`, `CACHE_PREFIX` | No context-cache implementation was found. | Remove until context caching exists. |
| `VertexAISettings.STREAM_BUFFER_SIZE`, `STREAM_TIMEOUT_SECONDS` | No live reads in the ADK streaming path. | Remove or wire after measuring a real need. |
| `AgentSettings.INTENT_THRESHOLD` | Class unused; classifier path does not read it. | Remove or move to `ChatSettings` only if classifier uses confidence. |
| `AgentSettings.VECTOR_SEARCH_*` | Class unused; tools and vector services hardcode defaults. | Move live defaults to `ChatSettings` and wire the tools. |
| `AgentSettings.CONVERSATION_HISTORY_LIMIT` | Class default is 10, ADK display history keeps the last 40 messages. | Move to `ChatSettings.display_history_limit` and wire it. |
| `AgentSettings.SESSION_EXPIRE_HOURS` | No live read; ADK sessions are managed by SQLSpec session service. | Remove unless session expiration is implemented. |
| `CacheSettings.RESPONSE_TTL_MINUTES` | Default is 5, but chat response cache writes with `ttl_minutes=60`. | Replace with `ChatSettings.response_cache_ttl_minutes` and wire. |
| `CacheSettings.EMBEDDING_CACHE_ENABLED` | Embedding cache is always used. | Remove or wire as a real bypass in `VertexAIService`. |
| `ViteSettings.set_static_files` | No live read. | Remove unless litestar-vite integration needs it. |
| `VITE_HOT_RELOAD` in generated/test env | `settings.py` does not read it. | Stop generating it or map it to `VITE_DEV_MODE`/lifespan semantics. |

### Duplicated concepts

1. App name appears in multiple places:
   - `AppSettings.NAME = "app"` drives OpenAPI title and `LITESTAR_APP_NAME`.
   - `src/app/domain/chat/services/adk.py` hardcodes `_APP_NAME = "coffee_assistant"` for ADK sessions.
   - The user-facing product is "Cymbal Coffee".

   Recommendation: decide on explicit names:
   - `app.service_name`: internal Litestar/service name.
   - `app.display_name`: OpenAPI/UI title if needed.
   - `chat.session_app_name`: ADK session namespace, only if it must differ.

2. Google model names are split:
   - `CHAT_MODEL` is used by the app LLM and `VertexAIService`.
   - `INTENT_MODEL` is used by the classifier.
   - Both currently default to `gemini-2.5-flash-lite`.

   Recommendation: keep one primary `ai.chat_model`, add
   `ai.intent_model_override: str | None = None`, and expose an
   `ai.intent_model` property that returns the override or `chat_model`.
   This preserves the ability to use a cheaper classifier model without forcing
   every local config to carry two model names.

3. Cache settings exist separately from chat behavior:
   - response cache TTL is hardcoded in `AgentToolsService`
   - embedding cache enablement is a setting but not wired

   Recommendation: put chat response cache policy under `ChatSettings`, and
   only keep an embedding-cache setting if the implementation actually bypasses
   cache reads/writes.

4. Database env parsing exists in both app settings and tools:
   - `DatabaseSettings` builds SQLSpec config.
   - `tools/oracle/connection.py` has its own `ConnectionConfig.from_env()`.
   - `tools/oracle/database.py` has a separate container `DatabaseConfig`.
   - `tools/lib/utils.py` writes `.env` values by hand.

   Recommendation: keep container lifecycle settings separate, but share or
   mirror one app connection env contract across `DatabaseSettings`,
   `ConnectionConfig`, and `.env` generation.

---

## Product Decisions

1. Stay on dataclasses plus cached settings. Do not introduce
   `pydantic-settings` for this cleanup; the repo does not currently depend on
   Pydantic for config.
2. Make settings objects immutable or effectively immutable. Use lower-case
   field names and typed parser helpers instead of upper-case mutable
   dataclass attributes.
3. Make shell environment variables win over `.env` values. Current
   `load_dotenv(..., override=True)` caused earlier local override confusion;
   the implementation should switch to `override=False` unless review rejects
   that behavior change.
4. Stop printing from settings construction. CLI commands may print that config
   was loaded, but the settings factory should be quiet and testable.
5. Keep one app settings module. Do not scatter environment parsing across
   handlers or services.
6. Keep `src/app/config.py` and `src/app/server/plugins.py` lazy materialization
   unless implementation finds a simpler path that does not reintroduce
   import-time I/O.
7. Remove future-feature settings until the feature exists. Optional maps
   settings belong in the maps/security chapter implementation, not in
   settings ahead of use.
8. Preserve the public env names that are already documented and used:
   `DATABASE_*`, `WALLET_*`, `TNS_ADMIN`, `SECRET_KEY`, `LITESTAR_DEBUG`,
   `VERTEX_AI_*`, `GOOGLE_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `VITE_*`, and
   `ASSET_URL`.
9. Standardize generated env output around `GOOGLE_CLOUD_PROJECT` or
   `VERTEX_AI_PROJECT_ID`; do not emit a separate `GOOGLE_PROJECT_ID` unless
   the app settings explicitly support it.
10. Do not reduce current runtime behavior while cleaning settings. This is a
    refactor and contract cleanup, not a feature rewrite.

---

## Target Settings Shape

Recommended target:

```text
Settings
  app: AppSettings
    service_name
    display_name
    debug
    secret_key
    allowed_cors_origins
    csrf_cookie_name
    csrf_header_name
    csrf_cookie_secure

  database: DatabaseSettings
    url
    wallet_password
    wallet_location
    user
    password
    host
    port
    service_name
    dsn
    pool_min_size
    pool_max_size
    migration_path
    fixture_path
    adk_enable_memory
    adk_in_memory
    litestar_session_in_memory

  ai: AISettings
    project_id
    location
    api_key
    chat_model
    intent_model_override
    intent_model  # derived property
    embedding_model
    embedding_dimensions

  chat: ChatSettings
    session_app_name
    response_cache_version
    response_cache_ttl_minutes
    product_search_limit
    product_search_threshold
    display_history_limit

  web: WebAssetSettings
    dev_mode
    use_server_lifespan
    host
    port
    bundle_dir
    asset_url
    trusted_proxies

  logging: LoggingSettings
    level
    sqlspec_level
    granian_access_level
    granian_error_level
```

Potential future maps shape, only when the maps/security chapter implements it:

```text
maps: MapsSettings
  enable_embed
  embed_api_key
```

---

## Roadmap

### Chapter 1 - `settings-contract-audit_20260501`

Lock down the current settings contract before refactoring.

Deliverables:

- Add `src/tests/unit/app/lib/test_settings.py` for settings parser and factory
  behavior.
- Add focused assertions for:
  - `.env` loading and shell-env precedence.
  - bool parsing for common true/false spellings.
  - `ALLOWED_CORS_ORIGINS` JSON-list and comma-list parsing.
  - `SECRET_KEY` behavior in local/test environments.
  - `DatabaseSettings.create_config()` local and wallet modes.
  - `Settings.from_env.cache_clear()` or replacement reset behavior.
- Add a simple static/settings inventory test or script assertion that flags
  top-level settings branches with no non-test consumers.
- Capture a short inventory note in `progress.md` after implementation starts.

Acceptance:

- A failing test exists for at least one known drift item, such as
  `CACHE_RESPONSE_TTL_MINUTES` not affecting chat response cache TTL or shell
  env not winning over `.env`.
- Tests use the current module-path layout.
- No production settings behavior changes are made before the tests exist.

### Chapter 2 - `settings-core-factory_20260501`

Clean the settings factory and core dataclass style.

Deliverables:

- Convert settings field names to lower-case internal attributes, updating all
  app call sites in one focused pass.
- Make settings immutable or effectively immutable.
- Replace ad hoc `os.getenv(...) in TRUE_VALUES` checks with small typed parser
  helpers.
- Replace `AppSettings.__post_init__` mutation with parse-time conversion.
- Stop printing from `Settings.from_env()`.
- Change dotenv loading so shell env overrides `.env`, unless review rejects
  that decision.
- Keep a single cached `get_settings()` path and one documented reset hook for
  tests.

Acceptance:

- Settings objects cannot be accidentally mutated by handlers/services.
- `get_settings()` remains cached and resettable in tests.
- Shell overrides like `VITE_DEV_MODE=False` can override `.env` values.
- `make lint` passes for the settings module and updated call sites.

### Chapter 3 - `settings-database-env-contract_20260501`

Make Oracle database settings and tooling share one env contract.

Deliverables:

- Keep SQLSpec app connection settings in `DatabaseSettings`.
- Remove or wire unused pool settings (`POOL_TIMEOUT`, `POOL_RECYCLE`) after
  checking SQLSpec/oracledb supported config keys.
- Keep SQLSpec extension flags that are genuinely used:
  `ADK_ENABLE_MEMORY`, `ORACLE_ADK_IN_MEMORY`, and
  `ORACLE_LITESTAR_SESSION_IN_MEMORY`.
- Align `DatabaseSettings`, `tools/oracle/connection.py`, and
  `tools/lib/utils.py` on the same env variable names and defaults.
- Keep Oracle container lifecycle config separate from app connection config.
- Normalize service name casing where practical (`freepdb1` vs `FREEPDB1`) only
  if existing tests and Oracle connections remain valid.

Acceptance:

- App startup, `coffee load-fixtures`, and `manage.py database upgrade` resolve
  the same connection env contract.
- Wallet/autonomous connection behavior is preserved.
- No unused database pool knob remains in settings.
- Relevant tests under `src/tests/unit/app/lib/` and
  `src/tests/integration/tools/oracle/` pass.

### Chapter 4 - `settings-ai-chat-cache_20260501`

Consolidate AI, chat, agent, and cache settings around actual runtime behavior.

Deliverables:

- Replace `VertexAISettings` with `AISettings` or narrow it to only live AI
  fields.
- Keep `embedding_model` and `embedding_dimensions` separate from chat model
  settings because Oracle vector schema depends on them.
- Replace the mandatory `INTENT_MODEL` setting with an optional classifier
  override whose default resolves to `chat_model`.
- Introduce `ChatSettings` for:
  - ADK session app namespace.
  - response cache version.
  - response cache TTL.
  - product vector search limit.
  - product vector search threshold.
  - display history limit.
- Wire chat defaults into `AgentToolsService`, `ADKRunner`, and vector/explain
  defaults where the app currently hardcodes them.
- Remove `AgentSettings` and `CacheSettings` after the live values are moved or
  deleted.
- Remove unused context-cache and stream settings unless implementation wires
  them to actual behavior.

Acceptance:

- `coffee model-info` still reports the active chat, embedding, project, and
  dimension settings.
- `VERTEX_AI_INTENT_MODEL` remains optional compatibility if kept, but local
  config does not need both chat and intent model entries when they are the
  same.
- `CACHE_RESPONSE_TTL_MINUTES` either works through the new chat setting or is
  no longer documented/generated.
- Search limit, threshold, and display history length are not duplicated between
  settings and hardcoded service constants.

### Chapter 5 - `settings-web-log-cleanup_20260501`

Prune web/server/logging settings and keep the actual plugin wiring obvious.

Deliverables:

- Delete `ServerSettings` or wire it into `coffee run`; default recommendation
  is deletion because Granian/Litestar CLI options own host/port/runtime flags.
- Remove `VITE_HOT_RELOAD` from generated/test env files if it remains unused.
- Keep `ViteSettings.get_config()` behavior, but rename the settings branch to
  `web` or `assets` if the review accepts lower-case renaming.
- Remove unused `ViteSettings.set_static_files` if no plugin consumes it.
- Reduce `LogSettings` to fields actually read by `src/app/config.py`, or wire
  the extra logging fields intentionally.
- Preserve current warning filters in `src/app/config.py` unless a cleaner log
  module home is chosen.

Acceptance:

- `src/tests/unit/app/test_vite_settings.py` or its renamed module still covers
  template mode, asset URL fallback, trusted proxies, and lifespan flag.
- `rg "VITE_HOT_RELOAD"` returns no app-owned generated/test env use, or the
  setting is deliberately wired and tested.
- No unused logging settings remain.
- App creation still wires CORS, CSRF, sessions, template config, Vite, HTMX,
  flash, SQLSpec, and structlog plugins.

### Chapter 6 - `settings-docs-verification_20260501`

Update docs, generated env templates, and verification gates.

Deliverables:

- Update README troubleshooting and `coffee model-info` output if model/env
  names change.
- Update `tools/lib/utils.py` `.env` generation to match the final settings
  contract.
- Update test fixtures in `src/tests/conftest.py`.
- Search all specs/docs for old setting names and revise only current planning
  artifacts that would mislead implementation.
- Run focused settings tests, then repo verification.

Acceptance:

- `uv run pytest src/tests/unit/app/lib src/tests/unit/app/test_vite_settings.py`
  passes, adjusted for any renamed test path.
- `uv run pytest src/tests/unit/app/test_ioc.py src/tests/integration/app/server/test_static_assets.py`
  passes if touched by settings wiring.
- `make lint` passes.
- `make test` passes, or any remaining Oracle/environment dependency is
  documented with exact failure output.
- `git diff --check` passes.

---

## Implementation Constraints

1. Do not add a new settings framework.
2. Do not read `os.environ` from handlers or request-scoped services except
   through `get_settings()`.
3. Do not keep settings for future features unless the same implementation
   wires and tests the feature.
4. Do not move Oracle container lifecycle config into app runtime settings.
5. Do not remove the ability to use either Vertex project credentials or API-key
   credentials.
6. Do not log secrets, API keys, wallet passwords, or full connection URLs.
7. Do not change database schema in this cleanup.
8. Do not add maps embed settings until maps embed support is implemented.
9. Keep source changes grouped by chapter so review can separate contract,
   database, AI/chat, and web/logging cleanup.
10. Preserve Flow test-layout rules: add tests under module-path homes, not new
    top-level issue buckets.

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Renaming uppercase fields creates broad churn | Do it in one chapter with focused tests and `rg` checks for old names. |
| Shell-env precedence change surprises local users | Call it out in README/CLI docs and cover with a test. |
| Removing unused settings hides a planned feature | Check active specs first; keep only settings tied to accepted implementation chapters. |
| Vertex/API-key behavior regresses | Add tests for project mode, API-key mode, and placeholder project guard behavior. |
| Database env consolidation breaks tools | Keep container config separate and extend existing `tools/oracle` tests. |
| Immutability breaks tests that mutate nested settings | Update tests to construct replacement settings objects or monkeypatch `get_settings()`. |

---

## Review Defaults

Unless review changes these decisions, implementation should proceed with these
defaults:

1. Use dataclasses, not Pydantic.
2. Use lower-case field names internally.
3. Make shell env override `.env`.
4. Remove `ServerSettings`.
5. Replace `AgentSettings` and `CacheSettings` with `ChatSettings`.
6. Keep one primary chat model plus optional intent-model override.
7. Keep embedding model and dimensions as their own explicit AI settings.
8. Remove settings that remain unwired after the cleanup.
