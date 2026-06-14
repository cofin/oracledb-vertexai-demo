# Flow: adk-readability

*Beads: oracledb-vertexai-mzm.6*
*Depends on: Ch5 `chat-path-consolidation` (mzm.5) — `process_request` and
`_CHAT_RESULT_KEYS` are already removed before this chapter starts.*

## Specification

Make `src/app/domain/chat/services/adk.py` and its `_adk_*` helpers readable for
a reader with high Oracle-DB expertise but low Python experience: fewer files,
fewer single-call indirections, one obvious shape for the "final" event, no dead
branches, and no compatibility shims. Chat behavior is byte-for-byte preserved —
verified by the integration chat HTTP + workflow tests and a new
PRODUCT_RAG-stream parity assertion.

This chapter assumes Ch5 already landed: `ADKRunner.process_request` and
`_CHAT_RESULT_KEYS` no longer exist, and `stream_request` is the only entry
point. `record_search_metric` deletion is owned by Ch2 (`deadcode-sweep`) — do
**not** touch it here.

Project rules in force: no backwards-compat shims (delete, never branch on
`hasattr`); docstrings/comments describe behavior only (no spec/phase refs);
delete any symbol that becomes unused; browser coordinates stay request-scoped
and masked in telemetry.

### Requirements

- Remove the unreachable PRODUCT_RAG re-ground branch in `stream_request`
  (`adk.py:1081-1087`). `_deterministic_route_event` already routes
  `PRODUCT_RAG` to `_product_rag_event` and returns before the fan-out, so the
  fan-out re-ground for PRODUCT_RAG is dead. After removal, the fan-out path
  serves only `GENERAL_CONVERSATION`; state that in one comment. Add an
  integration assertion that PRODUCT_RAG stream output is identical
  before/after.
- Introduce one `_final_event(...)` builder and use it everywhere the 12-key
  `{"type": "final", ...}` dict is currently hand-written (~6 sites:
  `adk.py:659` cached, `729` product-rag, `775` store-location, `854`
  availability, `896` order-status, `1110` general-conversation). Each route
  builds its payload through the one builder.
- Drop the dead camelCase dual-key fallbacks in `_cached_response_event`
  (`adk.py:614-685`): the cache is written snake_case by this same app
  (`_product_rag_event` / general-conversation `response_data` use
  `search_metrics`, `sql_phases`, `intent_detected`, `embedding_cache_hit`,
  `last_products`, etc.), so the `searchMetrics`/`sqlPhases`/`intentDetected`/
  `lastProducts`/`storeResults`/`inventoryResults`/`mapActions`/
  `embeddingCacheHit` reads are never hit. Read snake_case only.
- Inline single-call privates into `stream_request`: `_get_or_create_session`
  (`535-550`), `_classify_intent` (`609-612`), `_response_cache_lookup`
  (`909-928`). Collapse `_unsupported_order_status_event` (`874-907`, boilerplate
  around one constant answer) into a direct `_final_event(...)` call from
  `_deterministic_route_event`.
- KEEP these methods (real seams or multi-use): `_make_tool_factories`,
  `_build_workflow`, `_append_display_history`, `_deterministic_route_event`,
  `_product_rag_event`, `_store_location_event`, `_product_availability_event`,
  `_cached_response_event`, `get_history`, `get_history_or_empty`,
  `clear_session`.
- Fold `_adk_history.py` (~50 LOC) and `_adk_telemetry.py` (~99 LOC) back into
  `adk.py` (or one `_adk_support.py`); KEEP `_adk_grounding.py` as its own
  module. Update every import (`adk.py`, `_adk_grounding.py` imports
  `_coerce_sql_phases` from `_adk_telemetry`, and any test that imports
  `adk._sql_phase`/`_effective_intent` via the `adk` module re-export).
- Simplify `_adk_grounding.py` readability hot-spots:
  - The ~40-word inline stop-word regex in `_extract_product_query`
    (`_adk_grounding.py:164-168`) → a named `frozenset` of stop words with a
    word-by-word filter (same result, readable).
  - The `ans[:-1] + "…"`-style string-slice in `_format_availability_answer`
    (`_adk_grounding.py:340-341`, `ans = ans[:-1] + f". I found ..."`) → build
    the sentence in parts so a reader does not have to reason about negative
    slicing.
- Remove the `make_coffee_node` compat shim in `workflow.py:35-44`: drop the
  `if hasattr(agent, "model_copy")` dual path and the
  `agent.name = "coffee_turn"; return agent` fallback; keep only the real
  `return agent.model_copy(update={"name": "coffee_turn"})` path (LlmAgent has
  `model_copy` at the pinned ADK).
- After the refactor, `stream_request` reads as three linear exits — cache
  short-circuit, deterministic route, general-conversation event — and no longer
  needs `# noqa: PLR0914` (`adk.py:985`).

### Code Analysis Summary

Verified against current source on this branch.

**Dead PRODUCT_RAG re-ground (the headline risk):**

- `stream_request` calls `_deterministic_route_event` at `adk.py:1028`.
  `_deterministic_route_event` (`930-983`) handles `PRODUCT_RAG` first
  (`943-953` → `_product_rag_event`) and returns a non-`None` event; `1039-1041`
  yields it and `return`s. So the fan-out at `1043-1121` is only reached for
  intents that returned `None` from the router — i.e. `GENERAL_CONVERSATION`.
- The branch at `1081-1087` (`if intent_detected == _PRODUCT_RAG_INTENT:`
  re-runs `_ground_product_rag_turn`) is therefore unreachable for the route
  intent, but `_effective_intent` at `1076` can still *relabel*
  GENERAL_CONVERSATION → PRODUCT_RAG when a product lookup actually ran (e.g.
  the model called the `search_products_by_vector` tool). The re-ground there
  re-derives `answer`/`search_metrics`/`sql_phases` from `metric_state`. Removal
  must preserve that relabel-driven grounding: keep `_effective_intent`; the
  parity test must cover the GENERAL_CONVERSATION-that-becomes-PRODUCT_RAG case,
  not only the directly-routed PRODUCT_RAG case, before the branch is deleted.
  (If the branch is load-bearing for the relabel case, fold its body into the
  single general-conversation tail rather than deleting outright; the parity
  test decides.)

**The 12-key final dict, hand-written 6×** (identical key set, different values):
`adk.py:659-685` (cached, with `_safe_location_context` instead of
`_default_route_fields`), `729-740` (product-rag), `775-789` (store-location),
`854-872` (availability), `896-907` (order-status), `1110-1121` (general
conversation). Common keys: `type`, `answer`, `session_id`, `response_time_ms`,
`intent_detected`, `search_metrics`, `from_cache`, `embedding_cache_hit`,
`sql_phases`, then `store_results`/`inventory_results`/`map_actions`/
`location_context` (the last four come from `_default_route_fields` or are set
explicitly). A `_final_event(*, answer, session_id, response_time_ms,
intent_detected, search_metrics, sql_phases, from_cache=False,
embedding_cache_hit=False, store_results=None, inventory_results=None,
map_actions=None, location_context=None)` returning the dict (defaulting the
four route fields via `_default_route_fields` / empty lists) reproduces all six.

**camelCase fallbacks are dead:** `_cached_response_event` reads
`searchMetrics`/`search_metrics`, `sqlPhases`/`sql_phases`,
`intentDetected`/`intent_detected`, `lastProducts`/`last_products`,
`embeddingCacheHit`/`embedding_cache_hit`,
`storeResults`/`inventoryResults`/`mapActions` (`626-684`). The cache is written
only by this app: `_product_rag_event.response_data` (`707-717`) and the
general-conversation `response_data` (`1089-1098`) use snake_case keys
exclusively. No writer emits camelCase, so the camelCase arm is never taken.

**Single-call privates** (one caller each, all `stream_request`):
`_get_or_create_session` → `adk.py:1007`; `_classify_intent` → `1027`;
`_response_cache_lookup` → `1009`. `_unsupported_order_status_event` is called
once from `_deterministic_route_event:975`.

**Helper modules to fold:**

- `_adk_history.py` (51 LOC) exports `_coerce_history_messages`,
  `_event_content_text`, `_event_history_messages`. Imported by `adk.py:39-43`
  (`_coerce_history_messages`, `_event_content_text`, `_event_history_messages`)
  and used inside `_collect_workflow_stream`, `get_history`,
  `_append_display_history`.
- `_adk_telemetry.py` (99 LOC) exports `_coerce_sql_phases`,
  `_effective_intent`, `_record_tool_sql_phases`, `_response_cache_phase`,
  `_sha256_text`, `_similarity_score`, `_sql_phase`, `_summarize_vector`
  (plus private `_named_sql_text`, `_product_lookup_ran`). Imported by
  `adk.py:44-53` **and** by `_adk_grounding.py:12`
  (`from ...._adk_telemetry import _coerce_sql_phases`). When folded into
  `adk.py`, `_adk_grounding.py` would create a circular import
  (`adk` → `_adk_grounding` → `adk`); resolve by either (a) folding both into a
  single new `_adk_support.py` that both `adk.py` and `_adk_grounding.py`
  import, or (b) keeping `_coerce_sql_phases` reachable without a cycle. Prefer
  `_adk_support.py` — it keeps `_adk_grounding.py` independent of `adk.py` and
  satisfies "fewer files than three orbiting `_adk_*` modules" (3 → 2).
- Tests reference these via the `adk` module namespace:
  `test_adk.py` uses `adk_module._effective_intent` and
  `adk_module._safe_location_context`; `_safe_location_context` lives in
  `_adk_grounding` and is re-exported through `adk`'s import. After folding,
  ensure `_effective_intent` and `_safe_location_context` remain importable as
  `app.domain.chat.services.adk._effective_intent` /
  `._safe_location_context` (they already are, via the import statements) so
  these tests keep passing.

**`_adk_grounding.py` hot-spots:** the regex at `164-168` and the slice at
`340-341` (`ans = ans[:-1] + f". I found {len(...)} stores with matching availability."`).

**workflow.py shim:** `make_coffee_node` (`35-44`) branches on
`hasattr(agent, "model_copy")`. `_build_workflow` (`adk.py:524-533`) passes a
real `LlmAgent`, which has `model_copy`, so the fallback is dead. `make_workflow`
(`65-92`) and `__all__` keep `make_coffee_node`.

**`# noqa: PLR0914`:** `stream_request` is declared
`async def stream_request(  # noqa: PLR0914` at `adk.py:985`. Removing the
inlined locals' surrounding boilerplate and the dead re-ground should drop the
local count under the threshold; remove the `noqa` and let lint confirm.

## Implementation Plan

### Phase 1: Fold `_adk_history` + `_adk_telemetry` into `_adk_support.py`

- [ ] 1.1 Create `src/app/domain/chat/services/_adk_support.py` containing every
      function currently in `_adk_history.py` and `_adk_telemetry.py`
      (`_coerce_history_messages`, `_event_content_text`,
      `_event_history_messages`, `_named_sql_text`, `_sha256_text`,
      `_summarize_vector`, `_sql_phase`, `_response_cache_phase`,
      `_coerce_sql_phases`, `_record_tool_sql_phases`, `_similarity_score`,
      `_product_lookup_ran`, `_effective_intent`). Keep behavior identical and
      docstrings behavior-only.
- [ ] 1.2 Delete `_adk_history.py` and `_adk_telemetry.py`.
- [ ] 1.3 Update `adk.py` imports (currently `39-43` and `44-53`) to one
      `from app.domain.chat.services._adk_support import (...)` block.
- [ ] 1.4 Update `_adk_grounding.py:12` to
      `from app.domain.chat.services._adk_support import _coerce_sql_phases`.
- [ ] 1.5 Update any test that imports from `_adk_history`/`_adk_telemetry`
      directly (grep for the module names under `src/tests`); tests that go
      through `adk_module.<symbol>` keep working unchanged.
- [ ] 1.6 `make lint` — confirm no circular import, no unused imports.

### Phase 2: Remove the `workflow.py` compat shim

- [ ] 2.1 In `src/app/domain/chat/services/workflow.py`, simplify
      `make_coffee_node` (lines 35-44) to a single body:
      `return agent.model_copy(update={"name": "coffee_turn"})`. Keep the
      behavior-only docstring; drop the `hasattr` branch and the mutate-and-
      return fallback.

### Phase 3: Introduce `_final_event` and route everything through it

- [ ] 3.1 Add a module-level `_final_event(*, answer, session_id,
      response_time_ms, intent_detected, search_metrics, sql_phases,
      from_cache=False, embedding_cache_hit=False, store_results=None,
      inventory_results=None, map_actions=None, location_context=None) ->
      dict[str, Any]` in `adk.py`. It returns the canonical
      `{"type": "final", ...}` dict; when the four route fields are omitted it
      fills them from `_default_route_fields(location_context)`; when given it
      uses the provided lists and `_safe_location_context(location_context)`.
- [ ] 3.2 Rewrite the return at `_cached_response_event` (659-685) to call
      `_final_event(...)` with `from_cache=True` and the cached/coerced values.
- [ ] 3.3 Rewrite `_product_rag_event` return (729-740) via `_final_event(...)`.
- [ ] 3.4 Rewrite `_store_location_event` return (775-789) via `_final_event`
      (passing `store_results=stores`, `map_actions=_build_map_actions(stores)`,
      `location_context=location_context`).
- [ ] 3.5 Rewrite `_product_availability_event` return (854-872) via
      `_final_event` (`inventory_results=inventory`,
      `map_actions=_build_map_actions(inventory)`).
- [ ] 3.6 Rewrite the general-conversation tail return (1110-1121) via
      `_final_event`.
- [ ] 3.7 Confirm each rewritten dict is key-identical to the original
      (same 13 keys incl. `type`); rely on the integration tests in Phase 6.

### Phase 4: Strip camelCase fallbacks and inline single-call privates

- [ ] 4.1 In `_cached_response_event` (614-685), replace each
      `cached_response.get("camelKey") or cached_response.get("snake_key")`
      with the snake_case read only (`searchMetrics` → `search_metrics`,
      `sqlPhases` → `sql_phases`, `intentDetected` → `intent_detected`,
      `lastProducts` → `last_products`, `embeddingCacheHit` →
      `embedding_cache_hit`, `storeResults`/`inventoryResults`/`mapActions` →
      `store_results`/`inventory_results`/`map_actions`).
- [ ] 4.2 Inline `_get_or_create_session` body into `stream_request` at the
      call site (1007), then delete the method (535-550).
- [ ] 4.3 Inline `_classify_intent` body into `stream_request` at the call site
      (1027), then delete the method (609-612).
- [ ] 4.4 Inline `_response_cache_lookup` body into `stream_request` at the call
      site (1009), then delete the method (909-928). Preserve the
      `_has_browser_coordinates` early-return that bypasses caching for
      consented coordinates (coordinate privacy).
- [ ] 4.5 Collapse `_unsupported_order_status_event`: in
      `_deterministic_route_event` (974-982) build the order-status final event
      inline via `_final_event(...)` with the constant answer and
      `intent_detected=_ORDER_STATUS_INTENT`, still calling
      `_append_display_history`. Delete `_unsupported_order_status_event`
      (874-907).

### Phase 5: Remove the dead PRODUCT_RAG re-ground; simplify grounding hot-spots

- [ ] 5.1 Before editing: add/confirm the parity test (Phase 6.1) covering both
      a directly-routed PRODUCT_RAG turn and a GENERAL_CONVERSATION turn that a
      tool call relabels to PRODUCT_RAG via `_effective_intent`.
- [ ] 5.2 In `stream_request`, remove the dead re-ground branch (1081-1087). If
      the parity test shows the relabel case relied on it, fold the
      `_ground_product_rag_turn` re-derivation into the single tail so the
      relabeled answer/metrics still ground — without a separate `if PRODUCT_RAG`
      block. Add one comment stating the fan-out path now serves only
      `GENERAL_CONVERSATION` (and its tool-driven PRODUCT_RAG relabel).
- [ ] 5.3 Remove `# noqa: PLR0914` from `stream_request` (985); run lint.
- [ ] 5.4 In `_adk_grounding.py`, replace the inline stop-word regex
      (164-168) with a named `_PRODUCT_QUERY_STOP_WORDS = frozenset({...})`
      and a word-filter that preserves the existing output (lower-case, strip
      non-alphanumerics, drop stop words, title-case the remainder).
- [ ] 5.5 In `_adk_grounding.py` `_format_availability_answer` (333-342),
      replace `ans = ans[:-1] + f". I found ..."` by composing the sentence in
      parts (build the base in-stock sentence without a trailing period when a
      follow-on clause applies, then append
      `". I found {n} stores with matching availability."`).

### Phase 6: Verify identical behavior

- [ ] 6.1 Add an integration assertion (in
      `test_chat_workflow.py` or `test_chat_http.py`) that PRODUCT_RAG stream
      output (the final event's `answer`, `intent_detected`, `search_metrics`
      product keys, and `sql_phases` sql_keys) is unchanged — covering both the
      directly-routed and the tool-relabeled PRODUCT_RAG cases.
- [ ] 6.2 Run `make lint && make test`; confirm green.
- [ ] 6.3 Grep to confirm the three orbiting modules are now two
      (`_adk_support.py`, `_adk_grounding.py`) and `_adk_history.py` /
      `_adk_telemetry.py` are gone.

## Acceptance

- [ ] Chat behavior identical end-to-end: integration chat HTTP + workflow tests
      pass, including the new PRODUCT_RAG stream-parity assertion.
- [ ] No compat shim in `workflow.py` (`make_coffee_node` is a single
      `model_copy` line, no `hasattr`).
- [ ] `_adk_history.py` and `_adk_telemetry.py` no longer exist as separate
      modules; their functions live in `_adk_support.py`; `_adk_grounding.py`
      remains separate and import-cycle-free.
- [ ] One `_final_event` builds the final dict for all routes; the 12-key dict
      is no longer hand-written 6×.
- [ ] `_cached_response_event` reads snake_case keys only (no camelCase
      fallback).
- [ ] `_get_or_create_session`, `_classify_intent`, `_response_cache_lookup`,
      and `_unsupported_order_status_event` are gone (inlined/collapsed);
      `_make_tool_factories`, `_build_workflow`, `_append_display_history`,
      `_deterministic_route_event`, `_product_rag_event`,
      `_store_location_event`, `_product_availability_event` remain.
- [ ] The dead PRODUCT_RAG re-ground branch is removed; `stream_request` carries
      no `# noqa: PLR0914` and reads as three linear exits.
- [ ] `_adk_grounding.py` uses a named stop-word frozenset and a part-built
      availability sentence (no inline 40-word regex, no negative-index slice).
- [ ] `record_search_metric` is untouched here (Ch2 owns it).
- [ ] Browser coordinates stay request-scoped and masked; no coordinate value
      appears in history, cache, metrics, or logs.
- [ ] `make lint && make test` green.

## Verification

```bash
# Folded modules gone; support + grounding remain.
ls src/app/domain/chat/services/_adk_history.py \
   src/app/domain/chat/services/_adk_telemetry.py 2>&1 | grep -c 'No such file'
ls src/app/domain/chat/services/_adk_support.py \
   src/app/domain/chat/services/_adk_grounding.py

# No compat shim left.
grep -n 'hasattr(agent, "model_copy")' src/app/domain/chat/services/workflow.py   # 0 hits

# Final-dict builder present; hand-written finals collapsed.
grep -n 'def _final_event' src/app/domain/chat/services/adk.py
grep -c '"type": "final"' src/app/domain/chat/services/adk.py                      # 1 (inside _final_event)

# Inlined privates removed.
grep -n '_get_or_create_session\|_classify_intent\|_response_cache_lookup\|_unsupported_order_status_event' \
  src/app/domain/chat/services/adk.py                                             # 0 def hits

# Dead re-ground / noqa gone.
grep -n 'PLR0914' src/app/domain/chat/services/adk.py                             # 0 hits

# camelCase fallbacks gone from the cached path.
grep -n 'searchMetrics\|sqlPhases\|intentDetected\|lastProducts\|embeddingCacheHit\|storeResults\|inventoryResults\|mapActions' \
  src/app/domain/chat/services/adk.py                                             # 0 hits

# Grounding readability.
grep -n '_PRODUCT_QUERY_STOP_WORDS' src/app/domain/chat/services/_adk_grounding.py
grep -n 'ans\[:-1\]' src/app/domain/chat/services/_adk_grounding.py               # 0 hits

# Coordinate privacy guard still present on the cache path.
grep -n '_has_browser_coordinates' src/app/domain/chat/services/adk.py

# Gates.
make lint
make test
```
