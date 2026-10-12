---
type: Spec
flow_id: coffee-agent-stabilization-and-hybrid-search
title: Native Agent Stabilization, Hybrid RRF Retrieval, and Platform Alignment
state: completed
plan_revision: 1
plan_commit: feecf59
state_revision: 6
current_task: null
last_operation: complete_prd
operation_targets:
  - "slides-and-docs-refresh"
last_verified_checkpoint: 2026-10-12T20:48:00Z
created_at: 2026-10-12T17:35:00Z
updated_at: 2026-10-12T20:48:00Z
description: Master PRD roadmap stabilizing the native Gemini agent runtime, replacing LLM intent classification with a single-query Oracle 26ai Hybrid RRF search, aligning settings/DI/security/MCP with reference platform conventions, adding Oracle background queues, and refreshing slides and documentation.
tags:
  - spec
  - ai
  - oracle
  - hybrid-search
  - queues
parent_prd: null
research:
  - research/research_modern_litestar_oracle_patterns_20261007/research.md
  - research/research_codebase_audit_and_reference_patterns_20261012/research.md
---

# Master PRD: Native Agent Stabilization, Hybrid RRF Retrieval, and Platform Alignment

**Flow ID:** `coffee-agent-stabilization-and-hybrid-search`

---

## North Star

Transform the Cymbal Coffee Oracle 26ai + Vertex AI demo on `feat/gemini-embeddings` into a production-grade, workshop-ready application that:

1. **Runs a rock-solid native `google-genai` + `litestar-mcp` agent runtime** backed by committed `agent_session` and `agent_event` tables in Oracle 26ai, preserving `thought_signature` and tool call IDs, emitting complete SSE `final` frames that match the frontend telemetry contract, and honoring A2A task ownership.
2. **Eliminates the separate `FlashLiteIntentClassifier` LLM call and extra retrieval round trip** by executing a **single Oracle AI Database 26ai Hybrid Search SQL query (`hybrid-search-turn`)** that fuses Oracle Text lexical scoring (`CONTAINS`/`SCORE` with `MULTI_COLUMN_DATASTORE` preferences) and HNSW approximate vector similarity (`VECTOR_DISTANCE` with `FETCH APPROX`) via **Reciprocal Rank Fusion (RRF, $k=60$)** across route exemplars, products, and stores—plus per-term lexical hit counts (`JSON_TABLE`) for deterministic off-menu brand detection (`"Folgers"` $\rightarrow 0$ hits).
3. **Aligns code organization and platform infrastructure** with Litestar ecosystem reference conventions: modular `src/app/lib/settings/` and `src/app/ioc/` packages, private `_*.py` domain service modules, zero `google-adk` / `sqlspec[adk]` dependencies, `litestar-mcp>=0.15.0` (`SkillController`, `PromptController`, `TurnBudget`, `AgentStreamFrame`, `SpanManager`), explicit CSRF opt-in on cookie-session chat POSTs alongside optional `MCP_API_KEY` protection for `/mcp` and `/a2a`, and Ruff `TID251` banned-API gates.
4. **Configures background job processing with `litestar-queues[sqlspec]>=0.12.0` on Oracle 26ai** (`FOR UPDATE SKIP LOCKED`) using a dedicated `OracleAsyncConfig` that isolates queue LOB settings (`fetch_lobs=False`) from the main application database config (`fetch_lobs=True`).
5. **Updates `SLIDES.md`, Sphinx documentation, and OKF knowledge bundles** to showcase how single-query Hybrid RRF + lexical ranking eliminates the pre-router LLM call while catching exact SKUs, ZIP codes, and off-menu brands.

---

## Architectural Decisions (Resolved)

1. **Pure-SQL Hybrid RRF over `DBMS_HYBRID_VECTOR.SEARCH`**:
   - Oracle 26ai's `CTXSYS.CONTEXT` `CONTAINS`/`SCORE` uses Salton's inverse-frequency TF-IDF scoring (normalized 0–100); Oracle 26ai also supports `VECTOR(..., SPARSE)` for external BM25/SPLADE encoders.
   - Because Cymbal Coffee embeds 3,072-dimension `gemini-embedding-2` vectors client-side in Python (with an in-DB `embedding_cache`) and needs a **single query** spanning `chat_route`, `product`, and `coffee_store` plus per-term lexical hit counts, we use a pure-SQL CTE + `FULL OUTER JOIN` RRF query (`hybrid-search-turn`) paired with `CTX_DDL` `MULTI_COLUMN_DATASTORE` indexes (`product_hybrid_ctx_idx`, `store_hybrid_ctx_idx`, `chat_route_ctx_idx`).
   - Slides and docs present the lexical leg as **"BM25-style lexical ranking (Oracle Text `CONTAINS`/`SCORE`)"** and highlight Oracle 26ai `VECTOR(..., SPARSE)` as the native storage target when bringing external BM25/SPLADE sparse encoders.
2. **Delete `FlashLiteIntentClassifier`**:
   - `src/app/domain/chat/services/classifier.py` is deleted. Every chat turn embeds the user query once (using `embedding_cache`) and runs `hybrid-search-turn` + `hybrid-term-hits`. High-confidence deterministic routes (`PRODUCT_RAG`, `PRODUCT_AVAILABILITY`, `STORE_LOCATION`, `ORDER_STATUS`) dispatch directly with pre-fetched candidates; low-confidence or multi-intent turns enter the tool-equipped `AgentRuntime` with pre-fetched candidates injected into `CallContext`.
3. **Dedicated Queue `OracleAsyncConfig`**:
   - `litestar-queues`'s `SQLSpecBackend` mutates its `OracleAsyncConfig` to set `driver_features["enable_AutoLob"] = False` (`fetch_lobs=False`). `DatabaseSettings.get_queue_config()` constructs a dedicated `OracleAsyncConfig` instance for `SQLSpecBackendConfig` so `config.db` retains `fetch_lobs=True` for application CLOB/JSON queries.
4. **Security Boundary for Browser Chat vs Machine Protocols**:
   - `PublicController` in `litestar-security` 0.6.0 sets `exclude_from_csrf=True` on all routes. Browser cookie-session POST endpoints (`/api/chat/`, `/api/chat/stream`, `/api/chat/clear`, `/api/chat/location`) explicitly set `opt={"exclude_from_csrf": False}` so CSRF protection is enforced when `DEBUG=False`.
   - Machine endpoints (`/mcp`, `/a2a`, `/.well-known/agent-card.json`) remain CSRF-exempt and public by default, switching to `required(mechanism("api-key"))` (`X-API-Key` header) when `MCP_API_KEY` is set.

---

## Roadmap Chapters

| Order | Flow ID | Title | Depends On | Tasks | Summary |
| --- | --- | --- | --- | --- | --- |
| 1 | [`runtime-stabilization`](../runtime-stabilization/spec.md) | Native AI Runtime, Persistence, Streaming & Endpoint Stabilization | None | `1.1`–`1.4` | Fix all 11 runtime blockers: `0002` `agent_session`/`agent_event` migration, committing `Scope.APP` stores, non-partial event aggregation, `thought_signature`/call ID round-tripping, lowercase JSON Schema, full frontend `final` SSE contract, A2A owner context, `_vector.py` reserved `query` fix, HNSW `FETCH APPROX` SQL, and typed 503 `AIServiceUnconfigured`. |
| 2 | [`hybrid-rrf-retrieval`](../hybrid-rrf-retrieval/spec.md) | Single-Query Hybrid Lexical + Vector RRF Retrieval & Grounded Routing | `runtime-stabilization` | `2.1`–`2.4` | Add `MULTI_COLUMN_DATASTORE` Oracle Text indexes and `chat_route` exemplar table/fixtures; implement `hybrid-search-turn` and `hybrid-term-hits` SQL, `build_oracle_text_query`, `HybridRouteResolver`, grounded composers (`PRODUCT_RAG` + `term_hits` Folgers guard, `PRODUCT_AVAILABILITY`, `STORE_LOCATION`, `ORDER_STATUS`), 5 closure-bound agent tools, response cache/metrics restoration, and delete `FlashLiteIntentClassifier`. |
| 3 | [`platform-alignment`](../platform-alignment/spec.md) | Settings, DI, Services, LitestarMCP 0.15, and Security Alignment | `hybrid-rrf-retrieval` | `3.1`–`3.4` | Drop `sqlspec[adk]`, upgrade to `litestar-mcp>=0.15.0`, split `lib/settings/` and `ioc/` into packages, split monolithic `services.py` files into private `_*.py` modules, adopt `SkillController`/`PromptController`/`TurnBudget`/`AgentStreamFrame`/`SpanManager`, harden CSRF & optional `MCP_API_KEY`, add `GET /health`, and enforce Ruff `TID251` banned-API rules. |
| 4 | [`oracle-queues`](../oracle-queues/spec.md) | Oracle 26ai Background Task Queues (`litestar-queues`) | `platform-alignment` | `4.1`–`4.2` | Configure `litestar-queues[sqlspec]>=0.12.0` with a dedicated `OracleAsyncConfig`, wire `QueuePlugin` + `AutowirePlugin` job discovery, implement `system.cache_cleanup` and `products.embed_missing` tasks, and add `coffee worker` CLI commands and queue-backed `bulk-embed`. |
| 5 | [`slides-and-docs-refresh`](../slides-and-docs-refresh/spec.md) | Slides, Sphinx Documentation, and Knowledge Bundle Refresh | `oracle-queues` | `5.1`–`5.2` | Rewrite `SLIDES.md` around single-query Hybrid RRF + BM25-style lexical scoring and off-menu `term_hits` detection; update `AGENTS.md`, `README.md`, `docs/**` (`sphinx-build -W`), `cloudrun.tf`, and `.agents/bundles/{product,knowledge}/**`. |

---

## Requirement-to-Chapter Traceability

| Requirement ID | Requirement Summary | Owning Chapter | Tasks |
| --- | --- | --- | --- |
| `REQ-01` | Persist native agent sessions and events in Oracle 26ai with explicit commits and sequence ordering | `runtime-stabilization` | `1.1` |
| `REQ-02` | Fix streaming turn completion, tool loop `thought_signature`/call ID fidelity, and frontend `final` SSE contract | `runtime-stabilization` | `1.2` |
| `REQ-03` | Fix A2A owner task scoping, container lifecycle, and agent card dynamic URL | `runtime-stabilization` | `1.3` |
| `REQ-04` | Fix `/api/vector-search` reserved `query` param, HNSW `FETCH APPROX` SQL, and typed 503 on unconfigured AI | `runtime-stabilization` | `1.4` |
| `REQ-05` | Index multi-column product/store text and seed `chat_route` exemplars with 3,072-dim embeddings | `hybrid-rrf-retrieval` | `2.1` |
| `REQ-06` | Replace `FlashLiteIntentClassifier` with a single-query Oracle 26ai Hybrid RRF search and per-term lexical hit counter | `hybrid-rrf-retrieval` | `2.2`, `2.4` |
| `REQ-07` | Restore grounded deterministic routes (`PRODUCT_RAG`, `PRODUCT_AVAILABILITY`, `STORE_LOCATION`, `ORDER_STATUS`), Folgers off-menu guard, response cache, and search metrics | `hybrid-rrf-retrieval` | `2.3`, `2.4` |
| `REQ-08` | Modularize `lib/settings/`, `ioc/`, and domain `services/` packages; drop `sqlspec[adk]`; fix log middleware import/CORS bugs | `platform-alignment` | `3.1`, `3.2` |
| `REQ-09` | Adopt `litestar-mcp>=0.15.0` agent/skill/prompt primitives, CSRF/MCP security boundaries, `GET /health`, and Ruff `TID251` gates | `platform-alignment` | `3.3`, `3.4` |
| `REQ-10` | Configure `litestar-queues[sqlspec]>=0.12.0` on Oracle 26ai with isolated LOB config, scheduled cache cleanup, and async embedding jobs | `oracle-queues` | `4.1`, `4.2` |
| `REQ-11` | Update `SLIDES.md`, Sphinx docs, Terraform env vars, and OKF knowledge bundles to match the hybrid RRF + native runtime architecture | `slides-and-docs-refresh` | `5.1`, `5.2` |

---

## Global Constraints

1. **Zero Inline Comments in Python**: Never use inline `#` comments in Python files (except required `# noqa:` directives or `# docs:start-*` / `# docs:end-*` Sphinx literalinclude anchors). Explain rationale in Google-style docstrings.
2. **Modern Python Typing & Structure**: Use PEP 585/604 types (`list[str]`, `X | None`), `msgspec.Struct` for API/service schemas, module layout (`docstring` $\rightarrow$ grouped top-level imports $\rightarrow$ `__all__` $\rightarrow$ public classes/functions $\rightarrow$ private `_...` helpers), and class layout (class attributes $\rightarrow$ `__init__` $\rightarrow$ properties $\rightarrow$ public methods $\rightarrow$ private `_...` methods).
3. **Dishka DI & `ioc` Rules**: `src/app/ioc/` modules must never include `from __future__ import annotations`. Controller handlers use `Inject[T]` without `@inject` decorators.
4. **Coordinate Privacy**: Browser geolocation coordinates (`user_lat`, `user_lng`, `ChatLocationInput`) remain strictly request-scoped and must never be persisted to `agent_session`, `agent_event`, `response_cache`, `search_metrics`, or logs.
5. **Oracle 26ai & SQLSpec Discipline**: All SQL lives in named queries under `src/app/db/sql/*.sql` using `:name` binds and `TO_VECTOR(:vec, 3072, FLOAT32)`. Vector top-$k$ queries use `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX FIRST :limit ROWS ONLY` so the HNSW index is used.

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `coffee-agent-stabilization-and-hybrid-search` (`completed`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `2026-10-12T20:48:00Z`
- **Key Decisions**:
  - Pure-SQL Hybrid RRF (`hybrid-search-turn` + `hybrid-term-hits`) with `CTX_DDL` `MULTI_COLUMN_DATASTORE` preferences replaces `FlashLiteIntentClassifier`.
  - `OracleSessionStore` and `OracleEventStore` run at `Scope.APP` over `db_manager.provide_session()` with explicit `await driver.commit()`.
  - `DatabaseSettings.get_queue_config()` creates a dedicated `OracleAsyncConfig` for `litestar-queues` so `config.db` preserves `fetch_lobs=True`.
  - Browser chat POST endpoints enforce CSRF when `DEBUG=False`; `/mcp` and `/a2a` stay CSRF-exempt with optional `MCP_API_KEY` header authentication.
- **Newest Discoveries**:
  1. `ai-runtime.sql` references non-existent `adk_session`/`adk_event` tables and `_store.py` never commits (`AI-01`, `AI-04`).
  2. `GeminiModelClient.generate_stream` only yields `partial=True`, causing every turn to fail with `stream_incomplete` (`AI-02`, `CP-01`).
  3. `GET /api/vector-search` uses reserved parameter name `query` (`CP-08`) and `vector-search-products` orders by `similarity_score DESC`, bypassing HNSW (`CP-07`).
  4. Oracle Text `CONTAINS`/`SCORE` uses Salton TF-IDF (0–100) while `VECTOR(..., SPARSE)` supports external BM25 encoders (`research_oracle_hybrid_rrf_20261012`).
  5. `SQLSpecBackend._disable_oracle_lob_wrapping` sets `enable_AutoLob=False` on its `OracleAsyncConfig`, requiring a separate config instance (`research_codebase_audit_and_reference_patterns_20261012`).
- **Blockers & Unblock Conditions**: None
- **Next Exact Step**: Run `/flow:implement runtime-stabilization` starting with Task `runtime-stabilization:1.1`.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/knowledge/guides/architecture.md`
  - `.agents/bundles/knowledge/guides/oracle-database.md`
  - `.agents/bundles/knowledge/guides/agentic-ai-runtime.md`
  - `.agents/bundles/knowledge/guides/store-inventory-maps.md`
