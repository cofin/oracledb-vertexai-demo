# Flow: ADK Runner Source Organization

*Flow ID: `adk-runner-source-organization_20260501`*
*Chapter 4 of [demo-source-organization_20260501](../demo-source-organization_20260501/prd.md)*
*Beads: `oracledb-vertexai-8jt.4`*
*Depends on: `source-organization-contract_20260501`*
*Status: Implemented*

---

## Objective

Make the ADK chat runner readable as public orchestration first while preserving
the exact request-scoped tool, cache, telemetry, and streaming semantics.

---

## Primary Files

- `src/app/domain/chat/services/adk.py`
- `src/app/domain/chat/services/workflow.py`
- New private modules under `src/app/domain/chat/services/`, for example:
  - `_adk_grounding.py`
  - `_adk_telemetry.py`
  - `_adk_history.py`
  - `_adk_tools.py`
  - `_adk_credentials.py`
- `src/tests/unit/app/domain/chat/services/test_adk.py`
- `src/tests/integration/app/domain/chat/services/test_chat_workflow.py`

---

## Current Hotspots

- `adk.py` has 17 top-level private helpers before `AgentToolsService`.
- `ADKRunner._make_tool_factories()` has seven nested tool closures. These
  closures are probably correct because tools must bind request-scoped services
  and a per-turn metrics dictionary.
- `stream_request()` carries cache lookup, intent classification, ADK streaming,
  product grounding fallback, cache writes, and final payload assembly in one
  method.

---

## Requirements

- Keep `AgentToolsService`, `ADKRunner`, `credential_guard_callback`, and
  response payload constants import-compatible.
- Move product grounding helpers such as product coercion, price formatting,
  product answer formatting, similarity score, and product lookup checks into a
  grounding helper module.
- Move SQL phase/cache phase formatting and metrics recording helpers into a
  telemetry helper module.
- Move ADK event/history coercion helpers into a history helper module.
- Keep closure-bound tools request-scoped. If helper extraction touches tool
  factories, the public `ADKRunner._make_tool_factories()` must still create
  closures with active `tools_service` and `metric_state`.
- Keep `PRODUCT_RAG`, response-cache, SSE final/delta payloads, and display
  history behavior unchanged.
- Preserve typed 503 behavior for missing/placeholder Vertex configuration.

---

## Implementation Plan

1. Lock behavior with tests:
   - Run the current ADK unit/integration tests before refactor.
   - Add assertions if needed for response payload keys, effective
     `PRODUCT_RAG` intent, SQL phase data, and display history behavior.
2. Extract pure helpers:
   - Move product grounding helpers to `_adk_grounding.py`.
   - Move SQL phase, cache phase, and metric state helpers to
     `_adk_telemetry.py`.
   - Move history/event coercion helpers to `_adk_history.py`.
   - Keep imports internal to `app.domain.chat.services`.
3. Simplify `adk.py`:
   - Keep constants and public classes visible near the top.
   - Keep `AgentToolsService` methods together.
   - Keep `ADKRunner` public methods in a readable order:
     session/history helpers, stream processing, process-to-completion.
4. Review closure helpers:
   - Keep nested tool closures if they remain the clearest request-scoped shape.
   - If moved into `_adk_tools.py`, expose a small helper that accepts
     `tools_service` and `metric_state` and returns closures. Do not introduce
     globals.
5. Run focused verification:
   - `uv run pytest src/tests/unit/app/domain/chat/services/test_adk.py -q`
   - `uv run pytest src/tests/integration/app/domain/chat/services/test_chat_workflow.py -q`
   - `uv run pytest src/tests/unit/app/test_source_organization.py -q`
   - `uv run ruff check src/app/domain/chat/services`

---

## Acceptance Criteria

- `adk.py` no longer starts with a long run of private helper functions.
- Public ADK service and runner contracts remain import-compatible.
- Closure-bound tools still use active request services and per-turn metrics.
- Existing ADK behavior tests pass.
- No chat payload or cache key behavior changes.

## Implementation Notes

- Product grounding, deterministic store/product route formatting, safe
  location-context shaping, and map action formatting moved to
  `app.domain.chat.services._adk_grounding`.
- SQL phase, response-cache phase, vector summarization, tool SQL phase, and
  intent-promotion helpers moved to `_adk_telemetry`.
- ADK event text and display-history coercion moved to `_adk_history`.
- `adk.py` now leads with `AgentToolsService`, then credential guard wiring,
  then `ADKRunner`, while importing private helpers back under their existing
  private names for compatibility with current tests and call sites.
- Verification: focused ADK unit tests, focused ADK integration workflow test,
  source organization guard, `make lint`, `make test`, and `git diff --check`.
