---
type: Guide
title: Chat, Products, Stores, APEX, System & Web Domains
description: Hybrid RRF routing, grounded composers, HNSW product/store queries, APEX REST and Vertex AI gateway controllers, maps, cache, metrics, background jobs, and UI templates
tags:
  - chat
  - products
  - stores
  - apex
  - maps
  - htmx
---

# Chat, Products, Stores, APEX, System & Web Domains

## 1. Chat Domain (`src/app/domain/chat/`)

- `CoffeeChatController` (`controllers/_chat.py` & `controllers/_helpers.py`) and session helpers (`_session.py`: `chat_session_identity`, `clear_chat_session_id`): Serve `POST /api/chat/stream` (`ServerSentEvent`) and `POST /api/chat/session/clear`, bridging Litestar cookie session IDs to `AgentOrchestrationService`.
- Schemas (`schemas/_chat.py`, `schemas/_forms.py`, `schemas/_hybrid.py`): `FrozenBaseStruct` and `CamelizedFrozenStruct` DTOs for chat payloads, location/form inputs, and Hybrid RRF routing results.
- `HybridRouteResolver` (`services/_router.py`): Executes `hybrid-search-turn` and `hybrid-term-hits` (`src/app/db/sql/hybrid.sql`), extracts brand candidates via `extract_candidate_terms()`, and sanitizes Oracle Text queries via `build_oracle_text_query()` (`src/app/lib/text_search.py`).
- `GroundedRouteService` (`services/_grounded.py`) & Composers (`services/_composers.py`): Deterministically compose `GroundedTurnResult` responses for `PRODUCT_RAG` (including off-menu brand refusals with in-stock alternatives), `STORE_LOCATION`, `PRODUCT_AVAILABILITY` (with pronoun resolution from `last_products`), and `ORDER_STATUS`.
- Telemetry helpers (`services/_telemetry.py`): Build `SQLPhase`, `SearchMetrics` (including `ai_ms` and `grounded_answer_ms`), map action links (`build_map_actions`), and sanitized location contexts (`safe_location_context`).

## 2. Products, Stores, Maps & APEX (`src/app/domain/products/` & `src/apex/cymbal-coffee-ops/`)

- **Controllers (`src/app/domain/products/controllers/`)**:
  - `ProductController` & `StoreController` (`_products.py`): Paginated `/api/products` and `/api/stores` REST routes, HTMX store inventory partial, and `mcp_tool` handlers (`get_product`, `get_store_inventory`).
  - `VectorController` (`_vector.py`): `POST /api/vector-demo` (Hybrid RRF / HNSW search returning HTMX partial or JSON), `GET /api/explain-plan` (`DBMS_XPLAN.DISPLAY()`), and `GET /api/vector-search` (`mcp_tool="search_products"`).
  - `ApexController` (`_apex.py`, DTOs in `schemas/_apex.py`): `/api/apex/*` REST Source Catalog endpoints (`/products`, `/stores`, `/inventory/summary`, `/stores/{store_id}/inventory`, `/products/{product_id}/availability`, `/recommendations`, `/vector/status`, `/openapi/status`).
  - `ApexAIController` (`_apex_ai.py`, DTOs in `schemas/_apex_ai.py`): OpenAI-compatible Vertex AI gateway (`GET /api/apex/ai/v1/models` and `POST /api/apex/ai/v1/chat/completions`) backed by `GeminiModelClient` with optional constant-time `APEX_GATEWAY_API_KEY` Bearer checks, paired with `ApexVertexConfigurator` (`tools/oracle/apex_vertex.py`) and APEX 26.1 App ID `100` (`src/apex/cymbal-coffee-ops/`, Page 6 `src/apex/cymbal-coffee-ops/pages/p00006-vector-recommendations.apx` calling `APEX_AI.GENERATE` with `COFFEE_VERTEX_AI`).
- **Services & Background Jobs (`src/app/domain/products/services/` & `src/app/domain/products/jobs.py`)**:
  - `ProductService` (`services/_products.py`, DTOs in `schemas/_products.py`): Extending `OracleLoaderService` for HNSW vector search (`vector-search-products` and store-filtered `vector-search-products-by-store`), Hybrid RRF search (`hybrid-search-products`), paginated catalog and vector-readiness reads, and product/route embedding updates.
  - `OracleVectorSearchService` (`services/_vector.py`): Executes vector/hybrid demo searches, index diagnostics, and `DBMS_XPLAN.DISPLAY()` execution plan inspection.
  - `StoreService` (`services/_stores.py`) & `services/_location.py`: Haversine nearest-store ranking (`haversine_miles`, `store_matches_hint`), store hours lookup (`get_store_hours`), and `store_product_inventory` store/product availability and summary queries.
  - `VertexAIService` (`services/_embedding.py`): Generates 3072-dimension `gemini-embedding-2` embeddings (`embedding_purpose="query"` or `"document"`) with Oracle `embedding_cache` backing (while `AIProvider.provide_genai_client()` in `src/app/ioc/_ai.py` raises `AIServiceUnconfigured` for HTTP 503 handling when Vertex AI project/API-key settings are unconfigured or placeholders).
  - Google Maps (`services/_maps.py`): `build_store_search_url()` and `build_store_directions_url()` build keyless URLs (`https://www.google.com/maps/search/?api=1&...` and `https://www.google.com/maps/dir/?api=1&...`); browser coordinates are strictly opt-in and never persisted.
  - `embed_missing_records` (`jobs.py`): `@task("products.embed_missing")` batch-embeds products and routes (`uv run coffee bulk-embed` dispatches via `QueueService.enqueue(..., execution_backend="immediate")`).

## 3. System & Web Domains (`src/app/domain/system/` & `src/app/domain/web/`)

- **System Controllers, Services & Jobs (`src/app/domain/system/`)**: `SystemController` (`controllers/_system.py`) and `MetricsController` (`controllers/_metrics.py`) expose `/health`, `/api/system/health`, `/api/metrics/summary`, and `/api/metrics/charts`, backed by `CacheService` (`services/_cache.py`, `schemas/_cache.py`), `MetricsService` (`services/_metrics.py`, `schemas/_metrics.py` writing `search_metric`), `PersonaManager` (`services/_personas.py`, `schemas/_persona.py`), and `cleanup_expired_cache_and_sessions` (`@task("system.cache_cleanup")` in `jobs.py`).
- **Web Controller & Templates (`src/app/domain/web/`)**: `PageController` (`controllers/_pages.py`) renders Jinja2 + HTMX 2.x + Tailwind CSS v4 views (`/` via `templates/pages/chat.html.j2` and `/explore` via `templates/pages/explore.html.j2`, shared layout in `templates/base.html.j2` and `templates/partials/`) with client-side Vite assets under `src/resources/`.
