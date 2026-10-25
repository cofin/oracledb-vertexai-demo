---
type: Spec
flow_id: domain-standardization-and-debloat
title: Domain Service Standardization, Frozen Wire Models, MyPyC-Safe Fallbacks, and Dead-Code Removal
state: completed
plan_revision: 1
plan_commit: "7ff2771"
state_revision: 4
current_task: null
last_operation: complete
operation_targets:
  - "2.1"
  - "2.2"
  - "2.3"
  - "2.4"
last_verified_checkpoint: "5e3fd17"
created_at: 2026-10-24T19:29:00Z
updated_at: 2026-10-25T15:59:30Z
description: Second stacked PR migrating system, chat, ai, products, and web domains to OracleLoaderService, FrozenBaseStruct, and centralized serialization, extracting shared Oracle Text sanitization, splitting oversized modules, fixing mypyc-safe post-except SQLSpec fallbacks and DFW city filters, and deleting legacy wrappers, aliases, and banned-api ignores.
tags:
  - refactor
  - domain
  - sqlspec
  - msgspec
  - debloat
parent_prd: platform-alignment-apex-vertex-prd
research: []
---

# Flow: Domain Service Standardization, Frozen Wire Models, MyPyC-Safe Fallbacks, and Dead-Code Removal

**Flow ID:** `domain-standardization-and-debloat`
**Parent PRD:** [`platform-alignment-apex-vertex-prd`](../platform-alignment-apex-vertex-prd/spec.md)
**Depends On:** [`sqlspec-069-and-core-foundation`](../sqlspec-069-and-core-foundation/spec.md) (PR 2 of 5 in stack)
**Proposed Branch & PR Title:** `refactor/domain-standardization` — `refactor(domain): standardize loader services, frozen schemas, and module boundaries`

---

## Specification

### Code Analysis Summary

Files examined:

- `src/app/domain/system/` (`src/app/db/sql/system.sql:1-77`, `services/{_cache,_health,__init__}.py`, `schemas/{_cache,_metrics,__init__}.py`) — Imports `from app.config import db_manager` directly, uses non-atomic `DELETE` + `INSERT` cache writes instead of `MERGE INTO`, compares overlapping metric time windows in `system.sql`, bundles `PersonaManager` and `MetricsService` inside `_health.py`, and keeps `ResponseCacheService` and `SystemService` aliases.
- `src/app/domain/chat/` (`services/{_router,_grounded,_telemetry}.py`, `controllers/{_chat,_helpers}.py`, `schemas/{_chat,_hybrid}.py`, `{exceptions,session}.py`) — `_router.py` and `products/services/_products.py` duplicate Oracle Text reserved-word/token sanitization; `_grounded.py` spans 835 lines mixing orchestration and Markdown composers; `_telemetry.py` `_KNOWN_CITY_FILTERS` omits seeded DFW cities (`plano`, `fort worth`, `arlington`, `frisco`, `irving`); `_helpers.py` defines `CoffeeChatForm` inside `controllers/` instead of `schemas/_forms.py`; `exceptions.py` and `session.py` are non-underscored legacy files.
- `src/app/domain/ai/` (`src/app/db/sql/ai-runtime.sql:1-78`, `runtime/{_context,_model,_spec,_store,_stream,_tools,_types}.py`, `a2a/{card,executor}.py`, `services/{agent_service,_tools}.py`) — `list-ai-events` slices `[:limit]` in Python instead of pushing `FETCH FIRST :limit ROWS ONLY` into Oracle SQL; `_store.py` imports `db_manager` and `json.loads`; `_context.py` retains unused `RunContextRegistry` and unused fields on `CoffeeToolContext` (`InventoryService`, `MapsService`, `EmbeddingService`); `a2a/{card,executor}.py` and `services/agent_service.py` (683 lines) use public module filenames instead of focused private `_*` modules; `_tools.py` keeps unused `CoffeeToolServices`.
- `src/app/domain/products/` & `web/` (`services/{_products,_stores,_embedding,_inventory,_maps}.py`, `controllers/{_products,_vector,_vector_helpers,_apex}.py`, `jobs.py`, `src/app/cli/_helpers/embeddings.py`, `web/controllers/_pages.py`) — `ProductService.list_products` performs two manual count/select queries instead of `paginate_limit_offset`; `products/jobs.py` imports UI-coupled `cli._helpers.embeddings` (`rich.Progress`) inside a background worker job; `_apex.py:134-145` executes fallback SQLSpec queries *inside* an `except:` block (unsafe under `sqlspec[mypyc]`); `_inventory.py` (`InventoryService`), `MapsService`, `EmbeddingService`, and `_vector_helpers.py` add unnecessary indirection; `pyproject.toml:305-313` carries `TID251` `banned-api` ignores that are no longer needed once all domains use `PublicController` and `FrozenBaseStruct`.

### Relevant Patterns

- [AI Runtime & Protocols (`domain/ai/`)](../../knowledge/domains/ai-and-protocols.md) — `Scope.APP` stores with explicit `commit()`, non-partial event aggregation, coordinate non-persistence.
- [Chat, Products, Stores & System Domains](../../knowledge/domains/chat-products-stores-system.md) — Single-query Hybrid RRF routing, off-menu brand guard (`hybrid-term-hits`), two-level store inventory precedence.
- [Code Style Patterns](../../knowledge/patterns/code-style.md) — Private `_*` implementation modules re-exported via `__init__.py`, `FrozenBaseStruct` (`frozen=True, gc=False`), centralized `app.utils.serialization`.

### Requirements

- **PLAT-REQ-05 (`system` Domain Standardization)**:
  - Convert cache writes in `src/app/db/sql/system.sql` to atomic `MERGE INTO` statements and parameterize disjoint metric windows (`:window_start_hours`, `:window_end_hours`).
  - Migrate `src/app/domain/system/schemas/` (`_cache.py`, `_metrics.py`, `_persona.py`) to `FrozenBaseStruct` / `CamelizedFrozenStruct`.
  - Migrate `CacheService` (`_cache.py`), `PersonaManager` (`_personas.py`), and `MetricsService` (`_metrics.py`) to `OracleLoaderService` and `app.utils.serialization`, deleting `_health.py` and removing `ResponseCacheService` and `SystemService` aliases.
- **PLAT-REQ-06 (Shared `text_search.py` & `chat` Domain Standardization)**:
  - Create `src/app/lib/text_search.py` providing shared Oracle Text reserved-word/stopword sanitization (`build_oracle_text_query`, `build_oracle_proximity_query`).
  - Create `src/app/domain/chat/_session.py` and `src/app/domain/chat/schemas/_forms.py`, migrate chat schemas to `FrozenBaseStruct` / `CamelizedFrozenStruct`, migrate `HybridRouteResolver` (`_router.py`) to `OracleLoaderService` + `app.lib.text_search`, split Markdown route composers into `src/app/domain/chat/services/_composers.py` out of `_grounded.py`, and update `_KNOWN_CITY_FILTERS` in `_telemetry.py` to include all seeded DFW store cities (`dallas`, `plano`, `fort worth`, `arlington`, `frisco`, `irving`).
- **PLAT-REQ-07 (`ai` Domain Standardization & Store/Context Cleanup)**:
  - Push `FETCH FIRST :limit ROWS ONLY` into `list-ai-events` in `src/app/db/sql/ai-runtime.sql`.
  - Migrate `OracleSessionStore` and `OracleEventStore` (`runtime/_store.py`) to `OracleLoaderService` + `app.utils.serialization`, migrate `runtime/_types.py` wire structs to `FrozenBaseStruct`, and delete `RunContextRegistry` and dead `EmbeddingService` / `InventoryService` / `MapsService` fields from `CoffeeToolContext` (`runtime/_context.py`).
  - Rename `a2a/{card,executor}.py` to `a2a/{_card,_executor}.py`, split `services/agent_service.py` into `services/_agent.py` and `services/_history.py`, delete `CoffeeToolServices` from `services/_tools.py`, and update `src/app/ioc/_ai.py` and `src/app/server/plugins.py`.
- **PLAT-REQ-08 (`products` & `web` Domains, MyPyC-Safe Fallbacks & Final Alias / `banned-api` Purge)**:
  - Migrate `products/schemas/{_products,_apex}.py` to `FrozenBaseStruct` / `CamelizedFrozenStruct` (adding `RecommendationMode = Literal["hybrid", "vector", "fallback"]` and `hybrid_rrf_ready: bool` on `ApexVectorStatus`).
  - Migrate `ProductService` (`_products.py`, using `paginate_limit_offset` and `app.lib.text_search`), `StoreService` (`_stores.py`), `VertexAIService` (`_embedding.py`, owning pure async `embed_missing_products` decoupled from Rich CLI progress), and `OracleVectorSearchService` (extracted to `_vector.py` with mypyc-safe post-`except:` SQLSpec fallback recommendations and vector/hybrid readiness checks) to `OracleLoaderService`.
  - Delete `products/services/_inventory.py`, `MapsService` in `_maps.py` (retaining `build_store_search_url` and `build_store_directions_url`), `EmbeddingService`, `products/controllers/_vector_helpers.py`, `chat/{exceptions,session}.py`, `BaseStruct` / `CamelizedBaseStruct` in `src/app/lib/schema.py`, and lines `305-313` (`banned-api` ignores) in `pyproject.toml`.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `PLAT-REQ-05` | `2.1` | `behavior_tdd` | `src/app/db/sql/system.sql`, `src/app/domain/system/{schemas,services,controllers,jobs}*` | `src/tests/unit/domain/system/services/test_cache.py`, `src/tests/unit/domain/system/services/test_metrics.py`, `src/tests/unit/db/test_named_sql.py` |
| `PLAT-REQ-06` | `2.2` | `behavior_tdd` | `src/app/lib/text_search.py`, `src/app/domain/chat/{_session,schemas,services,controllers}*` | `src/tests/unit/domain/chat/services/test_hybrid_router.py`, `src/tests/unit/domain/chat/services/test_grounded_routes.py`, `src/tests/unit/domain/chat/controllers/test_chat_controller.py` |
| `PLAT-REQ-07` | `2.3` | `behavior_tdd` | `src/app/db/sql/ai-runtime.sql`, `src/app/domain/ai/{runtime,a2a,services}*`, `src/app/ioc/_ai.py`, `src/app/server/plugins.py` | `src/tests/unit/domain/ai/runtime/test_loop_stream.py`, `src/tests/unit/domain/ai/runtime/test_model_store.py`, `src/tests/unit/domain/ai/runtime/test_tools.py`, `src/tests/unit/domain/ai/a2a/test_a2a.py`, `src/tests/unit/domain/ai/test_agent_orchestration.py`, `src/tests/unit/domain/ai/test_mcp_controllers.py` |
| `PLAT-REQ-08` | `2.4` | `behavior_tdd` | `src/app/domain/products/{schemas,services,controllers,jobs}*`, `src/app/cli/_helpers/embeddings.py`, `src/app/domain/web/controllers/_pages.py`, `src/app/domain/chat/{exceptions,session}.py`, `src/app/ioc/_domain.py`, `src/app/lib/schema.py`, `pyproject.toml` | `src/tests/unit/domain/products/controllers/test_apex.py`, `src/tests/unit/domain/products/controllers/test_vector.py`, `src/tests/unit/domain/products/services/{test_maps,test_store_service,test_vertex_ai_service}.py`, `src/tests/unit/domain/web/controllers/test_pages.py`, `src/tests/unit/domain/test_background_jobs.py` |

---

## Implementation Plan

### Phase 1: System, Chat, AI, and Products/Web Domain Standardization & Debloat

- [x] 2.1 Standardize `system` domain on `OracleLoaderService`, `FrozenBaseStruct`, atomic `MERGE INTO` cache SQL, and split `_personas.py` / `_metrics.py` [`9d08f1f`]
- [x] 2.2 Extract `src/app/lib/text_search.py` and standardize `chat` domain (`_session.py`, `schemas/_forms.py`, split `_composers.py`, seeded DFW city filters) [`60414e9`]
- [x] 2.3 Standardize `ai` domain (`OracleLoaderService` stores, SQL `:limit` pushdown, `_card.py` / `_executor.py`, `_agent.py` / `_history.py`, delete `RunContextRegistry` & `CoffeeToolServices`) [`a7c83ec`]
- [x] 2.4 Standardize `products` and `web` domains (`_vector.py`, mypyc-safe fallbacks, pure async batch embedding), delete dead wrappers/aliases, and remove `pyproject.toml` `banned-api` ignores [`5e3fd17`]

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `domain-standardization-and-debloat` (`completed`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `5e3fd17`
- **Key Decisions**:
  - Execute Task `2.3` (`ai` domain) before Task `2.4` (`products` & `web` domains) so `_context.py` and `_agent.py` drop `EmbeddingService`, `InventoryService`, and `MapsService` imports before Task `2.4` deletes them from `products/services/`, keeping every intermediate commit green with zero overlapping `files:`.
  - Keep `src/tests/unit/db/test_named_sql.py` inspecting `<target>.get_sql(...)` call sites so named-SQL parity remains enforced across all `OracleLoaderService` subclasses.
- **Newest Discoveries**:
  1. Executing fallback SQLSpec queries *after* exiting `except:` in `OracleVectorSearchService` (`_vector.py`) prevents `sqlspec[mypyc]` compiled frames from observing active `sys.exc_info()` state.
  2. Keeping `products` free of `chat` imports (`ai -> chat -> products -> system/lib`) prevents circular package initialization when `chat/services/_telemetry.py` imports URL builders from `app.domain.products.services`.
- **Blockers & Unblock Conditions**: None
- **Next Exact Step**: Proceed to PR 3 (`adb-free-26ai-and-tools-hygiene`) on branch `feat/adb-free-26ai-runtime`.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: "7ff2771"`
- **State Identity**: `state_revision: 4`, `last_operation: complete`, `operation_targets: ["2.1", "2.2", "2.3", "2.4"]`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/platform-alignment-apex-vertex-prd/research/codebase-alignment-and-apex/research.md`
  - `.agents/bundles/knowledge/domains/ai-and-protocols.md`
  - `.agents/bundles/knowledge/domains/chat-products-stores-system.md`
