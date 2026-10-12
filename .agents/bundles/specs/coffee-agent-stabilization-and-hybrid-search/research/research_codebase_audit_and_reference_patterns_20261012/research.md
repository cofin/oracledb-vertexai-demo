---
type: Research
research_id: research_codebase_audit_and_reference_patterns_20261012
title: Codebase Audit, Regression Analysis, and Reference Platform Patterns
description: Comprehensive review of runtime defects on feat/gemini-embeddings, regression analysis against main, and reference Litestar/SQLSpec/Dishka/MCP/Queues patterns
scope: architecture
status: stable
state: promoted
promoted_to: coffee-agent-stabilization-and-hybrid-search
confidence: high
created_at: 2026-10-12T17:35:00Z
updated_at: 2026-10-12T17:35:00Z
tags:
  - research
  - architecture
  - ai
  - litestar
  - sqlspec
  - queues
  - security
---

# Codebase Audit, Regression Analysis, and Reference Platform Patterns

## Executive Summary

A full three-domain audit of `feat/gemini-embeddings` (`@3a3cbd1`) compared against `main` (`@2633e2e`) and first-party Litestar reference platform patterns identified **11 runtime blockers**, **14 high-severity regressions**, and concrete structural alignment opportunities across settings, DI, native agent runtime, MCP/A2A, security, and Oracle 26ai background queues.

## 1. AI Runtime & Persistence Findings (`AI-01`..`AI-22`)

| ID | Severity | Location | Finding & Root Cause | Resolution |
| --- | --- | --- | --- | --- |
| `AI-01` | Blocker | `src/app/db/sql/ai-runtime.sql:1-60`, `src/app/db/migrations/0001_cymball_coffee_products.sql` | `ai-runtime.sql` queries `adk_session` and `adk_event` with custom columns (`seq`, `turn`, `agent`, `content`, `actions`, `created_at`, `updated_at`), but `0001` never creates those tables and `lib/settings.py:228` removed the `adk` SQLSpec extension. Every non-in-memory turn raises `ORA-00942: table or view does not exist`. | Add `0002_agent_runtime_and_hybrid_search.sql` creating `agent_session` and `agent_event` (`ON DELETE CASCADE`, `UNIQUE (session_id, seq)`), and update `ai-runtime.sql` to target `agent_session` / `agent_event`. |
| `AI-02` | Blocker | `src/app/domain/ai/runtime/_model.py:80-86`, `src/app/domain/ai/services/agent_service.py:119-123`, `src/app/domain/ai/runtime/_stream.py:165-177` | `GeminiModelClient.generate_stream` yields only `partial=True` chunks. `agent_service.py` persists only `if not event.partial`, and `AgentStreamService._drain_queue` sets `has_final = True` only on non-partial model events. Every live turn emits `error: stream_incomplete` and persists zero model output. | Emit one aggregated `partial=False` `AgentEvent` at the end of each model step in `AgentRuntime.run_stream` (`_loop.py`) carrying combined text, function calls, and `usage_metadata`. |
| `AI-03` | Blocker | `src/app/domain/ai/services/agent_service.py:22-42` | `get_coffee_spec_tree()` registers `tools=()`. The assistant has zero access to product search, inventory, or store data. | Register closure-bound grounded tools (`search_products`, `get_product_details`, `find_nearby_stores`, `check_product_availability`, `check_order_status`) and precede the loop with the single-query hybrid RRF router. |
| `AI-04` | Blocker | `src/app/domain/ai/runtime/_store.py:72-195`, `src/app/ioc.py:93-128` | `OracleSessionStore` and `OracleEventStore` never call `await self._driver.commit()`. Because `AsyncOracleDriver` defaults to `autocommit=False`, session/event writes roll back on connection close. Furthermore, sharing a single request-scoped driver across concurrent streaming tasks risks interleaved transactions. | Inject `SQLSpec` (`db_manager`) at `Scope.APP` into `OracleSessionStore` and `OracleEventStore`, open short-lived `async with self._db.provide_session() as driver:` blocks per store operation, and call `await driver.commit()` after each write. |
| `AI-05` | High | `src/app/domain/ai/runtime/_loop.py:75-182`, `src/app/domain/ai/services/agent_service.py:92-123` | `seq` is never assigned (`seq=0` on every event), and `append_event` is called inside the streaming loop without incrementing sequence numbers. | Query `MAX(seq)` on session load and assign monotonically increasing `seq` values (`next_seq += 1`) across user, model, and tool events. |
| `AI-06` | High | `src/app/domain/ai/runtime/_loop.py:249-294`, `src/app/domain/ai/runtime/_model.py:83-85` | `thought_signature` on `Part` and `id` on `FunctionCall`/`FunctionResponse` are dropped when converting `google-genai` parts and rebuilding `types.Content` history. Gemini 2.5/3 thinking models reject multi-step tool turns when `thought_signature` or call IDs are missing. | Preserve `call_id` and `thought_signature` (base64-encoded for JSON storage) on `Part` and round-trip them in `_loop.py` and `_model.py`. |
| `AI-07` | High | `src/app/domain/ai/runtime/_schema.py:16-94`, `src/app/domain/ai/runtime/_model.py:131-137` | `_schema.py` emits uppercase OpenAPI types (`OBJECT`, `STRING`, `INTEGER`) while `_model.py` passes the dict to `parameters_json_schema`, which expects standard lowercase JSON Schema (`object`, `string`, `integer`). | Emit standard lowercase JSON Schema in `_schema.py` (with `additionalProperties: False` on object schemas). |
| `AI-08` | High | `src/app/domain/ai/a2a/executor.py:85-90` | `user_id = str(scope.get("user") or UnauthenticatedUser())` evaluates to `<...UnauthenticatedUser object at 0x...>`, producing a different owner string per request and breaking `OwnerScopedTaskStore` lookup. | Add `build_a2a_call_context(context)` resolving authenticated principal IDs or a deterministic `"anonymous"` fallback, plus `X-Session-ID` header inheritance. |
| `AI-09` | High | `src/app/domain/ai/a2a/executor.py:61-66` | `_get_container()` falls back to `create_container()`, instantiating a second `Scope.APP` Dishka container that is never closed. | Read `context.call_context["asgi_scope"]["state"]["dishka_container"]` (request container) or inject the app container explicitly into `CoffeeAgentExecutor.__init__`. |

## 2. Chat, Products & Frontend Regression Findings (`CP-01`..`CP-14`)

| ID | Severity | Location | Finding & Root Cause | Resolution |
| --- | --- | --- | --- | --- |
| `CP-01` | Blocker | `src/resources/chat-stream.js:297-305`, `src/app/domain/ai/runtime/_stream.py:157-191` | Frontend JS requires the `final` SSE frame to include `answer`, `session_id`, `response_time_ms`, `intent_detected`, `search_metrics`, `from_cache`, `embedding_cache_hit`, `sql_phases`, `store_results`, `inventory_results`, `map_actions`, and `location_context`. Current `_stream.py` emits only `{"type": "final", "session_id": ..., "turn": ...}`. | Add `final_metadata` callback / enrichment to `AgentStreamService` so the `final` SSE event emits the full `ChatResponse` contract expected by `chat-stream.js` and `telemetry.js`. |
| `CP-06` | High | `src/app/domain/chat/controllers/_chat.py`, `src/app/domain/ai/services/agent_service.py` | Grounded deterministic handlers (`PRODUCT_RAG` with off-menu Folgers guard, `PRODUCT_AVAILABILITY`, `STORE_LOCATION`, `ORDER_STATUS`), response cache lookup/save, and `record_search_metrics` were all bypassed during the initial native runtime migration. | Restore grounded composers in `domain/chat/services/_grounded.py` and telemetry builders in `_telemetry.py`, driven by the single-query hybrid RRF route resolver (`_router.py`). |
| `CP-07` | High | `src/app/db/sql/products.sql:71-80` | `vector-search-products` orders by `similarity_score DESC` with `FETCH FIRST :limit ROWS ONLY`. Oracle HNSW indexes (`INMEMORY NEIGHBOR GRAPH`) only trigger on `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX FIRST :limit ROWS ONLY`. | Rewrite `vector-search-products` and `find-similar-products` to `ORDER BY VECTOR_DISTANCE(embedding, TO_VECTOR(:query_vector, 3072, FLOAT32), COSINE) FETCH APPROX FIRST :limit ROWS ONLY`. |
| `CP-08` | High | `src/app/domain/products/controllers/_vector.py:173-175` | `GET /api/vector-search` declares `query: FromQuery[str]`, which collides with Litestar's reserved `query` keyword argument and fails with HTTP 400 on every call. | Rename parameter to `q: Annotated[str, Parameter(query="query", min_length=1)]` and clamp `limit` (`ge=1, le=20`). |
| `CP-10` | Medium | `src/app/db/sql/products.sql:4-16` | `get-product` selects `embedding`, returning 3,072 floats on single-product detail lookups while `list-products` omits it. | Remove `embedding` from `get-product` projection. |

## 3. Platform, Security, MCP & Queues Findings (`PL-01`..`PL-15`)

1. **Dependencies (`PL-03`)**: `pyproject.toml` still depends on `sqlspec[adk]`, pulling in `google-adk`, while `google-genai` and `tenacity` are only transitive dependencies. Drop `sqlspec[adk]`, declare `google-genai>=1.68.0` and `tenacity>=9.0.0` directly, upgrade `litestar-mcp[a2a,google-genai,opentelemetry]>=0.15.0`, and add `litestar-queues[sqlspec]>=0.12.0`.
2. **Typed 503 on Unconfigured AI (`PL-04`)**: `AIServiceUnconfigured` in `src/app/domain/chat/exceptions.py` is never raised; `ioc.py:72` passes placeholder `"demo-project"` into `genai.Client(vertexai=True)` and ignores `GOOGLE_API_KEY`. Validate credentials in `AIProvider` and raise `AIServiceUnconfigured` (mapped to HTTP 503) when neither `GOOGLE_API_KEY` nor a non-placeholder `GOOGLE_CLOUD_PROJECT` is configured.
3. **Middleware Import-Time Side Effects & CORS Bug (`PL-06`, `PL-10`)**: `src/app/lib/log/_middleware.py:13` calls `settings = get_settings()` at import time, and line 93 accesses `message["headers"]` directly on `http.response.start` (which raises `KeyError` on ASGI responses that omit headers). Resolve settings lazily and use `message.get("headers", [])`.
4. **CSRF & MCP/A2A Security (`PL-08`)**: In `litestar-security` 0.6.0, `PublicController` / `public()` sets `exclude_from_csrf=True` on every route. Browser cookie-session POST routes (`/api/chat/`, `/api/chat/stream`, `/api/chat/clear`, `/api/chat/location`) must opt back into CSRF (`opt={"exclude_from_csrf": False}`), while machine protocol endpoints (`/mcp`, `/a2a`) remain CSRF-exempt and support optional `MCP_API_KEY` header authentication (`X-API-Key`).
5. **Oracle 26ai `litestar-queues` (`SQLSpecBackend`)**: `litestar-queues` 0.12.0 natively supports `oracledb` with `FOR UPDATE SKIP LOCKED` and Oracle DDL (`NUMBER(19)`, `TIMESTAMP WITH TIME ZONE`, `CLOB`). However, `SQLSpecBackend._disable_oracle_lob_wrapping` sets `driver_features["enable_AutoLob"] = False` (`fetch_lobs=False`) on the `OracleAsyncConfig` passed to it. Sharing `config.db` with `SQLSpecBackendConfig` would break `json.loads()` on CLOB columns across the app. Therefore, `DatabaseSettings.get_queue_config()` must construct a dedicated `OracleAsyncConfig` for `SQLSpecBackendConfig`.
