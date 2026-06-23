# Master PRD: SQLSpec ADK 2 Branch Migration

*PRD ID: `adk2-sqlspec-migration`*
*Beads: `oracledb-vertexai-6uc`*
*Created: 2026-06-23*
*Status: Draft - implementation not started*

---

## North Star

Move Cymbal Coffee onto SQLSpec's ADK 2 store contract while the upstream
SQLSpec work is still open in `litestar-org/sqlspec#525`, preserve the demo's
Oracle-backed ADK sessions, and update the default lightweight Gemini model to
`gemini-3.1-flash-lite`.

The migration must be branch-aware: if `litestar-org/sqlspec#525` has not
merged and no release contains it, this app must resolve SQLSpec from the open
branch in `pyproject.toml` through uv. Once SQLSpec merges and releases the ADK
2 store contract, the temporary branch source must be removed and replaced with
the released requirement.

---

## Reviewed Sources

### Local planning inputs

- `.agents/specs/adk2-sqlspec-migration/source-plan.md` - moved from
  `.agents/plans/ADK2.md`; useful as an older migration sketch but superseded by
  this PRD.
- `.agents/specs/adk2-sqlspec-migration/source-branch-notes.md` - moved from
  `docs/ADK.md`; useful branch-specific notes but not public docs.

### Live upstream state

- SQLSpec PR: <https://github.com/litestar-org/sqlspec/pull/525>
- PR title: `feat(adk): align stores with ADK 2 contract`
- PR state on 2026-06-23: open, unmerged, mergeable, not draft.
- PR head: `feat/adk-2.0.0-updates`
- PR head SHA: `09269e27b632bd590f9509aafc4ae842dc225f9d`
- Local SQLSpec checkout: `/home/cody/code/litestar/sqlspec` on
  `feat/adk-2.0.0-updates`, same head SHA.

### External docs

- uv dependency sources: <https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-sources>
  - `tool.uv.sources` supports Git sources.
  - Branch form is `package = { git = "...", branch = "..." }`.
  - Sources are uv-only and ignored by non-uv tooling.
- Gemini model reference: <https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite>
  - Stable model code is `gemini-3.1-flash-lite`.
  - The model supports function calling and structured outputs, which this app
    needs for classifier output and Product RAG selection.

### Current app surfaces

- `pyproject.toml`
  - Currently pins `sqlspec[adk,mypyc,oracledb,performance]==0.50.0`.
  - Currently requires `google-adk>=2.0.0`.
- `src/app/lib/settings.py`
  - `AISettings.chat_model` defaults to `gemini-2.5-flash-lite`.
  - `AISettings.intent_model` falls back to `chat_model` unless
    `VERTEX_AI_INTENT_MODEL` is set.
  - `DatabaseSettings.create_config()` still overrides ADK table names to
    `adk_sessions`, `adk_events`, and `adk_memory_entries`.
- `src/app/domain/chat/services/classifier.py`
  - `FlashLiteIntentClassifier` default constructor model and docstring name
    `gemini-2.5-flash-lite`.
- `src/app/domain/chat/services/adk.py`
  - `_build_workflow()` builds `LlmAgent(... model=get_settings().ai.chat_model)`.
  - `_append_display_history()` reaches through
    `self._session_service.store.update_session_state(session_id, state)`, which
    is incompatible with SQLSpec PR #525.
- `src/app/ioc.py`
  - Provides `OracleAsyncADKStore(config=config)`.
  - Does not currently provide `OracleAsyncADKMemoryStore`.
- `src/tests/...`
  - Unit and integration tests pin the old 2.5 model name and the old
    2-argument ADK store state update.

---

## Product Decisions

1. **Use the SQLSpec branch while PR #525 is open.** Because the PR is open and
   unmerged as of 2026-06-23, implementation must use uv's Git branch source for
   `sqlspec` instead of pretending the feature is on SQLSpec `main` or PyPI.
2. **Keep the app uv-managed for this migration.** uv branch sources live in
   `[tool.uv.sources]` and are not portable package metadata. That is acceptable
   because this repository already uses uv for install, lock, and run commands.
3. **Make `gemini-3.1-flash-lite` the default chat and classifier model.**
   `VERTEX_AI_CHAT_MODEL` and `VERTEX_AI_INTENT_MODEL` remain the override
   escape hatches; the default only changes when env vars are absent.
4. **Prefer ADK service APIs over SQLSpec store reach-through.**
   `_append_display_history()` should write display-history state through
   `SQLSpecSessionService.append_event(session, Event(... state_delta=...))`.
   The 4-argument store `update_session_state(app_name, user_id, session_id,
   state)` is an acceptable fallback only if tests prove the extra display
   event breaks required behavior.
5. **Treat ADK schema reset as destructive and acceptable for the demo.**
   SQLSpec PR #525 ships `0002_reset_adk_tables.py`, which drops legacy ADK
   session/event/memory tables and recreates the clean-break schema. Cymbal
   Coffee chat sessions are ephemeral, so no export path is required.
6. **Remove legacy ADK table-name overrides unless a test proves they are
   needed.** The clean-break SQLSpec defaults are `adk_session`, `adk_event`,
   `adk_app_state`, `adk_user_state`, `adk_internal_metadata`, and `adk_memory`.
   Keeping plural overrides is valid but makes the reference app less aligned
   with SQLSpec's default contract.
7. **Do not add fake order-memory behavior.** The older source plan's "agent
   remembers past orders" section is aspirational and conflicts with the current
   product rule that `ORDER_STATUS` is explicit but unsupported until order data
   exists. This PRD may wire memory-store infrastructure, but it must not invent
   order persistence or order recall.

---

## Roadmap

### Chapter 1 - `adk2-dependency-source`

*Beads: `oracledb-vertexai-6uc.1`*

Make dependency resolution explicit and branch-correct.

**Implementation targets:**

- `pyproject.toml`
  - Replace the released SQLSpec pin with a source-resolved dependency:
    ```toml
    dependencies = [
        "sqlspec[adk,mypyc,oracledb,performance]",
        ...
    ]

    [tool.uv.sources]
    sqlspec = { git = "https://github.com/litestar-org/sqlspec", branch = "feat/adk-2.0.0-updates" }
    ```
  - Keep `google-adk>=2.0.0` unless live branch testing proves SQLSpec needs a
    higher lower-bound.
  - Do not use a raw direct-reference dependency string for SQLSpec; keep the
    source in `[tool.uv.sources]` so branch removal after release is localized.
- `uv.lock`
  - Refresh SQLSpec from the branch:
    `uv lock --upgrade-package sqlspec`.
  - Confirm the locked SQLSpec source resolves to commit
    `09269e27b632bd590f9509aafc4ae842dc225f9d` or a newer branch head if the PR
    advanced before implementation.
- `.agents/specs/adk2-sqlspec-migration/source-plan.md`
  - Add a top note that this file is a historical input and that
    `prd.md` is authoritative.
- `.agents/specs/adk2-sqlspec-migration/source-branch-notes.md`
  - Add a top note that this file is a historical input and that
    `prd.md` is authoritative.

**Acceptance:**

- `pyproject.toml` contains `[tool.uv.sources].sqlspec` pointing at
  `feat/adk-2.0.0-updates` while PR #525 is open.
- `uv lock --upgrade-package sqlspec` succeeds.
- `uv.lock` no longer resolves SQLSpec from PyPI `0.50.0` for the active app.
- The source notes are clearly marked superseded by this PRD.

---

### Chapter 2 - `adk2-store-contract`

*Beads: `oracledb-vertexai-6uc.3`*

Adapt Cymbal Coffee to SQLSpec's ADK 2 session, event, scoped-state, and memory
store contract.

**Implementation targets:**

- `src/app/lib/settings.py`
  - In `DatabaseSettings.create_config().extension_config["adk"]`, remove
    `session_table`, `events_table`, and `memory_table` overrides unless the
    implementation intentionally chooses plural legacy names.
  - If memory remains enabled, add only supported SQLSpec branch settings:
    `memory_use_fts` and `memory_max_results` if the app needs non-defaults.
  - Keep `ORACLE_ADK_IN_MEMORY` for Oracle INMEMORY DDL.
- `src/app/ioc.py`
  - Prefer imports from `sqlspec.adapters.oracledb.adk`:
    `OracleAsyncADKStore`.
  - Add `OracleAsyncADKMemoryStore` only if a concrete app path consumes it.
    Do not provide an unused singleton just to mirror the old source plan.
- `src/app/domain/chat/services/adk.py`
  - Replace `_append_display_history()` private store reach-through with
    `SQLSpecSessionService.append_event(...)`:
    - Load the session with `get_session(app_name=..., user_id=..., session_id=...)`.
    - Build the truncated `display_history` payload in Python as today.
    - Create an ADK `Event` with `EventActions(state_delta=state_delta)`.
    - Include `intent` and `last_products` in the same state delta.
    - Use a synthetic system invocation id such as `display-{uuid.uuid4().hex}`.
  - If the service-path write introduces unacceptable extra event history in the
    UI, use the new store signature as a fallback:
    `await self._session_service.store.update_session_state(app_name, user_id, session_id, state)`.
    This fallback must be documented in the code review summary because it keeps
    the private `.store` dependency.
- `src/tests/unit/app/domain/chat/services/test_adk.py`
  - Replace assertions for `store.update_session_state(session_id, state)` with
    assertions against `append_event()` and `event.actions.state_delta`.
  - Preserve truncation assertions for `CHAT_DISPLAY_HISTORY_LIMIT`.
- `src/tests/integration/app/domain/chat/services/test_chat_workflow.py`
  - Ensure chat display history, `intent`, and `last_products` round-trip after a
    Product RAG turn under the branch SQLSpec service.

**Acceptance:**

- No app code calls 2-argument `update_session_state(session_id, state)`.
- Existing direct `get_session`, `create_session`, `delete_session`, and
  `append_event` call sites use ADK/SQLSpec service signatures compatible with
  PR #525.
- `event_json` does not appear in app code or app tests.
- Oracle ADK extension config either uses SQLSpec clean-break table defaults or
  documents why plural table overrides are retained.

---

### Chapter 3 - `gemini31-flash-lite-default`

*Beads: `oracledb-vertexai-6uc.4`*

Move default chat and intent classification from Gemini 2.5 Flash-Lite to Gemini
3.1 Flash-Lite.

**Implementation targets:**

- `src/app/lib/settings.py`
  - Change `AISettings.chat_model` default from `gemini-2.5-flash-lite` to
    `gemini-3.1-flash-lite`.
  - Keep `VERTEX_AI_CHAT_MODEL` override behavior unchanged.
  - Keep `AISettings.intent_model` as `intent_model_override or chat_model`.
- `src/app/domain/chat/services/classifier.py`
  - Change the constructor fallback model to `gemini-3.1-flash-lite`.
  - Update the docstring so it says "Flash-Lite" or the exact new model, not
    `gemini-2.5-flash-lite`.
- `src/tests`
  - Update model assertions in:
    - `src/tests/integration/app/domain/chat/services/test_chat_workflow.py`
    - `src/tests/unit/app/test_ioc_integrations.py`
    - `src/tests/unit/app/domain/chat/services/test_classifier.py`
    - `src/tests/unit/app/domain/chat/services/conftest.py`
    - `src/tests/unit/app/domain/chat/services/test_adk.py`
    - `src/tests/unit/app/domain/chat/services/test_adk_grounding.py`
    - `src/tests/unit/app/domain/products/services/test_vertex_ai_service.py`
  - Update cache-key digest expectations because the model string contributes to
    the cache key.
- `docs/` and `.agents/knowledge/`
  - Replace shipped default model references in active docs and durable guides.
  - Historical completed knowledge entries may keep old model names when they
    explicitly describe past work.
- `src/app/cli/commands.py`
  - `coffee model-info` should naturally print the new default through settings;
    add or update a focused test if one exists.

**Acceptance:**

- `rg -n "gemini-2\\.5-flash-lite" src docs .agents AGENTS.md README.md -g '!docs/_build/**'`
  returns only historical research/completed-flow references that are explicitly
  not current guidance.
- With no env override, `Settings.from_env().ai.chat_model` is
  `gemini-3.1-flash-lite`.
- With `VERTEX_AI_INTENT_MODEL` set, classifier still uses the override.
- Google GenAI calls for chat, structured Product RAG selection, and intent
  classification all receive the expected model string.

---

### Chapter 4 - `adk2-oracle-verification-release-cleanup`

*Beads: `oracledb-vertexai-6uc.2`*

Prove the migration on Oracle, then remove the temporary branch source after the
upstream SQLSpec PR merges and releases.

**Implementation targets:**

- Oracle lifecycle
  - Run `make start-infra`.
  - Run `uv run coffee upgrade`.
  - Confirm SQLSpec ADK extension migration `0002_reset_adk_tables.py` drops the
    legacy tables and recreates the chosen ADK schema.
- Runtime smoke
  - Run a chat round-trip through `/api/chat/stream`.
  - Confirm display history persists across turns.
  - Confirm `PRODUCT_RAG` stores `last_products` and later pronoun resolution
    still works.
  - Confirm `STORE_LOCATION` and `PRODUCT_AVAILABILITY` retain browser-location
    privacy and no-key Maps URL behavior.
- Tests
  - Focused first:
    - `uv run pytest src/tests/unit/app/domain/chat/services/test_adk.py`
    - `uv run pytest src/tests/unit/app/domain/chat/services/test_classifier.py`
    - `uv run pytest src/tests/unit/app/test_ioc_integrations.py`
    - `uv run pytest src/tests/integration/app/domain/chat/services/test_chat_workflow.py`
  - Aggregate gates before completion:
    - `make lint`
    - `make test`
- Release cleanup
  - If PR #525 is still open, leave `[tool.uv.sources].sqlspec` in place and
    record the PR URL/head SHA in the implementation summary.
  - If PR #525 has merged and a release contains the ADK 2 store contract, remove
    `[tool.uv.sources].sqlspec`, set the released SQLSpec requirement, and run
    `uv lock --upgrade-package sqlspec`.

**Acceptance:**

- `make lint` and `make test` pass.
- Oracle migration and fixture loading pass through `uv run coffee upgrade`.
- Chat display state persists on the SQLSpec ADK 2 contract.
- The final dependency state truthfully matches upstream:
  - branch source while PR #525 is open/unreleased, or
  - released SQLSpec requirement after merge/release.

---

## Global Constraints

- Do not modify production code while only performing PRD/planning work.
- Do not add compatibility shims for old SQLSpec ADK store signatures.
- Do not create demo-side ADK reset migrations; SQLSpec owns the extension
  migrations.
- Keep browser coordinates request-scoped and out of ADK state, cache, logs, and
  metrics.
- Final product names, prices, and descriptions remain Oracle-rendered in Python,
  even when Gemini structured output selects among retrieved candidates.
- Keep raw SQLSpec developer commands on `python manage.py database ...`; the
  packaged app migration command remains `uv run coffee upgrade`.

---

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| SQLSpec PR #525 advances after planning. | Re-read PR head and run `uv lock --upgrade-package sqlspec`; record the resolved commit. |
| Non-uv install path ignores `[tool.uv.sources]`. | This repo is uv-managed; document branch source as temporary and uv-only. |
| ADK reset drops local chat sessions. | Accept for demo; mention destructive reset in PR/release notes. |
| `append_event()` adds display-history events. | Prefer service correctness; if UI history becomes noisy, use the 4-arg store fallback and document the private-store tradeoff. |
| Gemini 3.1 model availability differs by project/region. | Keep `VERTEX_AI_CHAT_MODEL` and `VERTEX_AI_INTENT_MODEL` overrides; test configured project in `us-central1`. |
| Product RAG response cache contains old model answers. | Model string is part of the cache key; update digest tests and clear cache if manual verification needs a clean slate. |

---

## Open Questions

1. Should the implementation remove the plural ADK table overrides immediately,
   or keep them for one branch while using SQLSpec's new scoped-state tables?
   Recommended: remove overrides and use SQLSpec clean-break defaults.
2. Should ADK memory remain enabled by default when no runtime memory feature uses
   it yet?
   Recommended: keep migration support enabled only if it is already part of the
   reference schema story; do not wire user-facing order memory until order data
   exists.

---

## Completion Definition

This PRD is complete when the four chapters above are implemented or explicitly
split into high-definition worksheets, the app installs SQLSpec from the correct
source for the current upstream state, `gemini-3.1-flash-lite` is the default
model, Oracle migration succeeds, and the full app test gate passes.
