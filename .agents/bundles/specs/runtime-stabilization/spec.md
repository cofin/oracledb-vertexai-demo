---
type: Spec
flow_id: runtime-stabilization
title: Native AI Runtime, Persistence, Streaming & Endpoint Stabilization
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-10-12T17:35:00Z
updated_at: 2026-10-12T17:35:00Z
description: Fix all 11 runtime blockers across Oracle session/event persistence, streaming event aggregation, Gemini thought_signature and tool call IDs, frontend final SSE contract, A2A task ownership, /api/vector-search parameter binding, HNSW FETCH APPROX SQL, and typed 503 AI configuration handling.
tags:
  - bugfix
  - ai
  - oracle
  - a2a
  - vector-search
parent_prd: coffee-agent-stabilization-and-hybrid-search
research: []
---

# Flow: Native AI Runtime, Persistence, Streaming & Endpoint Stabilization

**Flow ID:** `runtime-stabilization`
**Parent PRD:** [`coffee-agent-stabilization-and-hybrid-search`](../coffee-agent-stabilization-and-hybrid-search/spec.md)

---

## Specification

### Code Analysis Summary

Files examined on `feat/gemini-embeddings` (`@3a3cbd1`):

- `src/app/db/migrations/0001_cymball_coffee_products.sql` — Creates `product`, `coffee_store`, `store_product_inventory`, `embedding_cache`, `response_cache`, `search_metrics`, and `intent_exemplar`, but creates **no** AI session/event tables.
- `src/app/db/sql/ai-runtime.sql:1-60` — Queries `adk_session` and `adk_event` with custom columns (`seq`, `turn`, `agent`, `content`, `actions`, `created_at`, `updated_at`) that do not match SQLSpec's removed `adk` extension DDL (`AI-01`).
- `src/app/domain/ai/runtime/_store.py:72-195` — `OracleSessionStore` and `OracleEventStore` take a request-scoped `AsyncOracleDriver` and never call `await driver.commit()`, causing all inserts/updates/deletes to roll back when the connection closes (`AI-04`). `list_events` also hardcodes `seq=0` (`AI-05`).
- `src/app/domain/ai/runtime/_model.py:80-86`, `src/app/domain/ai/runtime/_loop.py:75-294`, `src/app/domain/ai/runtime/_stream.py:157-191`, `src/app/domain/ai/services/agent_service.py:55-124` — `generate_stream` yields only `partial=True` events; `agent_service.py` persists only `if not event.partial`; `_stream.py` sets `has_final = True` only on non-partial events and emits a minimal `final` frame lacking the fields required by `src/resources/chat-stream.js:297-305` (`AI-02`, `CP-01`, `CP-02`). Furthermore, `thought_signature` and `FunctionCall.id` / `FunctionResponse.id` are dropped (`AI-06`), and `_schema.py` emits uppercase OpenAPI types (`OBJECT`) into `parameters_json_schema` (`AI-07`).
- `src/app/domain/ai/a2a/card.py:12-40` & `src/app/domain/ai/a2a/executor.py:45-169` — `user_id = str(scope.get("user") or UnauthenticatedUser())` yields a memory-address string (`AI-08`), `_get_container()` leaks an unclosed `Scope.APP` container (`AI-09`), and `build_agent_card` hardcodes `http://localhost:8000` (`AI-17`).
- `src/app/domain/products/controllers/_vector.py:173-175` — `GET /api/vector-search` uses reserved parameter name `query: FromQuery[str]`, causing Litestar to return HTTP 400 on every request (`CP-08`), and lacks `limit` validation (`CP-11`).
- `src/app/db/sql/products.sql:4-16, 71-95` — `get-product` returns the 3072-float `embedding` column (`CP-10`), and `vector-search-products` / `find-similar-products` order by `similarity_score DESC` with `FETCH FIRST`, preventing Oracle 26ai from using the `product_embedding_idx` HNSW index (`CP-07`).
- `src/app/ioc.py:67-84` & `src/app/domain/chat/exceptions.py:1-58` — `AIServiceUnconfigured` is never raised when `GOOGLE_CLOUD_PROJECT` is a placeholder (`"demo-project"`, `"your-project-id"`) and `GOOGLE_API_KEY` is unset (`PL-04`).

### Relevant Patterns

- [SQLSpec Services](../../knowledge/patterns/sqlspec-services.md) — Named SQL files in `src/app/db/sql/*.sql`, `:name` bind parameters, `TO_VECTOR(:query_vector, 3072, FLOAT32)`.
- [Dishka Dependency Injection](../../knowledge/patterns/dishka-di.md) — `src/app/ioc.py` has no `from __future__ import annotations`; `Scope.APP` vs `Scope.REQUEST` lifecycle discipline.
- [Testing & Verification](../../knowledge/guides/testing-verification.md) — Deterministic unit tests with AnyIO and `AsyncTestClient`.

### Requirements

- **REQ-01 (Persistence)**: Create `agent_session` and `agent_event` in `0002_agent_runtime_and_hybrid_search.sql`, update `src/app/db/sql/ai-runtime.sql`, and refactor `OracleSessionStore` / `OracleEventStore` to run at `Scope.APP` over `db_manager.provide_session()` with explicit `await driver.commit()` and monotonic `seq` ordering.
- **REQ-02 (Streaming & Tool Fidelity)**: Emit an aggregated `partial=False` model `AgentEvent` at the end of each model step in `AgentRuntime.run_stream`, round-trip `thought_signature` and `call_id` on `Part`/`FunctionCall`/`FunctionResponse`, emit standard lowercase JSON Schema in `_schema.py`, and enrich `AgentStreamService`'s `final` SSE frame with the full `ChatResponse` payload required by `chat-stream.js`.
- **REQ-03 (A2A Protocol)**: Implement `build_agent_card(base_url=...)`, `build_a2a_call_context(context)` with stable principal/anonymous owner resolution and `X-Session-ID` inheritance, and proper `TaskUpdater` lifecycle (`start_work` $\rightarrow$ `add_artifact` $\rightarrow$ `complete`/`failed`) using the ASGI request container or injected app container.
- **REQ-04 (Vector Search & Typed 503)**: Alias `q` to `query="query"` with `limit` bounds (`ge=1, le=20`) in `GET /api/vector-search`, update `vector-search-products` and `find-similar-products` in `products.sql` to `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX FIRST :limit ROWS ONLY`, drop `embedding` from `get-product`, raise `AIServiceUnconfigured` (HTTP 503) when AI credentials are placeholders, and delete the stale `src/tests/unit/app/domain/chat/controllers/conftest.py`.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `REQ-01` | `1.1` | `regression_tdd` | `src/app/db/migrations/0002_agent_runtime_and_hybrid_search.sql`, `src/app/db/sql/ai-runtime.sql`, `src/app/domain/ai/runtime/_store.py`, `src/app/ioc.py` | `src/tests/unit/app/domain/ai/test_store.py` |
| `REQ-02` | `1.2` | `regression_tdd` | `src/app/domain/ai/runtime/_types.py`, `src/app/domain/ai/runtime/_schema.py`, `src/app/domain/ai/runtime/_model.py`, `src/app/domain/ai/runtime/_loop.py`, `src/app/domain/ai/runtime/_stream.py`, `src/app/domain/ai/services/agent_service.py`, `src/app/domain/chat/controllers/_chat.py` | `src/tests/unit/app/domain/ai/test_runtime.py`, `src/tests/unit/app/domain/ai/test_stream.py`, `src/tests/unit/app/domain/chat/controllers/test_chat_controller.py` |
| `REQ-03` | `1.3` | `regression_tdd` | `src/app/domain/ai/a2a/__init__.py`, `src/app/domain/ai/a2a/card.py`, `src/app/domain/ai/a2a/executor.py`, `src/app/server/plugins.py` | `src/tests/unit/app/domain/ai/test_a2a.py` |
| `REQ-04` | `1.4` | `regression_tdd` | `src/app/domain/products/controllers/_vector.py`, `src/app/db/sql/products.sql`, `src/app/domain/chat/exceptions.py`, `docs/reference/api.md` | `src/tests/unit/app/domain/products/test_vector_controller.py`, `src/tests/unit/app/domain/chat/test_exceptions.py` |

---

## Implementation Plan

### Phase 1: Persistence & Runtime Loop Stabilization

- [ ] 1.1 Add `0002` `agent_session`/`agent_event` migration, update `ai-runtime.sql`, and make `OracleSessionStore`/`OracleEventStore` commit at `Scope.APP`
- [ ] 1.2 Fix `AgentRuntime.run_stream` non-partial aggregation, `thought_signature`/call ID round-tripping, lowercase JSON Schema, and `final` SSE payload contract

### Phase 2: Protocol & Endpoint Bug Fixes

- [ ] 1.3 Fix A2A owner task scoping (`build_a2a_call_context`), container lifecycle, and dynamic `build_agent_card` URL
- [ ] 1.4 Fix `GET /api/vector-search` reserved `query` parameter, HNSW `FETCH APPROX` SQL in `products.sql`, and typed 503 `AIServiceUnconfigured` handling

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `runtime-stabilization` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - `OracleSessionStore` and `OracleEventStore` take `SQLSpec` (`db_manager`) at `Scope.APP` and open per-operation `async with self._db.provide_session() as driver:` sessions with explicit `await driver.commit()`.
  - `AgentRuntime.run_stream` yields `partial=True` text deltas for live streaming and then yields one `partial=False` aggregated `AgentEvent` per model step so `agent_service.py` persists complete turns and `AgentStreamService` emits the enriched `final` frame.
- **Newest Discoveries**:
  1. `ai-runtime.sql` targets `adk_session`/`adk_event` which are not created by any migration (`AI-01`).
  2. `OracleSessionStore` and `OracleEventStore` never commit transactions (`AI-04`).
  3. `GeminiModelClient.generate_stream` yields only `partial=True` chunks (`AI-02`, `CP-01`).
  4. `a2a/executor.py` uses `str(UnauthenticatedUser())` as task owner and leaks a Dishka container (`AI-08`, `AI-09`).
  5. `_vector.py` uses reserved `query` parameter name (`CP-08`) and `products.sql` omits `FETCH APPROX` (`CP-07`).
- **Blockers & Unblock Conditions**: None
- **Next Exact Step**: Claim and execute Task `1.1` (`tasks/1.1.md`).
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/knowledge/guides/agentic-ai-runtime.md`
  - `.agents/bundles/knowledge/guides/oracle-database.md`
  - `.agents/bundles/knowledge/patterns/sqlspec-services.md`
  - `.agents/bundles/knowledge/patterns/dishka-di.md`
