# Flow: chat-path-consolidation

*Beads: oracledb-vertexai-mzm.5*

## Specification

Retire the non-streaming chat path. The browser UI posts only to
`/api/chat/stream` (SSE) and `/api/chat/session/clear`; the legacy
`POST /api/chat` handler that returned HTMX partial HTML or JSON
`CoffeeChatReply` is unreached and is deleted along with everything that only
served it. After this chapter the chat surface is exactly two routes:
`chat.api.stream` and `chat.api.clear_session`.

Behavior of the streaming path is unchanged. This is a deletion-only chapter:
no new symbols, no shims, no re-exports (project rule: delete completely).

### Requirements

- Delete the `POST /api/chat` handler `send_chat_message`
  (`src/app/domain/chat/controllers/_chat.py:63-167`) and its only import that
  becomes unused (`metrics_badges`).
- Cascade-delete every symbol that has **no other caller** once the handler is
  gone (each re-verified by grep in Code Analysis Summary):
  - `ADKRunner.process_request` (`adk.py:1123-1158`) and the now-dead
    `_CHAT_RESULT_KEYS` constant (`adk.py:85-98`, used only by
    `process_request` at `adk.py:1146`).
  - `CoffeeChatReply` schema (`schemas/_chat.py:38-53`) plus its
    `schemas/__init__.py` import + `__all__` entry.
  - `metrics_badges` helper (`controllers/_helpers.py:37-48`).
- Delete dead Jinja partials and dead markup:
  - `partials/_chat_response.html.j2` (included only by the deleted handler).
  - `partials/_metrics_badges.html.j2` (included only by `_chat_response`).
  - `partials/chat_error.html.j2` (rendered only by the deleted handler at
    `_chat.py:85,108`).
  - The metrics `<footer>` block in `partials/message.html.j2:18-63` (the
    `{% if message.source == "ai" and metrics_badges is defined %}` block);
    keep the rest of `message.html.j2`.
- KEEP (still used by the stream handler / page-load history):
  - `validate_message`, `validate_persona` (static methods on
    `CoffeeChatController`), `chat_form_from_request`,
    `location_context_from_form` (and the `payload_*` / `location_text` helpers
    they depend on) — all consumed by `stream_chat_message`.
  - `ChatMessage` schema — used by `_adk_history.py` and
    `ADKRunner.get_history`.
  - `partials/message.html.j2` minus its footer — included by
    `pages/chat.html.j2:52` to render page-load history.
- Update tests: prune the `/api/chat` cases from integration `test_chat_http.py`
  (keep the `/api/chat/stream` + `/api/chat/session/clear` cases); remove the
  `process_request`-specific cases from unit `test_adk.py` and integration
  `test_chat_workflow.py`. The broader `test_adk.py` rewrite is owned by Ch10 —
  here only remove the now-dead `process_request` cases.
- Final grep proves zero references to `process_request`, `CoffeeChatReply`,
  `metrics_badges`, `_CHAT_RESULT_KEYS`, and the three deleted partials outside
  generated artifacts.

### Code Analysis Summary

Verified against current source on this branch.

**Handler is unreached by any client:**

- `templates/pages/chat.html.j2:74` — the chat form posts to
  `action="/api/chat/stream"`.
- `static/assets/main-BEAo4PUx.js` — submit handler posts to `t.action`
  (the stream URL); the only other fetch is `POST /api/chat/session/clear`.
- `grep '"/api/chat"'` (exact, non-stream) hits only the handler itself
  (`_chat.py`), the integration test, and generated
  `src/resources/generated/{openapi.json,routes.json}`. No external consumer.

**Cascade callers (each verified zero remaining app callers after the handler is removed):**

- `process_request` — app caller is only `_chat.py:96`. Other hits are tests
  (`test_chat_http.py`, `test_adk.py`, `test_chat_workflow.py`) and a
  doc/script reference `tools/scripts/lab.md:385` (non-executing markdown).
- `_CHAT_RESULT_KEYS` — defined `adk.py:85-98`, read only at `adk.py:1146`
  inside `process_request`. Dead once that method is gone.
- `CoffeeChatReply` — built only at `_chat.py:149`; declared in
  `schemas/_chat.py:38` and re-exported in `schemas/__init__.py:10,17`.
- `metrics_badges` — imported at `_chat.py:17`, called at `_chat.py:127`;
  defined `_helpers.py:37`. No other caller.

**Partial reference sites:**

- `_chat_response.html.j2` — `template_name` at `_chat.py:135` only; it
  `include`s `message.html.j2` (kept) and `_metrics_badges.html.j2` (deleted).
- `_metrics_badges.html.j2` — `include`d only by `_chat_response.html.j2:7`.
- `chat_error.html.j2` — rendered only by the deleted handler
  (`_chat.py:85,108`).
- `message.html.j2` — also `include`d by `chat.html.j2:52` (page-load history),
  so it stays; only its metrics footer (lines 18-63, gated on
  `metrics_badges is defined`) is removed. After removal `intent_detected` on
  the header (line 13-15) still renders for history bubbles unchanged.

**Stream path dependencies that must remain intact:**

- `stream_chat_message` (`_chat.py:170-217`) calls `chat_form_from_request`,
  `validate_message`, `validate_persona`, `location_context_from_form`,
  `adk_runner.ensure_configured`, and `adk_runner.stream_request`. None of these
  are touched.
- `clear_chat_session` (`_chat.py:219-229`) is unaffected.

## Implementation Plan

### Phase 1: Delete the non-streaming controller handler

- [ ] 1.1 In `src/app/domain/chat/controllers/_chat.py`, delete the
      `send_chat_message` handler (lines 63-167, the entire
      `@post(path="/api/chat", name="chat.api.send")` method).
- [ ] 1.2 In `_chat.py`, drop `metrics_badges` from the import at line 17 so it
      reads `from app.domain.chat.controllers._helpers import chat_form_from_request, location_context_from_form`.
- [ ] 1.3 In `_chat.py`, remove now-unused imports left by 1.1: `uuid`
      (line 5), `HTMXTemplate` and `flash` (lines 11-12),
      `HTTP_503_SERVICE_UNAVAILABLE` (line 14), `AIServiceUnconfigured`
      (line 18), and the `schemas` import (line 16) **only if** no longer
      referenced. Verify each by grep within the file before removing — keep
      whatever the stream/clear handlers still use (`ServerSentEvent`,
      `ValidationException`, `to_json`, `Inject`, `ADKRunner`,
      `AgentToolsService`, `adk_session_identity`, `clear_adk_session_identity`,
      `structlog`, `re`).
- [ ] 1.4 Confirm `make lint` passes on `_chat.py` (no unused imports, no
      undefined names) before moving on.

### Phase 2: Cascade-delete dead runner + schema + helper

- [ ] 2.1 In `src/app/domain/chat/services/adk.py`, delete `process_request`
      (lines 1123-1158).
- [ ] 2.2 In `adk.py`, delete the now-dead `_CHAT_RESULT_KEYS` constant
      (lines 85-98). Grep the file to confirm no remaining reference.
- [ ] 2.3 In `src/app/domain/chat/schemas/_chat.py`, delete the
      `CoffeeChatReply` struct (lines 38-53).
- [ ] 2.4 In `src/app/domain/chat/schemas/__init__.py`, remove `CoffeeChatReply`
      from the `from ._chat import (...)` block (line 10) and from `__all__`
      (line 17).
- [ ] 2.5 In `src/app/domain/chat/controllers/_helpers.py`, delete the
      `metrics_badges` function (lines 37-48). Keep `CoffeeChatForm`,
      `payload_raw/value/bool/float`, `location_context_from_form`,
      `chat_form_from_request`, `location_text`, and module constants.

### Phase 3: Delete dead templates / markup

- [ ] 3.1 Delete `src/app/domain/web/templates/partials/_chat_response.html.j2`.
- [ ] 3.2 Delete `src/app/domain/web/templates/partials/_metrics_badges.html.j2`.
- [ ] 3.3 Delete `src/app/domain/web/templates/partials/chat_error.html.j2`.
- [ ] 3.4 In `src/app/domain/web/templates/partials/message.html.j2`, remove the
      metrics `<footer>` block (lines 18-63), i.e. the
      `{% if message.source == "ai" and metrics_badges is defined %} ... {% endif %}`
      block. Keep the avatar, header (including the `intent_detected` badge at
      lines 13-15), and message paragraph. The closing `</article></div>` stay.

### Phase 4: Prune tests for the deleted path

- [ ] 4.1 In `src/tests/integration/app/domain/chat/controllers/test_chat_http.py`:
      delete the `/api/chat` cases — `test_htmx_returns_partial` (68-87),
      `test_htmx_validation_returns_chat_error` (90-94),
      `test_non_htmx_returns_json` (97-109),
      `test_json_location_context_requires_consent_for_coordinates` (112-129),
      `test_json_location_context_passes_consented_coordinates` (132-151),
      `test_json_location_context_rejects_invalid_consented_coordinates`
      (154-166), and
      `test_non_htmx_ai_unconfigured_returns_503_without_exception_path`
      (169-183). KEEP `test_stream_returns_sse_events`,
      `test_stream_handles_runner_exception_after_response_started`, and
      `test_clear_chat_session_deletes_adk_session_and_resets_bridge`.
- [ ] 4.2 In `test_chat_http.py`, simplify the `stub_adk_runner` fixture
      (47-65): remove the `process_request` monkeypatch (line 63) and the
      `_FAKE_REPLY` keys/asserts that only existed for the deleted JSON/HTMX
      cases if they are no longer referenced. Keep `_noop_init`,
      `_stream_request`, `ensure_configured`, and the `_FAKE_REPLY` fields the
      surviving stream test asserts (`answer`, `intent_detected`,
      `search_metrics.vector_query`, `embedding_cache_hit`, `sql_phases`).
      Update the module docstring (lines 4-8) to describe the streaming surface
      instead of `POST /api/chat`.
- [ ] 4.3 In `src/tests/unit/app/domain/chat/services/test_adk.py`, delete the
      `process_request`-specific cases:
      `test_process_request_rejects_placeholder_project_before_adk_run`
      (340-363), `test_process_request_returns_all_seven_keys` (366-468),
      `test_store_location_route_returns_grounded_store_without_model`
      (470-528),
      `test_product_availability_near_me_uses_consented_coordinates_and_bypasses_cache`
      (531-601), `test_product_rag_persists_last_products_through_session_store`
      (604-660), `test_order_status_route_is_explicitly_unsupported` (682-721),
      `test_process_request_prefers_workflow_output_intent` (723-785),
      `test_product_rag_response_is_grounded_to_menu_products` (787-856),
      `test_process_request_returns_cached_response_without_model` (923-966),
      `test_cached_response_with_product_lookup_metrics_promotes_visible_intent`
      (968-1010), and
      `test_process_request_raises_ai_service_unconfigured_on_credential_error`
      (1012-1064). KEEP the constructor/tool-factory/`_build_workflow`/
      `_effective_intent`/`_safe_location_context`/`AgentToolsService` cases and
      the `stream_request` case
      `test_product_rag_stream_does_not_emit_speculative_model_delta`
      (858-921). Note: any deeper rewrite of `test_adk.py` is Ch10's scope; do
      only the dead-case removal here.
- [ ] 4.4 In
      `src/tests/integration/app/domain/chat/services/test_chat_workflow.py`,
      rewrite `test_chat_workflow_populates_result_shape_with_oracle_backed_rag`
      to drive `runner.stream_request(...)` and assert on the `type == "final"`
      event payload instead of calling `runner.process_request(...)`
      (line 146). The final event carries the same 12 keys
      (`answer`, `session_id`, `response_time_ms`, `intent_detected`,
      `search_metrics`, `from_cache`, `embedding_cache_hit`, `sql_phases`,
      `store_results`, `inventory_results`, `map_actions`, `location_context`)
      plus a `type` key, so the existing assertions transfer by collecting the
      final event and reading its keys.

### Phase 5: Verify

- [ ] 5.1 Run the grep commands in Verification; confirm zero non-generated
      references to each deleted symbol/partial.
- [ ] 5.2 Run `make lint && make test`; confirm green.
- [ ] 5.3 Regenerate `src/resources/generated/{openapi.json,routes.json}` if the
      project generates them from the live route table, so the stale
      `/api/chat` route entry is dropped. If they are committed snapshots,
      update them; if generated on build, no manual action.

## Acceptance

- [ ] Only `/api/chat/stream` (`chat.api.stream`) and
      `/api/chat/session/clear` (`chat.api.clear_session`) chat routes exist;
      `POST /api/chat` is gone.
- [ ] `grep -rn 'process_request' src/app` → 0 hits;
      `_CHAT_RESULT_KEYS` → 0 hits in `src/app`.
- [ ] `grep -rn 'CoffeeChatReply' src/app` → 0 hits.
- [ ] `grep -rn 'metrics_badges' src/app` → 0 hits.
- [ ] `_chat_response.html.j2`, `_metrics_badges.html.j2`, and
      `chat_error.html.j2` no longer exist; `message.html.j2` still renders
      page-load history without the metrics footer.
- [ ] `validate_message`, `validate_persona`, `chat_form_from_request`,
      `location_context_from_form`, and `ChatMessage` remain and are still used
      by the stream path / history.
- [ ] `make lint && make test` green.

## Verification

```bash
# No remaining references to the deleted symbols (outside generated artifacts).
grep -rn 'process_request' src/app tools
grep -rn '_CHAT_RESULT_KEYS' src/app
grep -rn 'CoffeeChatReply' src/app src/tests
grep -rn 'metrics_badges' src/app

# Deleted partials are gone; message.html.j2 remains.
ls src/app/domain/web/templates/partials/_chat_response.html.j2 \
   src/app/domain/web/templates/partials/_metrics_badges.html.j2 \
   src/app/domain/web/templates/partials/chat_error.html.j2 2>&1 | grep -c 'No such file'
ls src/app/domain/web/templates/partials/message.html.j2

# Only the two surviving chat routes (non-generated source).
grep -rn '"/api/chat' src/app/domain/chat/controllers/_chat.py

# Kept symbols still present.
grep -n 'def validate_message\|def validate_persona' src/app/domain/chat/controllers/_chat.py
grep -n 'class ChatMessage' src/app/domain/chat/schemas/_chat.py

# Gates.
make lint
make test
```
