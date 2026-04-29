# Learnings: htmx-vite-frontend_20260429

> Notes captured during implementation. Synced from Beads task notes via `/flow:sync`.

_No implementation notes yet — chapter not started._

## Pre-implementation findings (planning phase, 2026-04-29)

- Backend `/api/chat` and `/api/vector-demo` endpoints already return chart-ready JSON — no breaking changes needed; only add `if request.htmx: return Template(...)` branch for partial responses.
- **No `TemplateConfig` exists yet** in the app — must add to `ApplicationCore.on_app_init` alongside the existing `VitePlugin` registration. `litestar[jinja]` is already a dep.
- `src/py/app/server/templates/` directory does not exist; must be created.
- `litestar-htmx` is **not** a current dep — add to pyproject.
- `OracleVectorSearchService.similarity_search` returns the right shape per result (`id, name, description, price, similarity_score, distance` after Ch 2's `current_price` fix). No backend refactor needed for chart data.
- **EXPLAIN PLAN viewer is genuinely educational** — ApexCharts is overkill here; a `<pre>` formatted plan output is the right UI. Debounce inputs (`keyup delay:500ms`) to avoid hammering Oracle on every keystroke.
- **Heatmap data shape** — ApexCharts wants `[{name, data: [{x, y}]}, ...]`; `search_metric` aggregation must reshape accordingly.
- **`@tailwindcss/vite` v4 content scanning** must include the new `*.html.j2` paths — confirm during Phase 2.
