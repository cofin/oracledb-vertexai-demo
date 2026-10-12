---
type: Spec
flow_id: hybrid-rrf-retrieval
title: Single-Query Hybrid Lexical + Vector RRF Retrieval & Grounded Routing
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
description: Replace FlashLiteIntentClassifier and separate vector searches with a single Oracle 26ai Hybrid RRF SQL query (CONTAINS/SCORE + VECTOR_DISTANCE), restore deterministic grounded routes and Folgers off-menu term_hits detection, and bind 5 grounded tools into AgentRuntime.
tags:
  - feature
  - oracle
  - hybrid-search
  - rrf
  - ai
parent_prd: coffee-agent-stabilization-and-hybrid-search
research:
  - research/research_oracle_hybrid_rrf_20261012/research.md
---

# Flow: Single-Query Hybrid Lexical + Vector RRF Retrieval & Grounded Routing

**Flow ID:** `hybrid-rrf-retrieval`
**Parent PRD:** [`coffee-agent-stabilization-and-hybrid-search`](../coffee-agent-stabilization-and-hybrid-search/spec.md)
**Depends On:** [`runtime-stabilization`](../runtime-stabilization/spec.md)

---

## Specification

### Code Analysis Summary

Files examined on `feat/gemini-embeddings` (`@3a3cbd1`) and compared against `main` (`@2633e2e`):

- `src/app/db/migrations/0001_cymball_coffee_products.sql:46-47` — Defines two single-column `CTXSYS.CONTEXT` indexes (`product_name_idx`, `product_desc_idx`) without `SYNC (ON COMMIT)` and without indexing `category`, `origin`, `roast_level`, `flavor_profile`, or `coffee_store` location fields (`CP-09`). Also defines `intent_exemplar` (`0001:122-135`), which is unseeded and unused.
- `src/app/domain/chat/services/classifier.py:1-151` — `FlashLiteIntentClassifier` makes a separate Gemini LLM call before retrieval (`AI-10`, `CP-06`), adding ~300–500 ms of latency and failing to detect exact lexical tokens (SKUs, ZIP codes, off-menu brand names like `"Folgers"`).
- `src/app/domain/ai/services/agent_service.py:22-42` — `get_coffee_spec_tree()` registers `tools=()`, and all deterministic grounded handlers (`PRODUCT_RAG`, `PRODUCT_AVAILABILITY`, `STORE_LOCATION`, `ORDER_STATUS`), response caching, and search metrics recording from `main:src/app/domain/chat/services/{adk,_adk_grounding,_adk_support}.py` were dropped (`AI-03`, `CP-05`, `CP-06`).
- `src/app/db/utils.py:18-24` & `src/app/cli/_helpers/{embeddings,fixtures}.py` — Fixture loader and `bulk-embed` only handle `product`, `coffee_store`, and `store_product_inventory`.

### Relevant Patterns

- [SQLSpec Services](../../knowledge/patterns/sqlspec-services.md) — Named SQL files in `src/app/db/sql/*.sql`, `TO_VECTOR(:query_vector, 3072, FLOAT32)`, typed `schema_type` mapping.
- [Vertex AI Integration](../../knowledge/patterns/vertex-ai.md) — `embedding_purpose="query"` for user search turns and `embedding_purpose="document"` for catalog/exemplar documents.
- [Store, Inventory & Maps Guide](../../knowledge/guides/store-inventory-maps.md) — Request-scoped coordinates, no-key Google Maps URLs, deterministic `STORE_LOCATION` and `PRODUCT_AVAILABILITY` grounding.

### Requirements

- **REQ-05 (Multi-Column Oracle Text & Route Exemplar Schema)**: Extend `0002_agent_runtime_and_hybrid_search.sql` to create `CTX_DDL` `MULTI_COLUMN_DATASTORE` preferences (`product_search_ds`, `store_search_ds`) with `SYNC (ON COMMIT)` `CTXSYS.CONTEXT` indexes (`product_hybrid_ctx_idx`, `store_hybrid_ctx_idx`), drop `intent_exemplar`, create `chat_route` (`id`, `route_label`, `title`, `exemplar_text`, `keywords`, `embedding VECTOR(3072, FLOAT32)` with `chat_route_ctx_idx` and `chat_route_embedding_idx`), seed `src/app/db/fixtures/chat_route.json`, and wire `chat_route` into `db/utils.py`, `cli/_helpers/embeddings.py`, and `cli/_helpers/fixtures.py`.
- **REQ-06 (Single-Query Hybrid RRF & Lexical Term Hits)**: Create `src/app/db/sql/hybrid.sql` with `hybrid-search-turn` (fusing `CONTAINS`/`SCORE` lexical ranks and `VECTOR_DISTANCE` `FETCH APPROX` ranks across `chat_route`, `product`, and `coffee_store` via RRF with $k=60$) and `hybrid-term-hits` (`JSON_TABLE(:terms_json)` per-term lexical hit counts on `product`), plus `build_oracle_text_query` and `HybridRouteResolver` in `src/app/domain/chat/services/_router.py`.
- **REQ-07 (Grounded Composers, Tools, Cache & Classifier Removal)**: Restore grounded deterministic handlers (`PRODUCT_RAG` with `term_hits == 0` off-menu guard for `"Folgers"`, `PRODUCT_AVAILABILITY`, `STORE_LOCATION`, `ORDER_STATUS`) in `src/app/domain/chat/services/_grounded.py` and telemetry builders in `_telemetry.py`, bind 5 grounded tools (`search_products`, `get_product_details`, `find_nearby_stores`, `check_product_availability`, `check_order_status`) in `src/app/domain/ai/services/_tools.py`, restore `response_cache` and `record_search_metrics` in `agent_service.py` / `_chat.py`, and delete `src/app/domain/chat/services/classifier.py` and `src/tests/unit/app/domain/chat/services/test_classifier.py`.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `REQ-05` | `2.1` | `behavior_tdd` | `src/app/db/migrations/0002_agent_runtime_and_hybrid_search.sql`, `src/app/db/fixtures/chat_route.json`, `src/app/db/sql/products.sql`, `src/app/db/utils.py`, `src/app/cli/_helpers/embeddings.py`, `src/app/cli/_helpers/fixtures.py` | `src/tests/unit/app/cli/test_fixtures_and_embeddings.py` |
| `REQ-06` | `2.2` | `behavior_tdd` | `src/app/db/sql/hybrid.sql`, `src/app/config.py`, `src/app/domain/chat/schemas/_hybrid.py`, `src/app/domain/chat/services/_router.py`, `src/tests/fixtures/routing_golden.jsonl` | `src/tests/unit/app/domain/chat/services/test_hybrid_router.py` |
| `REQ-07` | `2.3` | `behavior_tdd` | `src/app/domain/chat/services/_grounded.py`, `src/app/domain/chat/services/_telemetry.py`, `src/app/domain/chat/services/__init__.py` | `src/tests/unit/app/domain/chat/services/test_grounded_routes.py` |
| `REQ-06`, `REQ-07` | `2.4` | `behavior_tdd` | `src/app/domain/ai/services/_tools.py`, `src/app/domain/ai/services/agent_service.py`, `src/app/domain/chat/controllers/_chat.py`, `src/app/domain/chat/services/classifier.py`, `src/app/ioc.py` | `src/tests/unit/app/domain/ai/test_agent_orchestration.py`, `src/tests/unit/app/domain/chat/controllers/test_chat_controller.py` |

---

## Implementation Plan

### Phase 1: Hybrid Schema, Exemplar Fixtures & Single-Query RRF Router

- [ ] 2.1 Add `MULTI_COLUMN_DATASTORE` Oracle Text indexes and `chat_route` table/fixtures to migration `0002` and CLI helpers
- [ ] 2.2 Implement `hybrid.sql` (`hybrid-search-turn` and `hybrid-term-hits`), `build_oracle_text_query`, and `HybridRouteResolver`

### Phase 2: Grounded Composers, Agent Tools & Classifier Removal

- [ ] 2.3 Implement grounded route composers (`_grounded.py`) with `term_hits` off-menu guard and telemetry builders (`_telemetry.py`)
- [ ] 2.4 Register 5 grounded agent tools (`_tools.py`), wire single-query hybrid routing + cache/metrics into `agent_service.py`, and delete `classifier.py`

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `hybrid-rrf-retrieval` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - Use pure-SQL RRF (`hybrid-search-turn`) combining `CTXSYS.CONTEXT` (`MULTI_COLUMN_DATASTORE` with `SYNC (ON COMMIT)`) and `VECTOR_DISTANCE` (`FETCH APPROX`) across `chat_route`, `product`, and `coffee_store` in one round trip.
  - Use `hybrid-term-hits` (`JSON_TABLE(:terms_json)`) to detect zero-hit brand/proper-noun terms (`"Folgers"` $\rightarrow 0$ hits) deterministically without hardcoded brand blocklists.
  - Delete `FlashLiteIntentClassifier` (`classifier.py`).
- **Newest Discoveries**:
  1. `0001` Oracle Text indexes omit `SYNC (ON COMMIT)` and do not cover `category`, `origin`, `roast_level`, `flavor_profile`, or store location columns (`CP-09`).
  2. Oracle Text `CONTAINS` throws `DRG-50901` on unescaped punctuation or reserved keywords unless tokens are wrapped in `{token}` braces (`research_oracle_hybrid_rrf_20261012`).
- **Blockers & Unblock Conditions**: Depends on `runtime-stabilization`.
- **Next Exact Step**: Claim and execute Task `2.1` (`tasks/2.1.md`) after `runtime-stabilization` completes.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/hybrid-rrf-retrieval/research/research_oracle_hybrid_rrf_20261012/research.md`
  - `.agents/bundles/knowledge/guides/oracle-database.md`
  - `.agents/bundles/knowledge/guides/store-inventory-maps.md`
