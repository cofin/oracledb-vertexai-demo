# Flow: HTMX + Vite Frontend (htmx-vite-frontend_20260429)

*Chapter 4 of [cymbal-coffee-reset_20260429](../cymbal-coffee-reset_20260429/prd.md)*
*Beads epic: `oracledb-vertexai-4d6.4` (blocked by Ch 2; **soft-depends on Ch 3** — Phase 5.1c reads `dist/classify-compare.json` produced by Ch 3's CLI; if Ch 3 ships first, the explore page lights up immediately, otherwise the panel shows the 404 hint until Ch 3 lands; blocks Ch 5)*

---

## Specification

### Objective

Delete the React + TanStack frontend in `src/js/` and rebuild it as a tasteful **HTMX + Tailwind v4 + Alpine.js + ApexCharts** UI served via `litestar-vite` in `mode="template"` with `HTMXPlugin()`. Two pages, one shared layout:

- **`chat.html.j2`** — feature-parity with the React chat (persona switcher, message history, partial-swap message stream, session-id header pattern, metrics badges, cached badge).
- **`explore.html.j2`** — combines the deleted `performance` and `vector-demo` routes into one *Vector Explore* page with **5 panels**:
  1. Live search box → similarity-score distribution (ApexCharts bar).
  2. Top-K results with similarity bars.
  3. **Classification ground-truth-vs-live comparison** chart (data from Ch 3's `classify-compare` JSON).
  4. Cosine-similarity heatmap of recent queries.
  5. **Oracle EXPLAIN PLAN viewer** — runs `EXPLAIN PLAN FOR <vector search SQL>; SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY());` against the live query; shows the optimizer's choice of HNSW vector index range scan, target accuracy, partition pruning. Educational gold per PRD.

The visual polish bar is **at least the React version** — this is in the PRD's global constraints.

### Code Analysis Summary (verified 2026-04-29)

**Current React frontend (delete):**

- `src/js/src/main.tsx` — SPA entry point.
- `src/js/src/components/{CymbalLogo,GoogleLogo,OracleLogo,RetroGrid}.tsx` — logos + decorative grid.
- `src/js/src/routes/{__root,index,dashboard,chat,performance,vector-demo,routeTree}.tsx` — TanStack Router pages.
- `src/js/src/routes/{index,vector-demo}.test.tsx` — placeholder Bun test stubs (10 lines each).
- `src/js/package.json` orphans after delete: `react`, `react-dom`, `@tanstack/react-{router,query,table}`, `@radix-ui/react-{avatar,icons,scroll-area,slot}`, `lucide-react`, `@vitejs/plugin-react`, `@types/react*`.

**Keep (after rewrite):**

- `src/js/index.html` — rewrite `<body>` for HTMX boot.
- `src/js/src/index.css` — rewrite for Alpine + HTMX (Tailwind v4 stays via `@tailwindcss/vite`).
- `src/js/src/lib/{api,http}.ts` — keep; no React deps.
- `src/js/src/lib/generated/` — re-generate after Ch 2 + Ch 3 endpoints land.

**Add (npm deps):**

- `htmx.org` (~1.9.x).
- `alpinejs` (~3.x).
- `apexcharts` (~3.x).

**Vite config (`src/js/vite.config.ts`):**
- Currently `mode="spa"` with `@vitejs/plugin-react`. Flip to `mode="template"`, drop the React plugin.
- Inputs change from `["index.html", "src/main.tsx"]` to `["src/main.ts", "src/styles/main.css"]`.
- Keep `litestar-vite-plugin`, `@tailwindcss/vite`, `vite-tsconfig-paths`. Drop `@vitejs/plugin-react`.
- Pin `server.port`. Set `server.cors: true`.

**Python-side wiring:**
- `src/py/app/lib/settings.py:370-413` — `ViteSettings.create_config()` returns `ViteConfig(mode="spa", ...)`. Flip to `mode="template"`. Add template root path.
- `src/py/app/server/core.py:76` — `VitePlugin(config=config.vite)`. Add `HTMXPlugin()` next to it.
- **No `TemplateConfig` exists yet.** Must add `TemplateConfig(engine=JinjaTemplateEngine, directory=BASE_DIR / "server" / "templates")` to `app_config` in `ApplicationCore.on_app_init`. `litestar[jinja]` is already in `pyproject.toml:17`.
- **No Jinja templates exist yet.** Create `src/py/app/server/templates/` directory.

**Backend endpoints (existing, reuse):**
- `POST /api/chat` (`domain/chat/controllers.py:56-90`) — returns `{answer, intent_detected, search_metrics, from_cache, embedding_cache_hit, response_time_ms}`. Reuse for chat HTMX partial swaps.
- `POST /api/vector-demo` (`domain/products/controllers.py:47-95`) — returns `{results: [{id, name, description, price, similarity, distance}], search_time_ms, embedding_time_ms, oracle_time_ms, cache_hit, performance_level}`. Feeds explore panels 1+2.
- `GET /metrics` and `GET /api/metrics/summary` (`domain/system/controllers.py:41-80+`) — current performance-page data sources.

**Backend endpoints to add:**
- `GET /api/metrics/charts` — time-series + breakdown JSON for ApexCharts. Wraps existing metric aggregations (totalSearches, avg latencies, time series).
- `GET /api/explain-plan?query=<text>` — runs `EXPLAIN PLAN FOR ...; SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY());` against the live vector-search SQL with the user's query embedding bound. Returns `{plan_lines: list[str], plan_metadata: {...}}`.
- `GET /api/classify-compare` — reads `dist/classify-compare.json` (produced by Ch 3 CLI) and returns the rows + computed precision/recall per intent.
- `GET /api/explore/heatmap?window=24h` — pulls recent queries from `search_metric` + their similarity scores; returns a matrix.

**Other:**
- `OracleVectorSearchService.similarity_search` returns `(results, cache_hit, timings)` per `services.py:110-123`. Each result row has `id, name, description, price, similarity_score, distance` post-Ch 2 fix.
- `litestar-vite >= 0.18.2` already pinned (supports both modes).
- `litestar-htmx` is **not yet installed** — add to `pyproject.toml`.

### Requirements

1. **Delete every React/TanStack file** under `src/js/src/components/`, `src/js/src/routes/`, plus `main.tsx` and `routeTree.tsx`.
2. **`src/js/package.json`** — remove all React/TanStack/Radix/Lucide deps + `@vitejs/plugin-react`; add `htmx.org`, `alpinejs`, `apexcharts`.
3. **`src/js/vite.config.ts`** — flip to template mode; replace React plugin block; pin port; CORS true; rewrite `input` list.
4. **`src/js/src/main.ts`** (new) — boot HTMX + Alpine + register the `litestar` HTMX extension; import shared CSS.
5. **`src/js/src/styles/main.css`** (new) — Tailwind v4 entry + a small set of utility classes for chat bubbles + chart container.
6. **`src/py/app/server/templates/`** (new dir) — Jinja templates:
   - `_base.html.j2` — HTML shell with `vite_hmr()` + `vite('src/main.ts')` + `<body hx-ext="litestar">` + Alpine `x-data` skeleton + nav.
   - `chat.html.j2` — extends `_base`; persona buttons; chat history `<div id="messages">`; input form `hx-post="/api/chat" hx-target="#messages" hx-swap="beforeend"`; metrics badges via `hx-trigger="htmx:afterRequest"` + Alpine reactivity.
   - `explore.html.j2` — extends `_base`; 5 panels (see Phase 5 for details).
   - `_message.html.j2` — partial for a single chat message (used as HTMX response partial).
   - `_search_result.html.j2` — partial for a single vector-search result row.
7. **Python additions:**
   - `pyproject.toml`: `litestar-htmx>=0.2.0` (verify version).
   - `src/py/app/server/core.py`: register `HTMXPlugin()`; add `TemplateConfig`.
   - `src/py/app/lib/settings.py:ViteSettings`: `mode="template"`, set `paths.resource_dir` to `src/js/src`, `paths.bundle_dir` unchanged.
   - **New page controllers** in `src/py/app/server/page_controllers.py` (or add to `domain/system/controllers/`):
     - `GET /` → renders `chat.html.j2`.
     - `GET /explore` → renders `explore.html.j2`.
   - **New API endpoints** in their respective domain controllers:
     - `GET /api/metrics/charts` (system).
     - `GET /api/explain-plan?query=...` (products).
     - `GET /api/classify-compare` (system or chat).
     - `GET /api/explore/heatmap?window=24h` (system).
   - For HTMX-specific partial returns, controllers branch on `request.htmx`: full page or partial.
8. **Chat HTMX flow:**
   - User types in `<input>` inside `<form hx-post="/api/chat" hx-target="#messages" hx-swap="beforeend" hx-include="[data-include]">`.
   - Server receives, calls `ADKRunner.process_request`, returns `_message.html.j2` partial rendered with the response.
   - Alpine handles persona button state + session-id from `localStorage`; HTMX header `X-Session-Id` is set via `hx-headers`.
   - Message metadata (intent, latency, cached badge) lives in the partial markup.
9. **Explore page panels (5):**
   - **Panel 1 — Similarity score distribution:** `<div hx-get="/api/vector-demo" hx-trigger="search-submitted from:body" hx-swap="json">` consumed by Alpine into ApexCharts bar via `hx-ext="litestar"` `ls-for` template.
   - **Panel 2 — Top-K results:** server returns `_search_result.html.j2` partial repeated; similarity bar = inline div width%.
   - **Panel 3 — Classification ground-truth-vs-live:** ApexCharts grouped bar reading `/api/classify-compare`. Per-intent precision/recall + agreement chart.
   - **Panel 4 — Heatmap:** ApexCharts heatmap reading `/api/explore/heatmap?window=24h`.
   - **Panel 5 — EXPLAIN PLAN viewer:** input → `<button hx-get="/api/explain-plan?query={{ query }}" hx-target="#plan">` → `<pre id="plan">` formatted plan output.
10. **CSRF** — Litestar CSRF middleware applies; expose token via `<meta name="csrf-token">` and forward via `htmx:configRequest` (per `litestar-htmx` skill).
11. **Frontend test stubs deleted** — `src/js/src/routes/*.test.tsx`.
12. **No streaming chat** — PRD out-of-scope.

### Acceptance Criteria

- `find src/js/src -name "*.tsx"` returns **zero** files; `find src/js/src -name "*.ts"` returns the small set of TS modules (main.ts, lib/api.ts, lib/http.ts, lib/generated/*).
- `grep -E "react|tanstack|radix|lucide" src/js/package.json` returns **zero** matches.
- `find src/py/app/server/templates -name "*.html.j2"` returns at least 5 files (`_base`, `chat`, `explore`, `_message`, `_search_result`).
- `make install && make build` succeeds (Python + frontend build).
- `uv run app run` boots; `curl -s localhost:5006/` returns HTML containing `hx-ext="litestar"` and references to `/static/.../main.css` (manifest path resolved).
- Browser: `/` shows chat UI; persona buttons toggle; sending a message appends a partial; metrics badges populate.
- Browser: `/explore` shows 5 panels; live search updates similarity-distribution chart; top-K list refreshes; EXPLAIN PLAN panel returns text including `VECTOR INDEX RANGE SCAN` against `product_embedding_idx`.
- HMR works: edit `chat.html.j2` → page hot-swaps without full reload.
- (Manual checklist; not CI-gated) ApexCharts renders without console errors; Alpine `x-data` initialises without warnings — captured via Playwright `browser_console_messages` snapshot in the Beads notes.
- `make lint && make test` green; new tests `tests/api/test_pages.py` (renders chat + explore), `tests/api/test_explain_plan.py` (returns plan text), `tests/api/test_classify_compare_endpoint.py` (returns rows from JSON file).

### Risks / Known Gotchas

- **`hot_file` and `bundle_dir` paths must agree** between `ViteSettings.create_config()` and `vite.config.ts` `litestar({...})` block. Verify after the mode flip.
- **Tailwind v4 + `@tailwindcss/vite`** has a different content-resolution model than v3 — confirm Tailwind is scanning the new `*.html.j2` paths via `content` config or auto-detect.
- **`hx-ext="litestar"`** requires the JS extension to be loaded — bundle via `htmx.org` + the `litestar-vite-plugin` extension (or copy from `litestar-vite` examples).
- **EXPLAIN PLAN viewer** runs ad-hoc `EXPLAIN PLAN` against user input — the user-supplied phrase is **embedded** (not concatenated into SQL), so no SQL injection. But running EXPLAIN per-keystroke is wasteful — debounce on the client (HTMX `hx-trigger="keyup changed delay:500ms"`).
- **CSRF** for HTMX POST/GET-with-side-effects needs the meta-tag + `htmx:configRequest` JS handler. Don't ship without it.
- **Generated TypeScript types** under `src/js/src/lib/generated/` will be stale after Ch 2 + Ch 3 endpoint additions — regenerate via `litestar assets generate-types` (litestar-vite CLI). Commit the regen.
- **ApexCharts is not tree-shakable** — bundle size ~150KB gzipped. Acceptable for a reference demo; document.
- **`vector-demo` and `performance` collapse** removes existing routes — update any external references (README links, screenshots).
- **Heatmap data shape** — ApexCharts expects `[{name, data: [{x, y}]}, ...]`; `search_metric` aggregation must reshape accordingly.
- **HMR + sessions** — Alpine state + session-id `localStorage` survive HMR; HTMX swaps don't clobber Alpine state if the `x-data` root element is preserved.
- The page on `/` becomes a **server-rendered** page; the `dashboard.tsx` route disappears entirely. If users have bookmarked `/dashboard`, redirect at the controller layer.

---

## Implementation Plan

### Phase 0: Toolchain verification (`oracledb-vertexai-4d6.4.0`)

- [ ] **0.1** After Ch 1's `litestar-vite` (>=0.18.2) is on disk, install `htmx.org` + `alpinejs` + `apexcharts` into `src/js/` and **verify the canonical path of the `litestar` HTMX extension JS**: `bun add htmx.org && find node_modules -path '*htmx*litestar*' -o -path '*litestar-vite-plugin*' -name '*.js' | head -20`. Pin the actual import path (likely `litestar-vite-plugin/htmx/litestar.js` or similar) and update Phase 2.1's snippet before any template work begins. **If no `litestar` HTMX extension ships in either package**, fall back to plain HTMX (`hx-get/hx-post` + Litestar `HTMXTemplate` partial-HTML responses); do NOT use `hx-ext="litestar"` or `hx-swap="json"` in templates and update Phase 5.2 panels 3–4 to use server-rendered partials instead of client-side JSON templating.
- [ ] **0.2** Confirm `litestar-htmx` PyPI version pin: `uv add litestar-htmx --dry-run` to see the resolved version; pin in `pyproject.toml`.
- [ ] **0.3** Confirm CSRF token surface: `python -c "from litestar.middleware.csrf import CSRFConfig; print(CSRFConfig.__init__.__annotations__)"` — pin the exact Jinja accessor in `_base.html.j2` (`{{ request.scope.get('_csrf_token', '') }}` or `{{ csrf_input | safe }}` depending on what's available).

### Phase 1: Delete React + dependencies (`oracledb-vertexai-4d6.4.1`)

- [ ] **1.1** `git rm -r src/js/src/components/ src/js/src/routes/ src/js/src/main.tsx src/js/src/routeTree.tsx`.
- [ ] **1.2** Edit `src/js/package.json`: remove `react`, `react-dom`, `@tanstack/react-router`, `@tanstack/react-query`, `@tanstack/react-table`, `@radix-ui/react-{avatar,icons,scroll-area,slot}`, `lucide-react`, `@vitejs/plugin-react`, `@types/react`, `@types/react-dom`. Add `htmx.org@^1.9`, `alpinejs@^3`, `apexcharts@^3`. Run `bun install` (or `npm install`) to refresh `bun.lock`/`package-lock.json`.
- [ ] **1.3** Edit `src/js/vite.config.ts`:
  - Drop `import react from "@vitejs/plugin-react"`.
  - Replace `plugins: [react(), tailwindcss(), litestar({...})]` with `plugins: [tailwindcss(), litestar({input: ["src/main.ts", "src/styles/main.css"], bundleDir: ..., hotFile: ...})]`.
  - Pin `server.port: 5173`, `server.cors: true`.
  - Confirm `base` and `build.outDir` paths.
- [ ] **1.4** Audit `tsconfig.json` and remove React-specific JSX settings if present.
- [ ] **1.5** Confirm build still works: `cd src/js && bun run build` produces a manifest.

### Phase 2: New JS entry + bundled assets (`oracledb-vertexai-4d6.4.2`)

- [ ] **2.1** Create `src/js/src/main.ts`:
  ```ts
  import "htmx.org";
  import "htmx.org/dist/ext/litestar.js";   // verify path from litestar-vite-plugin docs
  import Alpine from "alpinejs";
  import ApexCharts from "apexcharts";

  // CSRF forwarding for HTMX
  document.body.addEventListener("htmx:configRequest", (e: any) => {
    const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");
    if (token) e.detail.headers["X-CSRF-Token"] = token;
  });

  (window as any).ApexCharts = ApexCharts;
  (window as any).Alpine = Alpine;
  Alpine.start();

  import "./styles/main.css";
  ```
- [ ] **2.2** Create `src/js/src/styles/main.css`:
  ```css
  @import "tailwindcss";
  @theme { /* design tokens */ }
  /* chat bubble + chart container utilities */
  ```
- [ ] **2.3** Delete `src/js/src/index.css` (replaced).
- [ ] **2.4** Confirm `bun run build` produces a single `manifest.json` referencing the new inputs.

### Phase 3: Python wiring — TemplateConfig + HTMXPlugin (`oracledb-vertexai-4d6.4.3`)

- [ ] **3.1** Add `litestar-htmx>=0.2.0` to `pyproject.toml`. Run `uv lock && uv sync`.
- [ ] **3.2** `src/py/app/lib/settings.py:ViteSettings.create_config`: change `mode="spa"` → `mode="template"`. Set `paths.resource_dir = BASE_DIR.parents[2] / "src" / "js" / "src"`. Confirm `bundle_dir` and `hot_file` match `vite.config.ts`.
- [ ] **3.3** `src/py/app/server/core.py:ApplicationCore.on_app_init`:
  ```python
  from litestar_htmx import HTMXPlugin
  from litestar.config.templating import TemplateConfig
  from litestar.contrib.jinja import JinjaTemplateEngine

  app_config.template_config = TemplateConfig(
      engine=JinjaTemplateEngine,
      directory=BASE_DIR / "server" / "templates",
  )
  app_config.plugins.extend([VitePlugin(config=config.vite), HTMXPlugin()])
  ```
- [ ] **3.4** Verify `litestar-vite` registers `vite_hmr()` and `vite()` Jinja globals automatically when both `TemplateConfig` and `VitePlugin` are present.

### Phase 4: Templates — base + chat (`oracledb-vertexai-4d6.4.4`)

- [ ] **4.1** Create `src/py/app/server/templates/_base.html.j2`:
  ```html
  <!DOCTYPE html>
  <html lang="en" class="dark">
  <head>
    <meta charset="utf-8">
    <meta name="csrf-token" content="{{ request.scope['csrf_token'] }}">
    <title>{% block title %}Cymbal Coffee{% endblock %}</title>
    {{ vite_hmr() }}
    {{ vite('src/main.ts') }}
  </head>
  <body hx-ext="litestar" class="min-h-screen bg-zinc-950 text-zinc-100">
    <nav>{% include "_nav.html.j2" %}</nav>
    {% block content %}{% endblock %}
  </body>
  </html>
  ```
- [ ] **4.2** Create `src/py/app/server/templates/_nav.html.j2` — links to `/` (Chat) and `/explore` (Vector Explore).
- [ ] **4.3** Create `src/py/app/server/templates/chat.html.j2`:
  - Persona switcher: 4 `<button x-on:click="persona = 'novice'" :class="...">` + Alpine `x-data="{ persona: 'enthusiast', sessionId: localStorage.getItem('sid') }"`.
  - Message stream `<div id="messages">`.
  - Form `<form hx-post="/api/chat" hx-target="#messages" hx-swap="beforeend" hx-include="[name=persona]" hx-headers='js:{ "X-Session-Id": sessionId }'>` (verify `hx-headers js:` syntax).
- [ ] **4.4** Create `src/py/app/server/templates/_message.html.j2` — single message bubble + metrics badges + cached badge.
- [ ] **4.5** Add page handler `GET /` rendering `chat.html.j2`. Locate in `src/py/app/server/page_controllers.py` (new file).
- [ ] **4.6** Update `POST /api/chat` controller: when `request.htmx` is true, return `Template("_message.html.j2", context={"message": result})`; otherwise return JSON (preserves API consumers).

### Phase 5: Templates — explore page (5 panels) (`oracledb-vertexai-4d6.4.5`)

- [ ] **5.1a** Add `GET /api/metrics/charts` to `src/py/app/domain/system/controllers/_metrics.py` (or whichever controller package Ch 2 normalized to). Returns `{labels: [str], total_latency: [float], oracle_latency: [float], vertex_latency: [float], breakdown: {...}}`. Reads from existing `search_metric` aggregations.
- [ ] **5.1b** Add `GET /api/explain-plan?query=<text>` to `src/py/app/domain/products/controllers/_vector.py`. Embeds the query via `VertexAIService`, then runs the `EXPLAIN PLAN FOR <named vector search SQL>` + `SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY())` sequence. Returns `{plan_lines: [str], plan_summary: {index_used, target_accuracy, ...}}`. Named SQL key: `explain-vector-search` in `db/sql/products.sql`.
- [ ] **5.1c** Add `GET /api/classify-compare` to `src/py/app/domain/system/controllers/_explore.py` (new file). Reads `Path.cwd() / "dist" / "classify-compare.json"` (the exact path Ch 3 writes to). Computes per-intent precision/recall, returns `{rows: [...], summary: {...}}`. **404 with body `{"hint": "run uv run app coffee classify-compare to generate this dataset"}`** if the file is missing.
- [ ] **5.1d** Add `GET /api/explore/heatmap?window=24h` to the same `_explore.py`. Reads `search_metric` rows in the time window, returns `{series: [{name, data: [{x, y}]}, ...]}` shaped for ApexCharts heatmap.
- [ ] **5.2** Create `src/py/app/server/templates/explore.html.j2` with 5 panels:
  - **Panel 1 — Similarity Distribution chart** — search input `<input hx-trigger="keyup changed delay:500ms" hx-post="/api/vector-demo" hx-target="#results" ...>`; chart updates on `htmx:afterRequest` via Alpine.
  - **Panel 2 — Top-K Results** — `<div id="results">` rendered from `_search_result.html.j2` partials.
  - **Panel 3 — Classify-compare chart** — `<div hx-get="/api/classify-compare" hx-trigger="load" hx-swap="json">` consumed by Alpine into ApexCharts via `ls-for` template.
  - **Panel 4 — Heatmap** — `<div hx-get="/api/explore/heatmap" hx-trigger="load" hx-swap="json">` consumed by Alpine into ApexCharts heatmap.
  - **Panel 5 — EXPLAIN PLAN viewer** — debounced input `<input hx-trigger="keyup changed delay:500ms" hx-get="/api/explain-plan" hx-target="#plan" hx-swap="innerHTML">`; `<pre id="plan">` displays plan text formatted with line numbers.
- [ ] **5.3** Create `src/py/app/server/templates/_search_result.html.j2` — single result row with name, description, similarity bar (CSS width%), price.
- [ ] **5.4** Add page handler `GET /explore` rendering `explore.html.j2`.
- [ ] **5.5** Update `POST /api/vector-demo` controller: when `request.htmx`, return repeated `_search_result.html.j2` partials (one per result). When not, return JSON (preserves API).

### Phase 6: Type regen + cleanup (`oracledb-vertexai-4d6.4.6`)

- [ ] **6.1** `litestar assets generate-types` — regenerate `src/js/src/lib/generated/{routes,schemas,openapi}.{ts,json}` to include new endpoints.
- [ ] **6.2** Delete `src/js/src/routes/*.test.tsx`.
- [ ] **6.3** Delete `src/js/src/lib/api.ts` if it became unused after the rewrite (HTMX talks directly to URLs); keep `lib/http.ts` only if needed for non-HTMX fetches (likely the typed regen replaces it).
- [ ] **6.4** Update `README.md` screenshot section: capture new chat + explore screenshots; commit under `docs/screenshots/`.

### Phase 7: Tests + verification (`oracledb-vertexai-4d6.4.7`)

- [ ] **7.1** `tests/api/test_pages.py` — `await client.get("/")` returns HTML with `hx-ext="litestar"` and a chat input; `await client.get("/explore")` returns HTML with 5 panel containers (assert IDs).
- [ ] **7.2** `tests/api/test_chat_partial.py` — `await client.post("/api/chat", json={...}, headers={"HX-Request": "true"})` returns HTML containing `<div class="message">` (asserts the partial branch was taken).
- [ ] **7.3** `tests/api/test_explain_plan.py` — `await client.get("/api/explain-plan?query=dark+roast")` returns 200 with `plan_lines` containing `VECTOR INDEX RANGE SCAN`.
- [ ] **7.4** `tests/api/test_classify_compare_endpoint.py` — write a stub `dist/classify-compare.json` fixture; assert endpoint returns rows + computed summary.
- [ ] **7.5** Manual smoke (document in Beads notes): `make install && make build && uv run app run`; open `/` and `/explore`; verify all 5 panels populate; verify HMR by editing `chat.html.j2`.
- [ ] **7.6** Update `.agents/patterns.md`: HTMX page-vs-partial branching idiom (`if request.htmx`); `hx-ext="litestar"` for client-side JSON rendering; ApexCharts + Alpine pattern; EXPLAIN PLAN viewer pattern.

---

## Out of Scope (defer to other chapters)

- Knowledge base / guide consolidation — Ch 5.
- README quickstart rewrite — Ch 5.
- CLI command pruning (`bulk-embed`, `export-fixtures` deletion) — Ch 5.
- Streaming chat (PRD says "not yet canonical").
- Authentication / multi-user (PRD out-of-scope).
- Inertia.js path (HTMX is the chosen story).
