# Flow: settings-ai-chat-web-log

*Beads: oracledb-vertexai-mzm.8*

## Specification

Absorbs old PRD Chapters 4 (AI/chat/cache) and 5 (web/log cleanup). Replaces the
sprawling `VertexAISettings` with a narrow `AISettings`, introduces a `ChatSettings`
that owns the chat-workflow constants currently hardcoded in
`src/app/domain/chat/services/adk.py` and the products services, and prunes the
remaining unread Vite/log knobs.

DEPENDS ON:
- flow `settings-audit-and-factory` (mzm.3) for the typed parser helpers, quiet
  immutable factory, and the `AgentSettings`/`CacheSettings` deletions whose live
  values land here as `ChatSettings`.
- a clean `adk.py` (mzm.6) so the rewire targets stable call sites; if mzm.6 has not
  landed, wire against the current `adk.py` line references below and re-baseline.

### Requirements

1. Replace `VertexAISettings` with `AISettings` exposing ONLY live fields:
   - `project_id` (env `VERTEX_AI_PROJECT_ID` or `GOOGLE_CLOUD_PROJECT`)
   - `location` (env `VERTEX_AI_LOCATION`/`GOOGLE_CLOUD_LOCATION`/`GOOGLE_LOCATION`,
     default `us-central1`)
   - `api_key` (env `VERTEX_AI_API_KEY` or `GOOGLE_API_KEY`)
   - `chat_model` (env `VERTEX_AI_CHAT_MODEL`, default `gemini-2.5-flash-lite`)
   - `intent_model_override` (env `VERTEX_AI_INTENT_MODEL`, default `None`)
   - `intent_model` derived property returning `intent_model_override or chat_model`
   - `embedding_model` (env `VERTEX_AI_EMBEDDING_MODEL`, default
     `gemini-embedding-2-preview`)
   - `embedding_dimensions` (default `3072`)
   `embedding_model`/`embedding_dimensions` stay explicit and separate because the
   Oracle `VECTOR(3072, FLOAT32)` schema depends on them.
   Preserve the project/api-key mutual-exclusivity handling (today in
   `VertexAISettings.__post_init__`, `settings.py:358-368`); relocate it so the
   factory stays effectively immutable — apply env mutation in a dedicated method
   (e.g. `configure_genai_env()`) called at startup, NOT during dataclass
   construction. Placeholder project IDs still resolve to a typed 503 via the
   existing `adk.py` credential guard.
2. Introduce `ChatSettings`:
   - `session_app_name` (default `coffee_assistant`) — replaces the hardcoded
     `_APP_NAME = "coffee_assistant"` in `adk.py:76`.
   - `response_cache_version` (default `menu-grounded-v1`) — replaces
     `_CHAT_CACHE_VERSION` in `adk.py:79`.
   - `response_cache_ttl_minutes` (default `60`) — replaces the hardcoded
     `ttl_minutes=60` in `adk.py:366`.
   - `product_search_limit` (default `5`) — replaces hardcoded `limit=5` defaults
     in the search tools.
   - `product_search_threshold` (default `0.7`) — replaces hardcoded
     `similarity_threshold=0.7` defaults.
   - `display_history_limit` (default `40`) — replaces the hardcoded `history[-40:]`
     in `adk.py:604`.
   WIRE these into `AgentToolsService` / `ADKRunner` / vector + explain defaults
   wherever `adk.py` and the products services currently hardcode them.
3. Type the embedding-cache read (symmetry with the response cache). Today
   `CacheService.get_cached_response` maps the full row to the `ResponseCache`
   struct, but `CacheService.get_embedding` returns a raw value and the
   `EmbeddingCache` struct (`system/schemas/_cache.py`) is never instantiated.
   The embedding-cache *feature* is fully live (`get_embedding`/`save_embedding`
   called from `products/services.py:279,295`; `invalidate_cache` clears both
   tables). To make the struct live (not dead) and symmetric with `ResponseCache`:
   - Widen the `get-cached-embedding` named query in `src/app/db/sql/system.sql`
     to select the full row (`id, text_hash, embedding, model, created_at,
     last_accessed, hit_count`) instead of only `embedding`.
   - Map it via `schema_type=EmbeddingCache` in `CacheService.get_embedding`,
     bump `hit_count`/`last_accessed` as today, and return `cached.embedding`.
   - This keeps the public method contract (`list[float] | None`) and the
     embedding-cache behavior identical; it only types the row.
   - `EMBEDDING_CACHE_ENABLED` is deleted as a dead knob (user-confirmed); it dies
     with `CacheSettings` in Ch3. The embedding cache stays unconditionally on — do
     NOT add a bypass branch in `get_text_embedding`.
4. Wire `CacheService.delete_expired_responses` into a cleanup path (user-confirmed:
   keep + wire, not delete). Make the method live by invoking it from a CLI command:
   extend `coffee clear-cache` (`cli/commands.py`) to also prune expired response-cache
   rows, or add a dedicated `coffee prune-cache` command. Surface the deleted-row count
   in the command output. Keep/extend the existing `test_cache.py` coverage to assert the
   method runs through the wired command.
5. Prune unread web/log knobs:
   - `ViteSettings.set_static_files`: 0 readers — there is no such method on the
     current `ViteSettings`; confirm and remove only if a stale reference exists.
   - `VITE_HOT_RELOAD` generation: 0 readers in `settings.py`/app — confirm it is
     not emitted by `.env` generation; if present, stop emitting it.
   - `LogSettings` fields NOT read by `config.py` or `_middleware.py`: only
     `HTTP_EVENT` is dead (already removed in mzm.3; do not re-add). Do NOT remove
     `EXCLUDE_PATHS`, `REQUEST_FIELDS`, `RESPONSE_FIELDS`, `OBFUSCATE_*`,
     `INCLUDE_COMPRESSED_BODY` — they are live via `_middleware.py`.
   - Optionally rename `ViteSettings` -> `WebAssetSettings`/`web` only if mzm.3's
     lower-case rename is accepted; otherwise leave the branch name as-is.
4. Acceptance behavior: `coffee model-info` still reports chat model, embedding
   model, project id, and embedding dimensions; cache TTL, search limit/threshold,
   and display-history length all come from `ChatSettings` with no duplicated
   hardcoded constants left in `adk.py` or the products services.
5. Project rules: dataclasses only; no compat shims or re-export of
   `VertexAISettings`; behavior-only docstrings; never log secrets/api-keys.

### Code Analysis Summary

- `src/app/lib/settings.py` `VertexAISettings` (lines 330-382): live fields
  `PROJECT_ID`, `LOCATION`, `API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`,
  `CHAT_MODEL`, `INTENT_MODEL`; dead fields `CACHE_TTL_SECONDS`, `CACHE_PREFIX`,
  `STREAM_BUFFER_SIZE`, `STREAM_TIMEOUT_SECONDS`. `__post_init__` mutates
  `os.environ` and nulls `API_KEY` when project mode is active.
- Live AI readers (these are the rewire targets):
  - `src/app/ioc.py:67-73` — `provide_genai_client` reads `PROJECT_ID`, `LOCATION`,
    `API_KEY`.
  - `src/app/ioc.py:85` — `provide_intent_classifier` reads
    `vertex_ai.INTENT_MODEL` (becomes `ai.intent_model`).
  - `src/app/ioc.py:121-125` — `provide_vertex_ai_service` reads `CHAT_MODEL`,
    `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`.
  - `src/app/cli/commands.py:118-121` — `model-info` reads `CHAT_MODEL`,
    `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` (and project).
  - `src/app/domain/chat/services/adk.py:386-387` — `_has_vertex_ai_backend_config`
    reads `PROJECT_ID`, `API_KEY`; `adk.py:527` `_build_workflow` reads `CHAT_MODEL`.
- Chat hardcodes to absorb into `ChatSettings`:
  - `adk.py:76` `_APP_NAME = "coffee_assistant"` — used in
    `Runner(app_name=...)` (1050) and every `_session_service` call
    (542, 547-549, 554, 575, 587).
  - `adk.py:79` `_CHAT_CACHE_VERSION = "menu-grounded-v1"` — used in
    `make_response_cache_key` (358).
  - `adk.py:366` `set_cached_response(..., ttl_minutes=60)`.
  - `adk.py:604` `state[_DISPLAY_HISTORY_STATE_KEY] = history[-40:]`.
  - search-limit/threshold defaults `limit: int = 5`, `similarity_threshold: float
    = 0.7` in `AgentToolsService.search_products_by_vector` (142) and the
    closure-bound tool (432); products service mirrors `0.7`/`5`
    (`products/services/services.py:86`).
- Web/log:
  - `ViteSettings` (lines 417-455): `DEV_MODE`, `BUNDLE_DIR`, `get_config()`. No
    `set_static_files` method exists today; `get_config()` hardcodes `asset_url`.
  - `config.py` reads only `log.LEVEL`, `log.SQLSPEC_LEVEL`, `log.GRANIAN_*`.
    `_middleware.py` reads the extraction fields. Only `HTTP_EVENT` was dead.
- Existing tests: `test_vertex_embedding_defaults_match_schema_contract`,
  `test_vite_config_uses_resources_as_frontend_root` reference
  `VertexAISettings`/`ViteSettings` directly and must be updated to the new shape.

## Implementation Plan

### Phase 1: Lock current AI/chat behavior with tests

- [ ] 1.1 In `src/tests/unit/app/lib/test_settings.py`, add `test_ai_settings_defaults`:
      `AISettings()` exposes `chat_model=gemini-2.5-flash-lite`,
      `embedding_model=gemini-embedding-2-preview`, `embedding_dimensions=3072`,
      and `intent_model == chat_model` when `intent_model_override is None`.
- [ ] 1.2 Add `test_intent_model_override_wins`: with
      `VERTEX_AI_INTENT_MODEL=gemini-x`, `intent_model == "gemini-x"`.
- [ ] 1.3 Add `test_chat_settings_defaults`: `session_app_name=coffee_assistant`,
      `response_cache_version=menu-grounded-v1`, `response_cache_ttl_minutes=60`,
      `product_search_limit=5`, `product_search_threshold=0.7`,
      `display_history_limit=40`.
- [ ] 1.4 In `src/tests/unit/app/domain/chat/services/test_adk.py`, add a
      regression asserting the response-cache write TTL and the display-history
      truncation length come from `ChatSettings` (will be RED until wired).
- [ ] 1.5 Run; confirm new chat-wiring tests RED, settings-shape tests describe the
      target. Record RED list in Beads note.

### Phase 2: AISettings

- [ ] 2.1 Add `AISettings` dataclass to `settings.py` with the fields and derived
      `intent_model` property in Requirement 1; replace `Settings.vertex_ai:
      VertexAISettings` with `Settings.ai: AISettings`.
- [ ] 2.2 Move the project/api-key env mutation out of `__post_init__` into an
      explicit `configure_genai_env()` (or fold into `setup_litestar_env()`'s
      startup path) so the dataclass stays immutable; preserve placeholder-project
      503 behavior.
- [ ] 2.3 Delete the four dead Vertex fields (if mzm.3 has not already) and
      `VertexAISettings` itself; no re-export.
- [ ] 2.4 Update `src/tests/unit/app/lib/test_settings.py`
      (`test_vertex_embedding_defaults_match_schema_contract` -> `AISettings`).

### Phase 3: Rewire AI readers

- [ ] 3.1 `src/app/ioc.py`: `provide_genai_client` -> `settings.ai.project_id/
      location/api_key`; `provide_intent_classifier` -> `settings.ai.intent_model`;
      `provide_vertex_ai_service` -> `settings.ai.chat_model/embedding_model/
      embedding_dimensions`.
- [ ] 3.2 `src/app/cli/commands.py:118-121`: `model-info` -> `settings.ai.*`.
- [ ] 3.3 `src/app/domain/chat/services/adk.py`: `_has_vertex_ai_backend_config`
      (386-387) and `_build_workflow` (527) -> `settings.ai.project_id/api_key/
      chat_model`.

### Phase 4: ChatSettings + wire chat constants

- [ ] 4.1 Add `ChatSettings` dataclass and `Settings.chat` field with the
      Requirement 2 fields/defaults.
- [ ] 4.2 In `adk.py`, replace `_APP_NAME` (76) usages with
      `get_settings().chat.session_app_name` (or inject via `ADKRunner.__init__`);
      replace `_CHAT_CACHE_VERSION` (79/358) with `chat.response_cache_version`;
      replace `ttl_minutes=60` (366) with `chat.response_cache_ttl_minutes`;
      replace `history[-40:]` (604) with `history[-chat.display_history_limit:]`.
- [ ] 4.3 Wire `chat.product_search_limit`/`product_search_threshold` as the
      default limit/threshold in `AgentToolsService.search_products_by_vector` (142)
      and the closure-bound `search_products_by_vector` tool (432); align the
      products service default in `products/services/services.py:86` so there is a
      single source. Leave the deliberate vector-fallback `0.6`/`limit=1` in
      `find_stores_with_product` (318-320) as an explicit local constant unless the
      flow decides to surface it (it is not in scope per the task).
- [ ] 4.4 Re-run Phase 1 tests; 1.3 and 1.4 turn GREEN.

### Phase 5: Prune web/log knobs

- [ ] 5.1 Confirm via grep there is no `ViteSettings.set_static_files` reader and no
      `VITE_HOT_RELOAD` generation; remove any stale reference if found.
- [ ] 5.2 Confirm `LogSettings` retains only fields read by `config.py` +
      `_middleware.py`; `HTTP_EVENT` already removed in mzm.3. No further LogSettings
      deletion.
- [ ] 5.3 If mzm.3's lower-case rename was accepted, rename `ViteSettings` ->
      `WebAssetSettings`/`web` and update `config.py:242`
      (`settings.vite.get_config()`) and `test_vite_config_*`; otherwise leave as-is.

### Phase 6: Verify

- [ ] 6.1 `uv run pytest src/tests/unit/app/lib` and the chat adk unit tests pass.
- [ ] 6.2 `coffee model-info` reports chat model, embedding model, project, and
      dimensions from `AISettings`.
- [ ] 6.3 `make lint` passes; `git diff --check` clean.

## Acceptance

- [ ] `VertexAISettings` is replaced by `AISettings` with `project_id`, `location`,
      `api_key`, `chat_model`, `intent_model_override`, derived `intent_model`,
      `embedding_model`, `embedding_dimensions`; no dead Vertex cache/stream fields
      remain; no re-export shim.
- [ ] `intent_model` returns the override when set, else `chat_model`.
- [ ] Project/api-key mutual exclusivity and placeholder-project 503 behavior
      preserved without mutating env during dataclass construction.
- [ ] `ChatSettings` exists and is wired: `session_app_name`,
      `response_cache_version`, `response_cache_ttl_minutes`,
      `product_search_limit`, `product_search_threshold`, `display_history_limit`.
- [ ] `adk.py` no longer hardcodes `_APP_NAME`, `_CHAT_CACHE_VERSION`,
      `ttl_minutes=60`, `history[-40:]`, or duplicate `limit=5`/`threshold=0.7`
      defaults — all sourced from `ChatSettings`.
- [ ] `coffee model-info` still reports chat/embedding/project/dimensions.
- [ ] Search limit/threshold, cache TTL, and display-history length are not
      duplicated between settings and service constants.
- [ ] No unread Vite/log knob remains; live `_middleware.py` log fields retained.

## Verification

```bash
uv run pytest src/tests/unit/app/lib src/tests/unit/app/domain/chat/services/test_adk.py
make lint
git diff --check
```

```bash
# Confirm chat constants are no longer hardcoded
grep -n "_APP_NAME\|_CHAT_CACHE_VERSION\|ttl_minutes=60\|history\[-40:\]\|= 0.7\|= 5\b" src/app/domain/chat/services/adk.py
# Confirm AI readers use the new shape
grep -rn "settings.ai\.\|vertex_ai\." src/app/ioc.py src/app/cli/commands.py src/app/domain/chat/services/adk.py
```
