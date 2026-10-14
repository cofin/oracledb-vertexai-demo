# Web, HTMX & Frontend Review Checklist

## HTMX, SSE & Maps Rules

1. **`litestar_htmx` Imports & Response Types**:
   - Always import HTMX types from `litestar_htmx` (`HTMXPlugin`, `HTMXRequest`, `HTMXTemplate`), never from the deprecated `litestar.plugins.htmx` shim.
   - Full-page `GET` routes return `Template` (`litestar.response`); partial HTML fragment endpoints return `HTMXTemplate`.
   - Pass a string URL (or `False`) to `HTMXTemplate(push_url=...)`; never pass `push_url=True`.
2. **SSE `final` Frame Contract (`POST /api/chat/stream`)**:
   - `src/resources/chat-stream.js` and `src/resources/telemetry.js` consume `answer`, `intent_detected`, `search_metrics` (`embedding_ms`, `oracle_ms`, `ai_ms`, `total_ms`), `sql_phases`, `from_cache`, `store_results`, and `map_actions` on the `final` SSE event. Backend changes must preserve this wire contract.
3. **Keyless Google Maps URLs**:
   - Store search and directions links built by `src/app/domain/products/services/_maps.py` must use standard `https://www.google.com/maps/search/?api=1&...` and `https://www.google.com/maps/dir/?api=1&...` URLs without embedding an API key.
