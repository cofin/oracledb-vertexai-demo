# Web, HTMX & Frontend Review Checklist

## HTMX, SSE & Keyless Maps Rules

1. **`litestar_htmx` Imports, `PageController` & Partial Response Types**:
   - Always import HTMX types from `litestar_htmx` (`HTMXPlugin`, `HTMXRequest`, `HTMXTemplate`), never from the deprecated `litestar.plugins.htmx` shim.
   - Full-page `GET` routes in `PageController` (`src/app/domain/web/controllers/_pages.py`) return `Template` (`litestar.response`), hydrating initial explore telemetry via `build_explore_telemetry_context` from `src/app/domain/products/services/_vector.py` and data-driven store lists via `StoreService.get_all_stores()` (`src/app/domain/products/services/_stores.py`); partial HTML fragment endpoints return `HTMXTemplate`.
   - Pass a string URL (or `False`) to `HTMXTemplate(push_url=...)`; never pass `push_url=True`.
2. **SSE `final` Frame Contract (`POST /api/chat/stream`)**:
   - `src/resources/chat-stream.js` and `src/resources/telemetry.js` consume `answer`, `intent_detected`, `search_metrics` (`embedding_ms`, `oracle_ms`, `ai_ms`, `total_ms`, `rrf_scores`, `lexical_hits`, `vector_query`), `sql_phases`, `from_cache`, `embedding_cache_hit`, `inventory_results`, `store_results`, and `map_actions` assembled by `AgentOrchestrationService` (`src/app/domain/ai/services/_agent.py`) and `AgentStreamService` (`src/app/domain/ai/runtime/_stream.py`) from `src/app/domain/chat/services/_telemetry.py` and streamed by `CoffeeChatController` (`src/app/domain/chat/controllers/_chat.py`) on the `final` SSE event. Backend changes must preserve this wire contract.
3. **Keyless Google Maps URLs & Coordinate Privacy (Web + APEX Page 3)**:
   - Store search and directions links built by `build_store_search_url` and `build_store_directions_url` in `src/app/domain/products/services/_maps.py` — as well as the `google_maps_url` column in APEX Page 3 (`src/apex/cymbal-coffee-ops/pages/p00003-stores.apx`) — must use standard `https://www.google.com/maps/search/?api=1&...` and `https://www.google.com/maps/dir/?api=1&...` URLs built from seeded `STORE` addresses without embedding an API key or persisting browser coordinates.
