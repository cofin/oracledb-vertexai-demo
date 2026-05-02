# Knowledge Entry: ui-regression-recovery_20260501

- **Flow ID:** `ui-regression-recovery_20260501`
- **Description:** Corrective PRD — restore Cymbal Coffee frontend quality after the React→HTMX migration: shared shell, structured `sql_phases` telemetry, popovers, ApexCharts dashboard, descope classify-compare.
- **Completed:** 2026-05-01
- **Beads Epic:** `oracledb-vertexai-4d6.8`
- **Topics:** htmx, ui, telemetry, apexcharts, sql-phases, classify-compare-removal, regression

<!-- truth: start -->
## Summary

Five-phase recovery on top of Ch 4's HTMX/Vite rebuild. Phase 1 restored the
shared app shell + reusable Tailwind primitives (panels, metric cards,
telemetry chips, icon buttons, chart hosts, popovers). Phase 2 added
structured `sql_phases` telemetry to chat stream/final payloads (named SQL
keys + sanitized binds + row counts + runtimes + cache status). Phase 3 fixed
`/explore?q=...` query prefill and HTMX form-post handling on
`/api/vector-demo`. Phase 4 expanded `/api/metrics/charts` from a single
latency series into a typed dashboard payload with response time-series,
vector similarity scatter, and component timing breakdown — all rendered as
bounded ApexCharts. Phase 5 removed the descoped classify-compare surface
entirely (panel + endpoint + schemas + tests) and tightened the
`hx-ext="litestar"` scoping.

## Patterns Elevated (see patterns.md for full list)

- HTMX endpoints that also accept JSON parse the request body directly
  (`await request.json()` / `await request.form()`); do NOT declare them
  as a typed `data:` body parameter — Litestar's body-DTO path rejects
  HTMX form posts when the route declares JSON body data.
- `hx-ext="litestar"` belongs only on JSON-templating panels; scope it out
  with `ignore:litestar` on partial-HTML-swap surfaces.
- Cached chat responses store only the product-lookup `sql_phases`. At read
  time the cache hit is wrapped in a fresh `get-cached-response` phase so
  the UI shows both the cache hit and the original product-lookup context.
- Streaming `/api/chat/stream` exception handling lives inside the async
  generator: catch broadly, log with `logger.aexception()`, yield a sanitized
  SSE `error` event. Litestar exception middleware cannot intercept failures
  after SSE headers ship.
- The current user-facing product label is `Oracle 26ai`. Older
  reference screenshots and some planning language mention `Oracle 23ai` —
  do not propagate the old label into new content.
- Keep the chart API shape aligned with the client by returning the full
  dashboard payload from one endpoint. The old single-series endpoint
  could not support response trends, scatter, and breakdown views without
  client-side guessing.
- When a chapter descopes a surface, audit the parent PRD too — otherwise
  a later verification task can accidentally restore the descoped surface.

## Key Files

- `src/app/domain/web/templates/{base,_nav}.html.j2` — shared shell.
- `src/app/domain/web/templates/pages/{chat,explore}.html.j2` — restored panels.
- `src/resources/{main.js,styles.css}` — shared primitives and ApexCharts wiring.
- `src/app/domain/chat/{services/adk.py,controllers/_chat.py,schemas/_chat.py}` — `sql_phases` telemetry.
- `src/app/domain/system/{schemas/_metrics.py,services/services.py,controllers/_metrics.py}` and `src/app/db/sql/system.sql` — typed dashboard payload.
- `src/app/domain/products/controllers/_vector.py` — HTMX/JSON dual contract for `/api/vector-demo`.
<!-- truth: end -->
