---
type: Guide
title: Chat, Products, Stores, System & Web Domains
description: Hybrid RRF routing, grounded composers, HNSW product/store queries, maps, cache, metrics, and UI templates
tags:
  - chat
  - products
  - stores
  - maps
  - htmx
---

# Chat, Products, Stores, System & Web Domains

## 1. Chat Domain (`src/app/domain/chat/`)

- `CoffeeChatController` (`controllers/_chat.py`): Serves `POST /api/chat/stream` (`ServerSentEvent`) and `POST /api/chat/session/clear`, bridging Litestar cookie session IDs to `AgentOrchestrationService`.
- `HybridRouteResolver` (`services/_router.py`): Executes `hybrid-search-turn` and `hybrid-term-hits` (`src/app/db/sql/hybrid.sql`) and sanitizes Oracle Text queries via `build_oracle_text_query`.
- `GroundedRouteService` (`services/_grounded.py`): Deterministically composes `PRODUCT_RAG` (including off-menu brand refusals with in-stock alternatives), `STORE_LOCATION`, `PRODUCT_AVAILABILITY` (with pronoun resolution from `last_products`), and `ORDER_STATUS`.
- Telemetry helpers (`services/_telemetry.py`): Build `SQLPhase`, `SearchMetrics` (including `ai_ms` and `grounded_answer_ms`), `MapAction`, and sanitize location contexts (`safe_location_context`).

## 2. Products, Stores & Maps (`src/app/domain/products/`)

- `ProductService` (`services/_products.py`): HNSW vector search (`vector-search-products`), Hybrid RRF search (`search-products-hybrid` with defensive brace-escaping), catalog lookups, and Oracle `EXPLAIN PLAN` inspection (`OracleVectorSearchService` in `services/_embedding.py`).
- `StoreService` (`services/_stores.py`), `_location.py`, & `_maps.py`: Haversine nearest-store calculations (`haversine_miles`), store hours evaluation, `store_product_inventory` availability checks, and store-filtered HNSW vector search (`vector-search-products-by-store`).
- `VertexAIService` (`services/_embedding.py`): Generates 3072-dimension `gemini-embedding-2` embeddings (`embedding_purpose="query"` or `"document"`) with Oracle `embedding_cache` backing and typed 503 `AIServiceUnconfigured` errors when `GOOGLE_CLOUD_PROJECT` is a placeholder.
- Background task (`tasks.py`): `@task("products.embed_missing")` batch-embeds products and routes (`uv run coffee bulk-embed` dispatches through `QueueService.enqueue(..., execution_backend="immediate")`).
- Google Maps (`services/_maps.py`): Uses keyless search/directions URLs (`https://www.google.com/maps/search/?api=1&...` and `https://www.google.com/maps/dir/?api=1&...`). Browser coordinates are strictly opt-in and never persisted.

## 3. System & Web Domains (`src/app/domain/system/` & `src/app/domain/web/`)

- `CacheService` (`domain/system/services/_cache.py`), `PersonaManager`, & `MetricsCollector` (`domain/system/services/_health.py`): Manage `response_cache`, `embedding_cache`, personas, and `search_metrics` tables in Oracle 26ai.
- Background task (`domain/system/tasks.py`): `@task("system.cache_cleanup")` purges expired cache entries.
- `PageController` & Templates (`domain/web/`): Render Jinja2 + HTMX 2.x + Tailwind CSS v4 views (`/` and `/explore`) with client-side Vite assets under `src/resources/`.
