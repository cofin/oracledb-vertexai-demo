# Flow: HTMX + Vite Frontend (htmx-vite-frontend_20260429)

*Chapter 4 of [cymbal-coffee-reset_20260429](../cymbal-coffee-reset_20260429/prd.md)*
*Beads epic: `oracledb-vertexai-4d6.4` (blocked by Ch 2; soft-depends on Ch 3 — Phase 5.1c reads `dist/classify-compare.json` produced by Ch 3's CLI; if Ch 3 ships first, the explore page lights up immediately, otherwise the panel returns `{"hint": "..."}` until Ch 3 lands; blocks Ch 5)*

---

## Specification

### Objective

Bundle two transformations into one chapter, in this order:

1. **Source-tree flatten + CLI restructure** — collapse `src/py/app/` → `src/app/`, `src/py/tests/` → `src/tests/`. Move frontend build INPUTS to `src/resources/` (parallel to `src/app/`). Land Jinja templates inside a new `src/app/domain/web/` package (web is a peer-domain alongside `chat`/`products`/`system`); Vite's bundle OUTPUT lands at `src/app/domain/web/static/dist/` (gitignored). After Ch 4, `src/js/` and `src/py/` no longer exist; `vite.config.ts` and `package.json` live at repo root. **And** rebuild `coffee` as a hand-rolled `rich_click` group (mirrors `dma/accelerator`'s `dma`) so it stops routing through `litestar_group()`; migrations and assets land on `manage.py` exclusively.
2. **Frontend rewrite** — replace the React + TanStack SPA (`mode="spa"`) with a tasteful **HTMX 2.x + Tailwind v4 + Alpine.js + ApexCharts** UI served via `litestar-vite` in `mode="template"` with `HTMXPlugin()` + `hx-ext="litestar"`. No bun, no biome, no TanStack. Two pages, one shared layout, five panels on the explore page (heatmap dropped). The runtime executor is `node` (npm), not `bun`.

End state: a clean monorepo where the JS/Python boundary is a directory, not a tree-deep prefix. Single dev command (`VITE_DEV_MODE=true uv run coffee run` — litestar-vite auto-launches Vite as a subprocess). Single build command (`uv run python manage.py assets build`). **`coffee` becomes a hand-rolled `rich_click` group** (no more `litestar_group()`) so it doesn't auto-mount asset/migration/database subcommands at help time. **All asset-pipeline and migration commands route through `manage.py` exclusively**, mirroring `dma/accelerator`'s `dma`-vs-`manage.py` split. Visual polish bar **at least the React version** per PRD global constraint #10.

### Code Analysis Summary (verified 2026-04-29)

**Current `src/js/` React frontend (delete in Phase 2):**

- `src/js/src/main.tsx`, `src/js/src/routeTree.tsx` — TanStack Router boot.
- `src/js/src/components/{CymbalLogo,GoogleLogo,OracleLogo,RetroGrid}.tsx` — logos + decorative grid.
- `src/js/src/routes/{__root,index,dashboard,chat,performance,vector-demo,routeTree}.tsx` (7 React route files).
- `src/js/src/routes/{index,vector-demo}.test.tsx` — placeholder Bun test stubs.
- `src/js/index.html`, `src/js/src/index.css` — SPA shell + Tailwind v4 import + design tokens (the dark-theme variables `--bg-canvas`, `--accent: #a16207`, etc. carry forward into the new `styles.css`).
- `src/js/src/lib/{api,http}.ts` + `src/js/src/lib/generated/` — typed API client (deleted; new code calls URLs directly).
- `src/js/{biome.json,tsconfig.json,tsconfig.node.json,bun.lock,package-lock.json,vite.config.ts,package.json}` — toolchain.
- `src/js/public/` — 23 static assets (favicons, SVG logos, manifest, browserconfig, screenshots). **Carry forward to `src/resources/public/` in Phase 3.4 verbatim.**
- `src/js/node_modules/` — gitignored.

**Python source `src/py/app/` (move in Phase 1):**

- `BASE_DIR = module_to_os_path("app")` resolves to `<repo>/src/py/app` today; after Phase 1 it resolves to `<repo>/src/app`.
- `BASE_DIR.parents[2]` is used in two places:
  - `app/lib/settings.py:408` — `root=BASE_DIR.parents[2] / "src" / "js"` (Vite root).
  - `app/domain/system/controllers/_system.py:28` — `path=BASE_DIR.parents[2] / "src" / "js" / "public" / "favicon.ico"`.
  - **After flatten, `parents[2]` shifts.** With `BASE_DIR = <repo>/src/app`: `parents[0]=src`, `parents[1]=<repo-root>`, `parents[2]=<parent-of-repo>` — broken. The new repo-root accessor is `BASE_DIR.parents[1]`. Both call sites must be edited in Phase 1.6.
- Other `BASE_DIR` users (`app/config.py:39`, `app/lib/settings.py:91,94,156,187,384`) all stay relative to `BASE_DIR` and are flatten-safe.

**Litestar-vite contract (verified against `litestar-vite==0.18.2+`):**

- `RuntimeConfig(executor="node")` is supported. `litestar_vite.executor.NodeExecutor.bin_name = "npm"` (verified `src/py/litestar_vite/executor.py:230`).
- `dev_mode=True` makes `VitePlugin` auto-launch `npm run dev` as a subprocess via `_popen_server_kwargs` — single dev command, no `make frontend-dev`.
- `mode="template"` registers Jinja globals `vite_hmr()`, `vite('path')`, `vite_static('path')`, `vite_routes()` automatically when both `TemplateConfig` and `VitePlugin` are present.
- `TypeGenConfig(generate_sdk=False, generate_routes=False, generate_schemas=False, generate_page_props=False)` is a valid construction — all kwargs default-typed (verified `src/py/litestar_vite/config/_types.py:13-52`). With every `generate_*` flag off, `litestar assets generate-types` is a no-op; it stays out of `make install` / `make build`.
- Helper `registerHtmxExtension()` from `litestar-vite-plugin/helpers` (npm package) wires CSRF + JSON templating client-side via `hx-ext="litestar"`. **Default header is `X-CSRFToken`** (verified `dist/js/helpers/csrf.js:12`). The current Litestar config uses `X-XSRF-TOKEN` (`src/py/app/lib/settings.py:261`). Phase 4.5 aligns the Litestar header to `X-CSRFToken` so the helper works with no client-side patch.

**Litestar-htmx contract (built into Litestar core; importable as `from litestar.plugins.htmx import ...`, verified 2026-04-29):**

- HTMX support ships inside Litestar 2.x via the built-in `litestar.plugins.htmx` module. **No separate `litestar-htmx` PyPI dependency is added** — `litestar[jinja,jwt,cryptography,structlog]` already exposes the surface.
- `HTMXPlugin()` registers `HTMXRequest` as the request class, exception handlers, and `HTMXTemplate`.
- Server-driven response objects in scope this chapter:
  - `HTMXTemplate(template_name=..., context={...}, re_target=..., re_swap=..., push_url=...)` — the canonical partial response, sets `HX-Retarget`/`HX-Reswap`/`HX-Push-Url` headers automatically when those kwargs are passed.
  - `TriggerEvent(name=..., params={...}, after="receive"|"settle"|"swap")` — sets `HX-Trigger*`. Used in chat send to trigger a `metrics-updated` client event so OOB-swapped badges refresh.
  - `Reswap`, `Retarget`, `PushUrl` — standalone response objects when not using `HTMXTemplate`'s shorthand kwargs (e.g., the explore search `PushUrl`).
- `request.htmx` is truthy when `HX-Request: true` header is present; access `request.htmx.target`, `request.htmx.trigger`, etc.
- Tests: `await client.post(..., headers={"HX-Request": "true"})` exercises the partial path; without the header the JSON path runs.

**Backend endpoints (existing, reuse — verified Ch 2 didn't move them):**

- `POST /api/chat` (`domain/chat/controllers/_chat.py:56-98`) — returns `CoffeeChatReply` with `answer`, `intent_detected`, `search_metrics`, `from_cache`, `embedding_cache_hit`. Phase 4.7 adds the `request.htmx` branch.
- `POST /api/vector-demo` (`domain/products/controllers/_vector.py:47-108`) — returns `{results, search_time_ms, embedding_time_ms, oracle_time_ms, cache_hit, performance_level, debug_timings}`. Phase 5.6 adds the `request.htmx` branch.
- `GET /metrics`, `GET /api/metrics/summary` (`domain/system/controllers/_metrics.py`) — already wired; Phase 5.1a adds `/api/metrics/charts` next to them.

**Backend endpoints to add (this chapter):**

- `GET /api/metrics/charts` — time-series JSON for ApexCharts. Phase 5.1a.
- `GET /api/explain-plan?query=<text>` — embeds the query, runs `EXPLAIN PLAN FOR <named SQL> ...` then `SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY())`. Phase 5.1b. **Two driver calls.**
- `GET /api/classify-compare` — reads `dist/classify-compare.json` (Ch 3 contract). Phase 5.1c.
- (Heatmap dropped — not in scope.)

**Page controllers (new):**

- `GET /` → `pages/chat.html.j2`. Phase 4.6.
- `GET /explore` → `pages/explore.html.j2`. Phase 5.4.
- Both live in `src/app/domain/system/controllers/_pages.py` (DomainPlugin auto-discovers; no manual registration in `ApplicationCore`). Single class `PageController` with two route handlers. Per the per-class-per-file convention from Ch 2.5, `_pages.py` holds one controller class.

**Tooling endpoints (`src/app/server/page_controllers.py`):**

- Not used. `/`, `/explore`, `/favicon.ico` all live under `domain/system/controllers/`.

**Other facts:**

- `OracleVectorSearchService.similarity_search` returns `(results, cache_hit, timings)` per Ch 2 (`services.py:110-123`). Each row has `id, name, description, price, similarity_score, distance`.
- `litestar[jinja]` is in `pyproject.toml:17`, so JinjaTemplateEngine is import-ready.
- No `TemplateConfig` exists yet; Phase 4.4 adds it.
- **Current `coffee` CLI shape (changes in Phase 1.8):** `coffee = "app.__main__:run_cli"` calls `litestar_group()` (`src/py/app/__main__.py:53-55`). That single call boots the full `Litestar(...)` app and triggers every plugin's `on_cli_init`:
  - `app/server/core.py:125-168` — `ApplicationCore.on_cli_init` lifts sqlspec `upgrade`/`downgrade` and mounts custom commands `load-fixtures`, `export-fixtures`, `bulk-embed`, `clear-cache`, `model-info`.
  - `litestar_vite.VitePlugin.on_cli_init` — auto-mounts `coffee assets {install, build, serve, init, status, generate-types}`.
  - `litestar_granian.GranianPlugin.on_cli_init` — auto-mounts `coffee run`.
  - `sqlspec.extensions.litestar.cli` — auto-mounts `coffee database *` (full migration tree).
  - **Side-effect we don't want:** `coffee --help` constructs `app.config.db` (the SQLSpec configuration) just to enumerate subcommands. The DB plumbing is mounted into the CLI even for commands that never touch it.
- **Target shape (Phase 1.8):** Mirror `dma/accelerator/src/py/dma/cli/main.py:28-44` and `manage.py:386-413`. `coffee` becomes a hand-rolled `rich_click` group; subcommands explicitly import only the Litestar/SQLSpec/Vite functions they need, and only when they need them.
  - `coffee` retains: `run` (wraps `litestar_granian.cli:run_command` lazily, accelerator-style), `bulk-embed`, `clear-cache`, `model-info`, `load-fixtures`, `export-fixtures`. Production-app commands.
  - `coffee` loses: `assets *`, `upgrade`/`downgrade`, `database *`. These move to `manage.py` exclusively.
  - `manage.py` keeps: `init`, `install`, `doctor`, `infra`, `database` (with `upgrade`/`downgrade` via `add_migration_commands`), `assets` (with `install`/`build`/`serve`/`generate-types` via the `vite_group` filter — already wired at `manage.py:152-154`).
  - **No more dual surface.** `coffee assets *` won't exist as a registered subcommand because `coffee` no longer routes through `litestar_group`. The "policy + invariant test" approach is replaced by the architecture itself.

**Visual seed (carry-over from React):**

Design tokens in `src/js/src/index.css` (dark theme: `--bg-canvas: #111113`, `--accent: #a16207`, `--accent-strong: #ca8a04`, etc.) are well-tuned. Phase 3.3 ports them verbatim into `src/resources/styles.css` with `@theme` so Tailwind v4 picks them up.

### Coupled-contract: `ViteConfig` (Python) ↔ `vite.config.ts` (TS)

These five values must agree on both sides. **Mismatch breaks HMR or manifest resolution silently.** Implementer copies the right column verbatim.

| Concept                | Python (`ViteSettings.get_config()`)                          | TS (`vite.config.ts`)                                             |
|------------------------|---------------------------------------------------------------|-------------------------------------------------------------------|
| Repo root              | `paths=PathConfig(root=BASE_DIR.parents[1], resource_dir=Path("src/resources"))` | `process.cwd()` (vite default; runs from repo root) |
| Bundle output          | `paths.bundle_dir = BASE_DIR / "domain" / "web" / "static" / "dist"` | `litestar({ bundleDir: "src/app/domain/web/static/dist", ... })` (plugin sets `build.outDir`) |
| Hot file               | (auto from `bundle_dir`) → `src/app/domain/web/static/dist/hot` | `litestar({ hotFile: "src/app/domain/web/static/dist/hot", ... })` |
| Asset URL              | `paths.asset_url = "/static/dist/"`                           | `litestar({ assetUrl: "/static/dist/" })` (plugin sets `base`)    |
| Inputs                 | (set by TS, plugin reflects)                                  | `litestar({ input: ["src/resources/main.js", "src/resources/styles.css"] })` |
| Dev port               | `runtime=RuntimeConfig(port=5173, host="0.0.0.0")`            | `server: { port: 5173, host: "0.0.0.0", strictPort: true, cors: true }` |
| Executor               | `runtime=RuntimeConfig(executor="node")`                      | (n/a; npm scripts driven by package.json)                         |

`paths.root` is `BASE_DIR.parents[1]` (= repo root after the flatten). Vite is invoked from repo root.

**Domain layout (mirrors dma/accelerator's `domain/web` pattern):**
- **`src/resources/`** — Vite build INPUT. Holds `main.js`, `styles.css`, `public/` (23 brand assets).
- **`src/app/domain/web/templates/`** — Jinja templates served by Litestar (HTMX partials + base layouts).
- **`src/app/domain/web/static/dist/`** — Vite build OUTPUT. Gitignored. `manage.py assets build` writes `manifest.json` + hashed bundles here; `dist/hot` is the dev-mode HMR marker.

The web domain is a peer to `chat`/`products`/`system`. `src/app/domain/web/__init__.py` documents the contract; the static subtree exists in dev only via the gitignored `dist/` (no `.gitkeep` is needed because the dir is purely build output).

### Server-driven HTMX response objects (decisions for this chapter)

Instead of ad-hoc client JS, use `litestar-htmx` response classes server-side wherever the behavior is server-driven:

| Use site                                                     | Object                                  | Why                                                                                  |
|--------------------------------------------------------------|-----------------------------------------|--------------------------------------------------------------------------------------|
| `POST /api/chat` HTMX branch — happy path                    | `HTMXTemplate(template_name="partials/_chat_response.html.j2", ...)` (wrapper that composes the message bubble + OOB metrics + OOB flash) | One round-trip renders the message bubble AND updates the metrics-badges row via `hx-swap-oob="true"` AND drains pending flash messages from the session into the OOB flash region |
| `POST /api/chat` HTMX branch — validation error              | `HTMXTemplate(..., re_target="#chat-error", re_swap="innerHTML")` (encodes `Retarget` + `Reswap`) | Server overrides the form's `hx-target=#messages` so the error renders into the dedicated error region |
| `POST /api/chat` HTMX branch — done event                    | `TriggerEvent(name="chat:reply-rendered", after="swap")` (chained with `HTMXTemplate` via the `trigger_event=` kwarg) | Emits a client event after swap so Alpine can reset the input + scroll-to-bottom without a JS click handler |
| Explore search box (Panel 1)                                 | `HTMXTemplate(template_name="partials/search_result_list.html.j2", push_url=f"/explore?q={quote(query)}", ...)` (composes `PushUrl`) | URL is shareable; back/forward navigate to past queries |
| Cache-clear button / persona-save / any side-effect button   | `flash(request, "...", "<category>")` then `HTMXTemplate(template_name="partials/_flash.html.j2", reswap="none")` | Side-effect handlers don't need to update the page they were invoked from — `Reswap("none")` suppresses the default swap; the OOB flash region renders independently |
| EXPLAIN-PLAN viewer (Panel 2) — query missing                | `raise NotFoundException(detail={"hint": "Type a query in the search box first."})` | Idiomatic 404 with structured detail |
| classify-compare endpoint (Panel 5) — file missing           | `raise NotFoundException(detail={"hint": "run uv run coffee classify-compare to generate this dataset"})` | Same idiom; surfaces actionable next-step text in the panel |

**Out of scope** (do NOT use): `HXLocation`, `ClientRedirect`, `ClientRefresh`, `HXStopPolling`. Not needed for this chapter's flows. If a future task introduces auth or session expiry, `ClientRedirect(redirect_to="/login")` is the right tool — defer.

### Per-panel decision: `hx-ext="litestar"` vs Alpine + fetch

| Panel | Source                                | Render strategy                              | Rationale                                  |
|------:|---------------------------------------|----------------------------------------------|--------------------------------------------|
| 1     | `POST /api/vector-demo` (HTMX branch) | Server partial — list of `partials/search_result.html.j2` | Already a server-rendered list; trivial swap |
| 2     | `GET /api/explain-plan?query=...`     | Server partial — `partials/plan_lines.html.j2` rendering `<pre>` | Plan output is preformatted text; client templating buys nothing |
| 3     | `GET /api/metrics/summary` (existing) | **Client `ls-*` template** against JSON       | No interactivity; static "JSON → cards" map is exactly what `ls-for` is for. Eliminates an Alpine snippet. |
| 4     | `GET /api/metrics/charts`             | Alpine (`x-data` + `init() { fetch().then(j => new ApexCharts(el, opts).render()) }`) | ApexCharts must be instantiated by JS |
| 5     | `GET /api/classify-compare`           | Alpine + ApexCharts                           | Same reason as Panel 4                     |

Panel 3 example (canonical `ls-*`):

```html
<div hx-get="/api/metrics/summary" hx-trigger="load, every 10s" hx-swap="json">
  <template ls-for="card in $data.cards" ls-key="card.id">
    <article class="rounded-xl border border-border bg-surface p-4">
      <p class="text-xs uppercase tracking-wider text-muted">${card.label}</p>
      <p class="mt-1 text-2xl font-semibold">${card.value}</p>
      <p class="mt-1 text-sm text-muted">${card.delta}</p>
    </article>
  </template>
</div>
```

`/api/metrics/summary` must return `{cards: [{id, label, value, delta}, ...]}`. Phase 5.1d ensures the existing endpoint matches this shape (or shapes a thin wrapper if it doesn't).

### Templates inventory (every `.html.j2` this chapter creates)

All templates live under `src/app/domain/web/templates/` (the web-domain Jinja root passed to Litestar's `TemplateConfig`).

`src/app/domain/web/templates/`:
- `base.html.j2` — `<head>` with `{{ vite_hmr() }}` + `{{ vite('src/resources/main.js') }}` + `<meta name="csrf-token" content="{{ csrf_token() }}">`; `<body hx-ext="litestar" class="min-h-screen bg-canvas text-base">`; `{% include "_nav.html.j2" %}`; **`{% include "partials/_flash.html.j2" %}`** (renders any pending flash messages on full-page loads); `{% block content %}{% endblock %}`.
- `_nav.html.j2` — top nav: `<nav>` with two anchor links to `/` and `/explore` (no `hx-boost` — full reload is fine for two-page apps).
- `pages/chat.html.j2` — extends base; persona switcher (Alpine `x-data="{ persona: 'enthusiast', sessionId: localStorage.getItem('sid') ?? crypto.randomUUID() }"`); messages region (`<div id="messages">`); chat error region (`<div id="chat-error">`); chat form (`hx-post="/api/chat"`, `hx-target="#messages"`, `hx-swap="beforeend"`, `hx-headers='js:{ "X-Session-Id": sessionId }'`, `hx-include="[name=persona]"`); metrics badges row (`<div id="metrics-badges">`).
- `pages/explore.html.j2` — extends base; 5 panels; persistent search input (Panel 1+2+5 share the query); `<input hx-trigger="keyup changed delay:300ms" hx-post="/api/vector-demo" hx-target="#search-results" name="query">` driving the result list; secondary `hx-get="/api/explain-plan"` on the same input with longer debounce (500ms) targeting `#plan`.
- `partials/message.html.j2` — single chat-message bubble: human/AI variant via `{% if message.source == 'human' %}`; intent badge; cached badge; latency span; `<article class="message ...">` root.
- `partials/search_result.html.j2` — single result row: name, description, similarity bar (CSS `width: {{ result.similarity }}%`), price.
- `partials/plan_lines.html.j2` — `<pre id="plan-output" class="overflow-x-auto text-sm">{% for line in plan_lines %}{{ line }}{% endfor %}</pre>` plus a small summary header (`{{ plan_summary.index_used }}` etc.) when present.
- `partials/chat_error.html.j2` — `<div class="rounded-lg bg-danger/10 px-3 py-2 text-danger">{{ error }}</div>`. Targeted by `Retarget(target="#chat-error")` on validation failure.
- `partials/_metrics_badges.html.j2` — small fragment used as `hx-swap-oob="true"` payload from `POST /api/chat` to refresh latency/cached/intent badges.
- `partials/_flash.html.j2` — single fragment rendering `<div id="flash-region" hx-swap-oob="afterbegin">` with `{% for f in get_flashes() %}<div class="flash flash-{{ f.category }}" role="alert">{{ f.message }}</div>{% endfor %}`. Included from `base.html.j2` for full-page renders **and** included from `partials/_chat_response.html.j2` for HTMX swaps. `get_flashes()` pops messages from session — render-once semantics. Categories used: `info`, `success`, `warning`, `error`.
- `partials/_chat_response.html.j2` — composing wrapper for the chat happy path: `{% include "partials/message.html.j2" %}{% include "partials/_metrics_badges.html.j2" %}{% include "partials/_flash.html.j2" %}`. The HTMX response handler returns a single `HTMXTemplate(template_name="partials/_chat_response.html.j2", ...)`; the message bubble appends to `#messages` while the metrics + flash fragments OOB-swap into their own regions.

### `main.js` (canonical content for this chapter)

```js
import "htmx.org"
import Alpine from "alpinejs"
import ApexCharts from "apexcharts"
import { registerHtmxExtension } from "litestar-vite-plugin/helpers"
import "./styles.css"

window.Alpine = Alpine
window.ApexCharts = ApexCharts
Alpine.start()
registerHtmxExtension()  // wires CSRF (X-CSRFToken) + ls-* JSON templating
```

Notes:
- `registerHtmxExtension()` reads `<meta name="csrf-token">` (verified in `dist/js/helpers/csrf.js:19-30`) and forwards it on every HTMX request as `X-CSRFToken`. **No manual `htmx:configRequest` listener needed.**
- `htmx-ext-response-targets` is not imported — `Retarget` is the server-side equivalent and we don't need `hx-target-error` until error volume justifies it. Document the tradeoff in `patterns.md`.
- Importing `"htmx.org"` runs HTMX's auto-init on `DOMContentLoaded`; no explicit `htmx.process(document.body)` needed in the standard case.

### `styles.css` (canonical content)

```css
@import "tailwindcss";
@source "../app/domain/web/templates";

@theme {
  --color-canvas: #111113;
  --color-deep: #09090b;
  --color-surface: #18181b;
  --color-surface-strong: #27272a;
  --color-border: rgba(255, 255, 255, 0.1);
  --color-strong: #ffffff;
  --color-base: #e4e4e7;
  --color-muted: #a1a1aa;
  --color-accent: #a16207;
  --color-accent-strong: #ca8a04;
  --color-accent-soft: rgba(161, 98, 7, 0.15);
  --color-success: #4ade80;
  --color-danger: #f87171;
  --font-sans: "Inter", "Space Grotesk", "Sora", system-ui, sans-serif;
}

/* Chat bubble + chart-container helpers go below as @utility / @layer components */
```

`@source "../app/domain/web/templates";` tells Tailwind v4 to scan the Jinja templates directory for utility-class strings — without it the v4 auto-detector misses `.html.j2` files. The relative path resolves from `src/resources/styles.css` to the web-domain templates package.

### Requirements

1. **Source-tree flatten (Phase 1)** — `src/py/app/` → `src/app/`, `src/py/tests/` → `src/tests/`. After Phase 1, `src/py/` does not exist.
2. **React deletion (Phase 2)** — `src/js/` is deleted *in full* (after Phase 3.4 rescues `src/js/public/`).
3. **Resources scaffold (Phase 3)** — `src/resources/` (new): `main.js`, `styles.css`, `public/` (24 carryover assets), `generated/` (empty placeholder dir).
4. **Templates scaffold (Phase 4)** — `src/app/domain/web/templates/` (new — co-located with the new `web` Python sub-package `src/app/domain/web/__init__.py`): base + `_nav` + `pages/chat` + `partials/{message,search_result,chat_error,_metrics_badges}` (Phase 4 ships the chat-only set; explore-page templates land in Phase 5.2-5.3).
5. **Top-level toolchain (Phase 3.6)** — `package.json`, `vite.config.ts`, `tsconfig.json` at repo root. `pyproject.toml`, `Makefile`, `Dockerfile{,.distroless}`, `manage.py`, `.gitignore` updated for the flatten + npm/node toolchain.
6. **Python wiring (Phase 4.4-4.5)** — `litestar.plugins.htmx` and `litestar.plugins.flash` ship with Litestar 2.x core (no new PyPI dep). `src/app/lib/settings.py:ViteSettings.get_config()` flips `mode="spa"` → `mode="template"`, `executor="bun"` → `executor="node"`, retargets `BUNDLE_DIR` from `BASE_DIR / "server" / "static" / "dist"` to `BASE_DIR / "domain" / "web" / "static" / "dist"`, adds `resource_dir=Path("src/resources")`, sets `TypeGenConfig(generate_sdk=False, generate_routes=False, generate_schemas=False, generate_page_props=False)`. `ApplicationCore.on_app_init` adds `TemplateConfig(directory=BASE_DIR / "domain" / "web" / "templates", engine=JinjaTemplateEngine)` and appends `HTMXPlugin()` plus `FlashPlugin(FlashConfig(template_config=app_config.template_config))` to the plugin list. `FlashPlugin` rides the existing `ServerSideSessionConfig(store="sessions")` middleware backed by `OracleAsyncStore` (`src/app/config.py:60-61`) — no extra middleware, no extra store. `csrf.header_name` is changed to `"X-CSRFToken"` in `app/config.py:46-50` (and the corresponding `CSRF_HEADER_NAME` default in `app/lib/settings.py:261`).
7. **`POST /api/chat` HTMX branch (Phase 4.7)** — when `request.htmx`, returns:
   - On success: build the metrics dict and call `flash(request, f"Reply in {latency_ms} ms{' (cache hit)' if cached else ''}", "info" if not cached else "success")`. Then return `HTMXTemplate(template_name="partials/_chat_response.html.j2", context={"message": reply, "metrics_badges": badges}, trigger_event="chat:reply-rendered", after="swap")`. The wrapper template composes `partials/message.html.j2` + OOB `partials/_metrics_badges.html.j2` + OOB `partials/_flash.html.j2` in one response — one round-trip, three regions updated.
   - On `ValidationException`: `HTMXTemplate(template_name="partials/chat_error.html.j2", context={"error": str(exc)}, re_target="#chat-error", re_swap="innerHTML")`. **Wrap the `validate_message` call in a try/except inside the handler** so the exception path can return an HTMX response instead of bubbling. (Local error — no flash; the `chat_error.html.j2` partial is the right surface.)
   - On non-HTMX requests: returns `CoffeeChatReply` JSON exactly as today.
   - **OpenAPI return-type annotation stays `-> CoffeeChatReply`.** `HTMXTemplate` is a `Response` subclass; Litestar accepts that. Phase 0.7 verifies OpenAPI doesn't choke. If it does, fall back to a separate `POST /fragments/chat` endpoint and document.
8. **`POST /api/vector-demo` HTMX branch (Phase 5.6)** — when `request.htmx`, returns `HTMXTemplate(template_name="partials/search_result_list.html.j2", context={"results": demo_results, "query": query})` plus a `PushUrl(push_url=f"/explore?q={quote(query)}")`. (`partials/search_result_list.html.j2` is a tiny wrapper that loops over results and includes `partials/search_result.html.j2`.) Otherwise: JSON as today.
9. **`GET /api/metrics/charts` (Phase 5.1a)** — new handler in `src/app/domain/system/controllers/_metrics.py`. Returns `{labels: list[str], series: {total_ms: list[float], oracle_ms: list[float], embedding_ms: list[float]}}` shaped for ApexCharts line-chart. Reads from `search_metric` aggregations via existing service methods; one new named SQL `metrics-time-series` in `src/app/db/sql/system.sql`.
10. **`GET /api/explain-plan?query=<text>` (Phase 5.1b)** — new handler in `src/app/domain/products/controllers/_vector.py`. Embeds the query via injected `VertexAIService`, then runs **two driver calls**:
    1. `await driver.execute("EXPLAIN PLAN FOR " + db_manager.get_sql("vector-search-products").to_sql(), query_vector=..., threshold=0, limit=5)` — Oracle's `EXPLAIN PLAN FOR` cannot be parameterized as a named-SQL select wrapper, so the implementation builds the explain-prefix in code and uses the same parameter binds as the underlying select. **Risk gate Phase 0.6 verifies bind variables work in `EXPLAIN PLAN FOR`.**
    2. `rows = await driver.select("SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY())")` — returns `plan_table_output VARCHAR2`.
    Returns `{plan_lines: [str], plan_summary: {index_used: str | None, target_accuracy: int | None}}`. Summary fields parsed by string-matching `VECTOR INDEX RANGE SCAN` and `TARGET ACCURACY n` in plan output.
11. **`GET /api/classify-compare` (Phase 5.1c)** — new handler in `src/app/domain/system/controllers/_explore.py` (new file). Reads `BASE_DIR.parents[1] / "dist" / "classify-compare.json"` (matches Ch 3 contract `Path.cwd() / "dist" / "classify-compare.json"` when run from repo root). On missing file: `raise NotFoundException(detail={"hint": "run uv run coffee classify-compare to generate this dataset"})`. On present: returns `{rows: [{phrase, gold, legacy, new}, ...], summary: {per_intent: {<INTENT>: {precision, recall, agreement}}}}`.
12. **CSRF** — `<meta name="csrf-token" content="{{ csrf_token() }}">` in `base.html.j2`. `registerHtmxExtension()` reads it and forwards `X-CSRFToken` automatically. Litestar `CSRFConfig.header_name = "X-CSRFToken"` (Phase 4.5 changes this from `"X-XSRF-TOKEN"`).
13. **Test fixture (Phase 7.1)** — add `htmx_client` fixture to `src/tests/conftest.py`: `AsyncTestClient(app=app, raise_server_exceptions=False, headers={"HX-Request": "true"})`. Used by all HTMX-flavored tests.
14. **Visual polish (PRD constraint)** — port the dark-theme tokens verbatim. Persona switcher renders as a segmented control. Chat bubbles use `rounded-xl` with subtle shadow. Cards on Panel 3 use `bg-surface border-border`. Charts use the accent palette. **Manual checklist verified via Playwright `browser_console_messages` snapshot** captured in Beads notes for the final task.
15. **No `make frontend-dev` target** — `litestar-vite` auto-launches Vite when `dev_mode=True` (Ch 1 verified `RuntimeConfig`). Single dev command: `VITE_DEV_MODE=true uv run coffee run`.
16. **Dockerfile** updates: `npm` not `bun`; `package.json` at repo root; `src/{app,resources,templates,tests}` instead of `src/{py,js}`. Phase 6.4.
17. **Manage.py path** — `sys.path.insert(0, str(SCRIPT_DIR / "src" / "py"))` becomes `sys.path.insert(0, str(SCRIPT_DIR / "src"))`. Phase 1.5.

### Acceptance Criteria

- `find src/py src/js -maxdepth 0 2>/dev/null | wc -l` returns **0** (the directories are gone).
- `find src/app src/resources src/templates src/tests -maxdepth 0 | wc -l` returns **4**.
- `ls vite.config.ts package.json` succeeds at repo root; `ls src/js 2>/dev/null` fails.
- `grep -E "react|tanstack|radix|lucide|@vitejs/plugin-react|biome" package.json` returns **zero** matches.
- `grep -E "bun" Makefile pyproject.toml tools/deploy/docker/run/Dockerfile{,.distroless}` returns **zero** code-path matches (only allowed in comments/docs).
- `find src/templates -name "*.html.j2" | wc -l` returns **≥ 8** (the inventory above).
- `grep -rn "BASE_DIR.parents\[2\]" src/app` returns **zero** matches; `grep -rn "BASE_DIR.parents\[1\]" src/app` returns **2** (settings.py + _system.py).
- `make install` from a clean checkout succeeds (`uv sync` + `npm ci`).
- `make build` succeeds (`uv build` + `npm run build` via `python manage.py assets build`).
- `uv run coffee --help` shows only `run`, `bulk-embed`, `clear-cache`, `model-info`, `load-fixtures`, `export-fixtures` — no `assets`, `upgrade`, `downgrade`, or `database` group (`test_cli_surface.py` enforces).
- `uv run python manage.py --help` exposes `init / install / doctor / infra / database / assets`; `database upgrade` and `assets build` both reachable.
- `make lint` green (ruff + mypy + pyright + Tailwind/Vite TS check via `tsc --noEmit`; biome removed).
- `make test` green; new tests:
  - `src/tests/api/test_pages.py` — `/`, `/explore` render with expected anchors.
  - `src/tests/api/test_chat_partial.py` — HTMX branch returns partial HTML.
  - `src/tests/api/test_explain_plan.py` — returns 200 with `plan_lines` containing "VECTOR" (real Oracle integration path).
  - `src/tests/api/test_classify_compare_endpoint.py` — fixture-based file present/missing branches.
  - `src/tests/unit/test_metrics_charts_shape.py` — `/api/metrics/charts` shape matches the spec.
- `uv run coffee run` boots; `curl -s localhost:5006/` returns HTML containing `hx-ext="litestar"` and `<meta name="csrf-token"`.
- Browser smoke (manual, document in Beads notes):
  - `/` chat works end-to-end with mocked LLM.
  - `/explore` shows 5 panels; live search updates results + Push-Url; EXPLAIN-PLAN renders with `VECTOR INDEX RANGE SCAN`.
  - HMR works: edit `pages/chat.html.j2` → page hot-swaps without full reload.
  - Console clean (Playwright `browser_console_messages` snapshot captured).
- `litestar assets generate-types` is a no-op (all `generate_*` flags off); not part of `make install`.

### Risks / Known Gotchas

- **`BASE_DIR.parents[2]` shifts** during the flatten. Phase 1.6 audits and rewrites both call sites in the same atomic commit as the directory move; otherwise Vite root and the favicon handler break before Phase 4 wires the new mode. Test: `python -c "from app.lib.settings import BASE_DIR; print(BASE_DIR.parents[1])"` should print `<repo-root>` after Phase 1.
- **CSRF header rename** (`X-XSRF-TOKEN` → `X-CSRFToken`). Any external API consumer relying on the old header breaks. Acceptable for a reference demo per PRD constraint #3 (no backward-compat shims). Document in `patterns.md`.
- **Flatten-then-delete order is load-bearing.** Phase 1 (flatten) must finish (and tests must pass) before Phase 2 (delete `src/js`). If Phase 2 runs first, `BASE_DIR.parents[2] / "src" / "js" / "public" / "favicon.ico"` returns 500 in the running app and tests fail. Phase 3.4 (asset rescue) runs *between* 2 and the new layout to avoid an interim missing-asset window.
- **Tailwind v4 + `@source "../templates"`** is required for utility-class detection in `.html.j2` files. Without it, build silently emits a CSS file missing classes used by templates. Phase 7 includes a smoke build with grep-asserts on at least 3 utility classes appearing in the bundle.
- **HTMX 2.x vs 1.x** — HTMX 2 changed default behaviors (e.g., `hx-on:` syntax, `hx-swap` defaults). Phase 0.4 confirms `htmx.org@2.0.10` works with `litestar-vite-plugin/helpers` `registerHtmxExtension()`.
- **ApexCharts bundle size** — ~150KB gzipped, not tree-shakable. Acceptable for a reference demo; charts are Panels 4 and 5 only. Document in `patterns.md`.
- **EXPLAIN PLAN with bind variables** — Oracle has historically accepted `EXPLAIN PLAN FOR SELECT ... WHERE col = :v`, but the named SQL we wrap (`vector-search-products`) uses `VECTOR_DISTANCE(embedding, :query_vector, COSINE)` with a `VECTOR(3072)` bind. Phase 0.6 risk gate: a one-shot integration test against a fixture-loaded DB to confirm the bind succeeds and the plan output mentions the HNSW index. If it fails, fall back to a *parameter-stripped* explain plan against a representative query embedding hard-baked into the controller (less educational; document the compromise).
- **EXPLAIN-PLAN per-keystroke is wasteful.** Client debounce: `hx-trigger="keyup changed delay:500ms"` (longer than the 300ms search-results debounce on the same input).
- **`HTMXTemplate` from a JSON-annotated handler** — Litestar's response-type machinery accepts `Response` subclasses returned from a handler annotated with a non-`Response` type, but OpenAPI schema generation may produce noise. Phase 0.7 risk gate: hit `/schema/openapi.json` and confirm `/api/chat` declares `CoffeeChatReply` only (no spurious extra `text/html` schema). If OpenAPI is noisy, split into `POST /api/chat` (JSON only) + `POST /fragments/chat` (HTMX only) and update the chat form's `hx-post` accordingly. This is a known fallback; add a Phase 4 note.
- **Vite dev server origin mismatch** — `server.cors: true` in `vite.config.ts` is mandatory; without it HMR XHRs from `localhost:5006` to `localhost:5173` fail with CORS errors.
- **Dishka + `from __future__ import annotations`** — global PRD constraint #2. The new `_pages.py` controller and `_explore.py` controller follow the existing convention (no `__future__` import). Reviewers reject otherwise.
- **The page on `/` becomes server-rendered.** Old `dashboard` SPA route disappears. PRD considers this acceptable (no auth, simple-greater-than-clever).
- **CLI restructure breaking change** (Phase 1.8). Three external surfaces shift in one phase:
  - `coffee upgrade` → `python manage.py database upgrade`. Anyone with shell aliases or CI runbooks pointing at `coffee upgrade` breaks. Acceptable for a reference demo per PRD constraint #3 (no backward-compat shims). README + Makefile updated in same phase; document the rename in the doc-touch (Phase 7.4).
  - `coffee assets *` removed entirely. Same rationale.
  - `coffee database *` removed entirely (sqlspec migrations now only on `manage.py database`).
  Mitigation: `test_cli_surface.py` includes assertions for what *is* present, so accidental regressions in either direction (re-mounting, or losing a command) fail loudly. Also: `coffee --help` printout is captured in Beads notes during Phase 1.9 so the new surface is documented at the moment of switch.
- **`litestar_granian` run-command import-shape risk.** Phase 1.8's `coffee run` wraps `litestar_granian.cli:run_command` lazily. Accelerator does this in `dma/cli/commands/server.py:40-55` via a `_create_run_command` helper that copies `original_command.params`. If the granian floor in `pyproject.toml` ever bumps in a way that changes the `run_command` callable shape, the wrapper breaks. HALT GATE 0.9 verifies the import; the unit test `test_coffee_retains_runtime_commands` verifies the registration; manual `make run` smoke in Phase 1.10 verifies end-to-end boot.

---

## Implementation Plan

### Phase 0: HALT GATE — toolchain verification (`oracledb-vertexai-4d6.4.0`)

**No subsequent phase runs unless every check below passes.** Document each result in Beads notes on `oracledb-vertexai-4d6.4.0`.

- [ ] **0.1** `litestar-vite` mode + TypeGen surface. `uv run python -c "from litestar_vite import ViteConfig, PathConfig, RuntimeConfig, TypeGenConfig; ViteConfig(mode='template', paths=PathConfig(resource_dir='src/resources'), runtime=RuntimeConfig(executor='node'), types=TypeGenConfig(generate_sdk=False, generate_routes=False, generate_schemas=False, generate_page_props=False)); print('OK')"`. Fail → halt and re-research.
- [ ] **0.2** Litestar built-in HTMX import surface. `uv run python -c "from litestar.plugins.htmx import HTMXPlugin, HTMXRequest, TriggerEvent, Reswap, Retarget, PushUrl, HTMXTemplate; print('OK')"`. Confirms HTMX support resolves from the existing `litestar[jinja,...]` install — **no separate `litestar-htmx` package is added.** If any name fails to import, the installed Litestar version is too old; bump the floor in `pyproject.toml` and re-run.
- [ ] **0.3** npm package versions. Read `~/code/litestar/litestar-vite/examples/jinja-htmx/package.json` for canonical pins. Confirm `htmx.org@2.0.10`, `@tailwindcss/vite@4.2.4`, `tailwindcss@4.2.4`, `litestar-vite-plugin@0.22.x`, `vite@8.x`. Add `alpinejs@^3.15`, `apexcharts@^5.10`. Record in Beads notes.
- [ ] **0.4** `registerHtmxExtension()` + HTMX 2.x compatibility. Scaffold a throwaway directory: `mkdir /tmp/h-check && cd /tmp/h-check && npm init -y && npm i htmx.org@2.0.10 litestar-vite-plugin@latest && node -e "import('litestar-vite-plugin/helpers').then(m => console.log(typeof m.registerHtmxExtension))"`. Expect `function`. If module not found, halt.
- [ ] **0.5** `executor="node"` runs end-to-end. After 0.1 + 0.3, scaffold a minimal app via `mkdir /tmp/lv-check && cd /tmp/lv-check && uv run litestar-vite-plugin init --template jinja-htmx` (or hand-craft if the CLI lacks the template). Run `litestar assets status` and confirm it doesn't error. If it does, fall back: pin `executor="node"` and document the minimum reproducer.
- [ ] **0.6** EXPLAIN PLAN with VECTOR bind. After Ch 1's fixtures load: `uv run python -c "..."` script that opens a driver session, runs `EXPLAIN PLAN FOR <vector-search-products SQL>` with a real 3072-dim embedding bind, then `SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY())`. Confirm output contains "VECTOR INDEX RANGE SCAN" or equivalent. **If bind fails**, document the failure mode and switch Phase 5.1b to use a hard-coded representative embedding; update the spec risks section.
- [ ] **0.7** OpenAPI tolerance for `HTMXTemplate` returns. Boot the app post-Phase-4.7 in a scratch fixture (or stub a controller now): `await client.get("/schema/openapi.json")` → confirm `/api/chat` POST declares `CoffeeChatReply` schema only. If multiple content-types appear, switch to the split-endpoint fallback (Phase 4.7 notes).
- [ ] **0.8** CSRF token reachable in Jinja. Boot a tiny app with `TemplateConfig(engine=JinjaTemplateEngine, ...)` + `CSRFConfig(secret="x", header_name="X-CSRFToken")`. Render a template containing `{{ csrf_token() }}` against a fake request. Confirm it returns a non-empty string. Source: `litestar.contrib.jinja:55` registers the callable.
- [ ] **0.9** CLI restructure import shape. `uv run python -c "from litestar_granian.cli import run_command; from sqlspec.cli import add_migration_commands; from litestar_vite.cli import vite_group; from litestar.cli._utils import LitestarEnv; print('OK')"`. Confirms the four functions/groups Phase 1.8 needs (granian run command lazy-wrap, sqlspec migrations on `manage.py database`, vite_group already mounted on `manage.py assets`, LitestarEnv lazy construction inside a custom click group) all import cleanly from the existing dependency floors. Read `dma/accelerator/src/py/dma/cli/main.py:28-44`, `dma/accelerator/src/py/dma/cli/commands/server.py:24-58`, and `dma/accelerator/manage.py:386-413` as the canonical reference patterns. Halt if any import fails.

### Phase 1: Source-tree flatten + CLI restructure (`oracledb-vertexai-4d6.4.9`)

Target end state: `src/app/`, `src/tests/`, with `coffee` as a hand-rolled `rich_click` group (no `litestar_group()` call) and migrations/assets reachable only via `manage.py`. Atomic with the `BASE_DIR.parents[*]` audit so the app keeps booting.

**Sub-phase 1A (1.1–1.7): directory move.** Sub-phase 1B (1.8–1.10): CLI restructure. Sub-phase 1A must finish green before 1B begins so the CLI work happens against final paths.

- [ ] **1.1** `git mv src/py/app src/app` (single git operation; preserves history). `git mv src/py/tests src/tests`. `rmdir src/py`.
- [ ] **1.2** `pyproject.toml` updates:
  - `[tool.hatch.build.targets.sdist] packages = ["src/app"]` (was `["src/py/app"]`).
  - `[tool.hatch.build.targets.wheel] packages = ["src/app"]`.
  - `[tool.hatch.build] dev-mode-dirs = ["src", "."]` (was `["src/py", "."]`).
- [ ] **1.3** `Makefile` — replace every `src/py` and `src/js` reference with the new paths AND route every `coffee assets *` / `coffee upgrade` invocation through `python manage.py *` (these subcommands disappear from `coffee` in 1.8). Specifically:
  - `clean` target (`src/js/dist`, `src/js/node_modules` → `dist/`, `node_modules/`).
  - `test` target (`src/py/tests` → `src/tests`).
  - `lint` target (`src/py/app` → `src/app`, drop `cd src/js && bun run fix`).
  - `mypy`/`pyright` (`src/py/app` → `src/app`).
  - `lock` (drop `src/js && bun install`).
  - `install` target: drop `install-bun`; drop `@uv run coffee assets generate-types >/dev/null 2>&1` line entirely; rewrite `@uv run coffee assets install` → `@uv run python manage.py assets install`.
  - `destroy` (drop `src/js/node_modules src/js/dist`).
  - `assets-build` target: rewrite `@uv run coffee assets build` → `@uv run python manage.py assets build`.
  - `migrate` (or equivalent) target: rewrite `@uv run coffee upgrade` → `@uv run python manage.py database upgrade`.
  - Delete the `js-*` targets entirely; delete the `assets-generate-types` target (use `python manage.py assets generate-types` directly when needed).
  - `coffee load-fixtures` and `coffee run` references stay (those subcommands remain on `coffee` per 1.8).
- [ ] **1.4** Test fixture path `src/py/tests` → `src/tests` in `pytest.ini`/`pyproject.toml` `[tool.pytest.ini_options]` (`testpaths`).
- [ ] **1.5** `manage.py:39` — `sys.path.insert(0, str(SCRIPT_DIR / "src" / "py"))` → `sys.path.insert(0, str(SCRIPT_DIR / "src"))`. Failing test: `python manage.py --help` prints commands without ImportError.
- [ ] **1.6** **`BASE_DIR.parents[*]` audit.** Edit `src/app/lib/settings.py:408` from `BASE_DIR.parents[2] / "src" / "js"` to `BASE_DIR.parents[1]` (root will be the repo, `resource_dir` carries `src/resources`). Edit `src/app/domain/system/controllers/_system.py:28` from `BASE_DIR.parents[2] / "src" / "js" / "public" / "favicon.ico"` to `BASE_DIR.parents[1] / "src" / "resources" / "public" / "favicon.ico"` (Phase 3.4 will populate this directory; the favicon handler temporarily 500s between Phase 1 and Phase 3.4). **Failing test that must pass after Phase 3.4 lands: `src/tests/unit/test_base_dir_audit.py` asserts `BASE_DIR.parents[1].name == <repo-name>` and the favicon path resolves.**
- [ ] **1.7** Run `make lint && make test` (Python only — frontend is mid-rewrite). Both must pass before sub-phase 1B starts. Smoke: `uv run coffee --help` lists commands (still via `litestar_group` at this point — 1.8 changes that).
- [ ] **1.8** **CLI restructure — `coffee` becomes hand-rolled.** Mirrors `dma/accelerator/src/py/dma/cli/main.py` and `dma/accelerator/src/py/dma/cli/commands/server.py`.
  - **Rewrite `src/app/__main__.py`:** `run_cli()` no longer calls `litestar_group()`. Instead: `from app.cli import main; main()`. Keep `setup_environment()` for env-var defaults but drop the `LitestarExtensionGroup.format_help` monkey-patch (no longer needed with a plain click group).
  - **New package `src/app/cli/main.py`:** `@rich_click.group(name="coffee", help="Cymbal Coffee — Oracle 23ai + Vertex AI demo CLI", context_settings={"help_option_names": ["-h", "--help"]})` decorated `cli()` callback (analogous to `dma/cli/main.py:28-44`). `main()` function calls `setup_logging()`, imports `app.cli.commands` (side-effecting registration), then `cli()`.
  - **New `src/app/cli/commands/__init__.py`:** `from app.cli.commands import server, manage` (each module side-effects subcommand registration via `@cli.command(...)` decorators).
  - **New `src/app/cli/commands/server.py`:** Wraps `litestar_granian.cli:run_command`. Define a `ServerGroup(click.RichGroup)` whose `invoke()` constructs `LitestarEnv.from_env("app.server.asgi:create_app")` lazily and calls `create_app()`. Mount `run` as the only subcommand under it (or, simpler: top-level `coffee run` that wraps the granian command directly via the `_create_run_command` helper from `dma/cli/commands/server.py:40-55`). Pick one and document the choice in Beads notes.
  - **New `src/app/cli/commands/manage.py`:** Hosts `bulk_embed_cmd`, `clear_cache_cmd`, `model_info_cmd`, `load_fixtures_cmd`, `export_fixtures_cmd`. Move the implementations from `src/app/cli/commands.py` (the existing file) — they're already plain `@click.command` functions, only the registration changes. **Delete the existing `src/app/cli/commands.py`** after moving (single file → split by concern: `server.py` for runtime, `manage.py` for db/data ops).
  - **Remove `on_cli_init` from `src/app/server/core.py`:** delete lines 125-168 (the entire `on_cli_init` method on `ApplicationCore`). Server-side plugin registration unchanged; the CLI side is now hand-rolled in `app/cli/`.
  - **`coffee` no longer mounts `assets`, `upgrade`/`downgrade`, or `database *`** — these are reachable only via `python manage.py {assets,database} ...`.
  - Failing tests (must RED before code, GREEN after):
    - `src/tests/unit/test_cli_surface.py::test_coffee_does_not_have_assets_group` — invoke `coffee --help` (subprocess or Click test runner against `app.cli.main:cli`) and assert `"assets"` does not appear in the listed commands.
    - `src/tests/unit/test_cli_surface.py::test_coffee_does_not_have_database_group` — same, asserting `"database"` and `"upgrade"`/`"downgrade"` are absent.
    - `src/tests/unit/test_cli_surface.py::test_coffee_retains_runtime_commands` — assert `"run"`, `"bulk-embed"`, `"clear-cache"`, `"model-info"`, `"load-fixtures"`, `"export-fixtures"` are all present.
    - `src/tests/unit/test_cli_surface.py::test_manage_py_database_upgrade_works` — invoke `python manage.py database upgrade --help` and assert exit code 0.
    - `src/tests/unit/test_cli_surface.py::test_manage_py_assets_build_works` — invoke `python manage.py assets build --help` and assert exit code 0.
    - `src/tests/unit/test_cli_surface.py::test_coffee_help_does_not_construct_db_config` — patch `app.config.db` constructor with a sentinel that raises; invoke `coffee --help`; assert no exception raised (proves `--help` no longer materializes the SQLSpec config). This is the architectural-improvement assertion that justifies the whole restructure.
- [ ] **1.9** Smoke validation post-restructure: `uv run coffee --help` shows only the curated production list; `uv run python manage.py --help` shows `init/install/doctor/infra/database/assets`; `uv run python manage.py database --help` lists `upgrade/downgrade/...`; `uv run python manage.py assets --help` lists `install/build/serve/generate-types`. Document the help-text outputs in Beads notes.
- [ ] **1.10** Run `make lint && make test` again. Confirm `test_cli_surface.py` is green and no other tests regressed. Smoke: `make migrate` (which now calls `python manage.py database upgrade`) and `uv run coffee bulk-embed --help` both work.

### Phase 2: Delete React frontend (`oracledb-vertexai-4d6.4.10`)

**Precondition: Phase 1 green.** Order: rescue `src/js/public/`, then `git rm -r src/js`.

- [ ] **2.1** `mkdir -p src/resources/public && git mv src/js/public/* src/resources/public/` (preserves history for the 23 SVG/icon assets). Verify: `ls src/resources/public/ | wc -l` returns `23`.
- [ ] **2.2** `git rm -r src/js`. Verify: `ls src/js 2>&1` errors.
- [ ] **2.3** `.gitignore` audit — remove all `src/js/`-specific lines (`!src/js/src/lib/`, `!src/js/src/lib/**`, `src/js/.litestar.json`, `src/js/public/hot`, `src/js/tsconfig.tsbuildinfo`, `src/js/tsconfig.node.tsbuildinfo`, `src/js/vite.config.js`, `src/js/vite.config.d.ts`, `src/js/src/lib/generated/`) AND scrub the Phase 1A leftovers (`src/py/app/server/static/dist/hot`, `!src/py/app/lib`). Add the new ignores: `src/app/domain/web/static/dist/` (Vite output, including the HMR marker) and `src/resources/generated/` (TypeGen output). `node_modules` is already ignored.
- [ ] **2.4** Failing test (added now, will pass after Phase 3.4): `src/tests/api/test_static_assets.py::test_favicon_resolves` asserts `await client.get("/favicon.ico")` returns 200 with `image/x-icon`. **Skip this test until Phase 3.4** via `pytest.skip("Phase 3.4 not yet complete")` — Phase 3.4 removes the skip.

### Phase 3: New frontend scaffold (`oracledb-vertexai-4d6.4.11`)

- [ ] **3.1** `package.json` at repo root. Dependencies: `htmx.org@2.0.10`, `alpinejs@^3.15`, `apexcharts@^5.10`. devDependencies: `vite@8.x`, `@tailwindcss/vite@4.2.4`, `tailwindcss@4.2.4`, `litestar-vite-plugin@0.22.x`, `typescript@5.x` (vite needs it even though we're not writing TS in this chapter). Scripts: `"dev": "vite"`, `"build": "vite build"`, `"preview": "vite preview"`. **No biome, no bun-specific scripts.**
- [ ] **3.2** `vite.config.ts` at repo root. Copy verbatim from `~/code/litestar/litestar-vite/examples/jinja-htmx/vite.config.ts`, then change:
    ```ts
    plugins: [
      tailwindcss(),
      litestar({
        input: ["src/resources/main.js", "src/resources/styles.css"],
        bundleDir: "src/app/domain/web/static/dist",
        hotFile: "src/app/domain/web/static/dist/hot",
        assetUrl: "/static/dist/",
        resourceDir: "src/resources",
      }),
    ],
    server: { host: "0.0.0.0", port: 5173, strictPort: true, cors: true },
    ```
    Keep the `bundlerKey` switch for vite 8 / rolldown compatibility.
- [ ] **3.3** `src/resources/styles.css` — content per the *styles.css* block in this spec (Tailwind import, `@source "../templates"`, `@theme` tokens carried over from the React `index.css`). Failing test: `src/tests/unit/test_styles_source.py` asserts the file contains `@import "tailwindcss"` and `@source "../templates"`.
- [ ] **3.4** `src/resources/main.js` — content per the *main.js* block in this spec. Verify Phase 2.4's skipped test now passes (favicon resolves through `src/resources/public/favicon.ico`).
- [ ] **3.5** `tsconfig.json` at repo root — minimal: `{ "compilerOptions": { "target": "ES2022", "module": "ESNext", "moduleResolution": "bundler", "strict": true, "skipLibCheck": true } }`. (No code is TS in this chapter, but vite + the litestar plugin expect a tsconfig to exist.)
- [ ] **3.6** Failing test: `src/tests/unit/test_repo_layout.py` asserts `Path("vite.config.ts").exists() and Path("package.json").exists() and not Path("src/js").exists()`. Run `npm install` and assert `package-lock.json` exists. Run `npm run build` and assert `src/app/domain/web/static/dist/manifest.json` exists.

### Phase 4: Python wiring + chat templates (`oracledb-vertexai-4d6.4.1`, rewritten)

- [ ] **4.1** No new PyPI dependency. `litestar.plugins.htmx` ships with the existing `litestar[jinja,...]` install (Phase 0.2 already verified). Skip — keep the slot for any small fix-ups uncovered by Phase 4 tests.
- [ ] **4.2** `src/app/lib/settings.py:ViteSettings.get_config()`:
    ```python
    return ViteConfig(
        mode="template",
        dev_mode=self.DEV_MODE,
        types=TypeGenConfig(
            output=Path("src/resources/generated"),
            generate_sdk=False,
            generate_routes=False,
            generate_schemas=False,
            generate_page_props=False,
        ),
        paths=PathConfig(
            root=BASE_DIR.parents[1],
            resource_dir=Path("src/resources"),
            bundle_dir=self.BUNDLE_DIR,
            asset_url=self.ASSET_URL,
        ),
        runtime=RuntimeConfig(executor="node", host=self.HOST, port=self.PORT),
    )
    ```
    Failing test: `src/tests/unit/test_vite_settings_shape.py` asserts the returned config has `mode == "template"` and `runtime.executor == "node"`.
- [ ] **4.3** `src/app/server/core.py:ApplicationCore.on_app_init`:
    ```python
    from litestar.config.template import TemplateConfig
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.plugins.flash import FlashConfig, FlashPlugin
    from litestar.plugins.htmx import HTMXPlugin

    app_config.template_config = TemplateConfig(
        engine=JinjaTemplateEngine,
        directory=BASE_DIR / "domain" / "web" / "templates",
    )
    # HTMXPlugin first (no template dependency); FlashPlugin needs the Jinja
    # engine instance built by TemplateConfig, so it must run after the
    # template config is in place — appending here is fine because plugin
    # `on_app_init` runs in registration order.
    app_config.plugins.append(HTMXPlugin())
    app_config.plugins.append(
        FlashPlugin(config=FlashConfig(template_config=app_config.template_config)),
    )
    ```
    `FlashPlugin` registers a `get_flashes()` Jinja global that pops `request.session["_messages"]`. Flash relies on the existing `ServerSideSessionConfig(store="sessions")` middleware — no new infrastructure (the Oracle-backed `OracleAsyncStore` from `src/app/config.py:60-61` is already wired). Failing tests:
    - `src/tests/unit/test_app_plugins.py` — asserts the plugin list contains `HTMXPlugin`, `FlashPlugin`, and that `template_config` is set.
    - `src/tests/api/test_flash_messages.py::test_flash_round_trip` — boots the app, posts a message that triggers a `flash(request, "saved", "success")` call (e.g. `POST /api/cache/clear`), follows up with a `GET /` and asserts the rendered HTML contains `flash flash-success` exactly once; a second `GET /` proves the message was popped.
- [ ] **4.4** `src/app/lib/settings.py:259-264` change `CSRF_HEADER_NAME` default `"X-XSRF-TOKEN"` → `"X-CSRFToken"`. `src/app/config.py:46-50` carries through. Failing test: `src/tests/unit/test_csrf_header.py` boots the app and asserts `app.csrf_config.header_name == "X-CSRFToken"`.
- [ ] **4.4b** Create `src/app/domain/web/__init__.py` with a one-line docstring (`"""Web domain — Jinja templates and the litestar-vite bundle output for the HTMX frontend."""`). The package marker turns `domain/web` into a peer-domain alongside `chat`/`products`/`system`.
- [ ] **4.4c** Wire flash usage into the chat success path so the global `flash-region` exercises the wiring end-to-end: on a successful `POST /api/chat`, `flash(request, f"Reply in {latency_ms} ms", "info")` (or the `cached`/`fresh` distinction). The OOB-swap response automatically renders `partials/_flash.html.j2` and pops the message. Confirms the flash → session → Jinja-global → OOB-swap loop without needing a separate non-HTMX action surface to test it.
- [ ] **4.5** Create `src/app/domain/web/templates/base.html.j2` per the templates inventory above (vite_hmr + vite + csrf meta + hx-ext body + nav + content block).
- [ ] **4.6** Create `src/app/domain/web/templates/_nav.html.j2`, `src/app/domain/web/templates/pages/chat.html.j2`, `src/app/domain/web/templates/partials/{message,chat_error,_metrics_badges}.html.j2`. Use the dark theme tokens from `styles.css` via Tailwind utilities (`bg-canvas`, `text-base`, `border-border`, `bg-accent`, etc.).
- [ ] **4.7** **Failing tests first**, then implement:
    - `src/tests/api/test_pages.py::test_chat_page_renders` — `GET /` returns 200, body contains `hx-ext="litestar"`, `id="messages"`, `id="metrics-badges"`, `<meta name="csrf-token"`.
    - `src/tests/api/test_chat_partial.py::test_htmx_returns_partial` — `htmx_client.post("/api/chat", json={...})` returns 200 with body containing `<article class="message"` and NOT containing `<!DOCTYPE html>`.
    - `src/tests/api/test_chat_partial.py::test_htmx_validation_returns_chat_error` — empty message body returns the `chat_error.html.j2` partial with `HX-Retarget: #chat-error` header.
    - `src/tests/api/test_chat_partial.py::test_non_htmx_returns_json` — `client.post("/api/chat", ...)` (no HX-Request header) returns JSON `CoffeeChatReply`.
- [ ] **4.8** Implement: add `PageController` to `src/app/domain/system/controllers/_pages.py` (one class, two route handlers `GET /` and `GET /explore`; `/explore` raises `NotFoundException` for now — Phase 5.4 swaps in the real template).
- [ ] **4.9** Update `src/app/domain/chat/controllers/_chat.py:send_chat_message` to accept `request: HTMXRequest` (replace the `Request` import) and branch on `request.htmx`. On HTMX + success: return the `HTMXTemplate` per requirements §7. On HTMX + ValidationException: catch the exception and return the `chat_error` partial. On non-HTMX: return `CoffeeChatReply` as today.
    - **OpenAPI risk gate**: Phase 0.7 already verified. If the openapi.json still contains a stray text/html schema, switch to the split-endpoint fallback now and document.
- [ ] **4.10** `src/tests/conftest.py` — add `htmx_client` fixture:
    ```python
    @pytest.fixture
    def htmx_client(app: Litestar) -> AsyncTestClient:
        from litestar.testing import AsyncTestClient
        return AsyncTestClient(app=app, raise_server_exceptions=False, headers={"HX-Request": "true"})
    ```
    Failing test: `src/tests/api/test_chat_partial.py` uses `htmx_client` fixture-by-name; pytest collection would fail without it.
- [ ] **4.11** Run `make test` — Phase 4 tests must pass; Phase 5 tests (still TODO) are skipped.

### Phase 5: Explore page (5 panels) (`oracledb-vertexai-4d6.4.5`, rewritten)

- [ ] **5.1a** `GET /api/metrics/charts` in `src/app/domain/system/controllers/_metrics.py`. Add `metrics-time-series` named SQL to `src/app/db/sql/system.sql`. Returns `{labels: list[str], series: {total_ms, oracle_ms, embedding_ms}}`. Failing test: `src/tests/unit/test_metrics_charts_shape.py` asserts shape with mocked service.
- [ ] **5.1b** `GET /api/explain-plan?query=<text>` in `src/app/domain/products/controllers/_vector.py`. Two driver calls (EXPLAIN PLAN FOR + DBMS_XPLAN.DISPLAY). Returns `{plan_lines, plan_summary}`. Failing test: `src/tests/api/test_explain_plan.py` (integration) asserts plan text contains "VECTOR" — runs against the real Oracle integration fixture.
- [ ] **5.1c** `GET /api/classify-compare` in new `src/app/domain/system/controllers/_explore.py`. Reads `BASE_DIR.parents[1] / "dist" / "classify-compare.json"`. NotFound on missing. Computes per-intent precision/recall/agreement on present. Failing test: `src/tests/api/test_classify_compare_endpoint.py` covers both branches with a tmp-file fixture.
- [ ] **5.1d** Verify `GET /api/metrics/summary` (existing) returns `{cards: [...]}` shape required by Panel 3 `ls-for`. If it doesn't, add a thin shape adapter — do not change the existing endpoint contract. Failing test: `src/tests/unit/test_metrics_summary_cards_shape.py`.
- [ ] **5.2** Create `src/templates/pages/explore.html.j2` with five panels:
    - **Panel 1 (Vector Search)**: `<input name="query" hx-post="/api/vector-demo" hx-trigger="keyup changed delay:300ms" hx-target="#search-results" hx-include="this">`; `<div id="search-results">` rendered from `partials/search_result_list.html.j2`.
    - **Panel 2 (EXPLAIN PLAN viewer)**: same input emits a second event `hx-trigger="keyup changed delay:500ms"` to a parallel `<input>` (or use HTMX `hx-trigger="...,..."` chaining) hitting `/api/explain-plan`; `<div id="plan">` rendered from `partials/plan_lines.html.j2`.
    - **Panel 3 (Metrics summary cards)**: `<div hx-get="/api/metrics/summary" hx-trigger="load, every 10s" hx-swap="json">` with the `<template ls-for="card in $data.cards">` block from the per-panel decision section.
    - **Panel 4 (Latency time-series)**: `<div x-data="latencyChart" x-init="init()"></div>` Alpine component fetching `/api/metrics/charts` and rendering ApexCharts line chart.
    - **Panel 5 (Classify-compare)**: same Alpine pattern fetching `/api/classify-compare`; renders ApexCharts grouped bar (gold vs legacy vs new). NotFound → render the "run the CLI" hint inline.
- [ ] **5.3** Create `src/templates/partials/search_result.html.j2` and `src/templates/partials/search_result_list.html.j2` and `src/templates/partials/plan_lines.html.j2`.
- [ ] **5.4** `PageController.explore` in `_pages.py` — replace the placeholder NotFoundException with `Template(template_name="pages/explore.html.j2")`. Failing test: `src/tests/api/test_pages.py::test_explore_page_renders` asserts body contains all 5 panel IDs.
- [ ] **5.5** `POST /api/vector-demo` HTMX branch in `src/app/domain/products/controllers/_vector.py`. Wrap returned `HTMXTemplate` with `PushUrl(push_url=f"/explore?q={quote(query)}")` (litestar-htmx supports chaining via `HTMXTemplate(push_url=...)`). Failing tests: `src/tests/api/test_vector_demo_partial.py::test_htmx_returns_partial_and_pushes_url`, `::test_non_htmx_returns_json`.
- [ ] **5.6** Alpine components — add small inline `x-data="..."` definitions in `pages/explore.html.j2` for Panels 4 + 5. Each fetches its endpoint via `csrfFetch` (imported in `main.js`) or plain `fetch` (GET, no CSRF needed) and instantiates ApexCharts on the host element.

### Phase 6: Toolchain & deployment (`oracledb-vertexai-4d6.4.4`, rewritten + `oracledb-vertexai-4d6.4.6`, rewritten)

- [ ] **6.1** `pyproject.toml` final pass — confirm no `litestar-htmx` direct dependency was inadvertently added (HTMX comes from `litestar[jinja,...]`). No `bun` references anywhere. Confirm `[tool.hatch.build.targets.wheel].packages = ["src/app"]` and `artifacts` includes `**/*.j2`.
- [ ] **6.2** `Makefile` final pass — Phase 1.3 did most of this. Confirm: `make install` runs `uv sync` + `npm install` (via `uv run python manage.py assets install` which delegates to `NodeExecutor.install`); `make build` runs `uv build` + `npm run build` (via `uv run python manage.py assets build`); `make lint` runs ruff + mypy + pyright + `npx tsc --noEmit`. **No `coffee assets ` or `coffee upgrade` invocations remain in the Makefile** (Phase 1.8 made these unregistered subcommands; `test_cli_surface.py` enforces). Add a small `frontend-typecheck` target wrapping `npx tsc --noEmit` so CI can target it.
- [ ] **6.3** `.gitignore` final pass — verify Phase 2.3 audit landed (no `src/js/` or `src/py/` references; `src/app/domain/web/static/dist/` and `src/resources/generated/` ignored; `node_modules/` ignored). Note: `dist/.gitkeep` does *not* apply to `src/app/domain/web/static/dist/` — that subtree is purely Vite build output and the dir is recreated by `manage.py assets build`. The repo-root `dist/.gitkeep` (for `classify-compare.json`) is unrelated and predates Ch 4.
- [ ] **6.4** `tools/deploy/docker/run/Dockerfile`:
    - Drop the `oven/bun` COPY layer.
    - `COPY package.json package-lock.json ./` (root, was `src/js/package.json src/js/bun.lock ./src/js/`).
    - Stage 2 install: `RUN npm ci --frozen-lockfile` (was `cd src/js && bun install --frozen-lockfile`).
    - `COPY src/ ./src/` (was `src/js/` + `src/py/`).
    - Build: `RUN npm run build && uv sync --frozen --no-editable && uv build --wheel`.
    - Distroless variant gets the same edits.
    Failing test (manual smoke): `docker build -f tools/deploy/docker/run/Dockerfile .` succeeds; `docker run -p 8080:8080 <image>` boots and `curl localhost:8080/` returns HTML.
- [ ] **6.5** **README.md doc-touch** — single-line dev command update (`make run` continues to work; the README's "Frontend Development" section is updated to say "Frontend HMR is automatic when `VITE_DEV_MODE=true`; no separate command required"). Screenshots regen deferred to Ch 5 per PRD.
- [ ] **6.6** Final build smoke: `make clean && make install && make build && make lint && make test` from a fresh checkout. All green. Document elapsed time in Beads notes.

### Phase 7: Tests & patterns (`oracledb-vertexai-4d6.4.7`, rewritten + new `oracledb-vertexai-4d6.4.12` for doc-touch)

- [ ] **7.1** Confirm `htmx_client` fixture in `src/tests/conftest.py` (added Phase 4.10).
- [ ] **7.2** Cumulative test inventory passes:
    - `src/tests/unit/test_base_dir_audit.py` (Phase 1.6)
    - `src/tests/unit/test_repo_layout.py` (Phase 3.6)
    - `src/tests/unit/test_styles_source.py` (Phase 3.3)
    - `src/tests/unit/test_vite_settings_shape.py` (Phase 4.2)
    - `src/tests/unit/test_app_plugins.py` (Phase 4.3)
    - `src/tests/unit/test_csrf_header.py` (Phase 4.4)
    - `src/tests/unit/test_metrics_charts_shape.py` (Phase 5.1a)
    - `src/tests/unit/test_metrics_summary_cards_shape.py` (Phase 5.1d)
    - `src/tests/api/test_static_assets.py` (Phase 2.4 / 3.4)
    - `src/tests/api/test_pages.py` (Phase 4.7, 5.4)
    - `src/tests/api/test_chat_partial.py` (Phase 4.7)
    - `src/tests/api/test_explain_plan.py` (Phase 5.1b)
    - `src/tests/api/test_classify_compare_endpoint.py` (Phase 5.1c)
    - `src/tests/api/test_vector_demo_partial.py` (Phase 5.5)
    - `src/tests/unit/test_cli_surface.py` (Phase 1.8 — replaces the originally-planned grep-based invariant test; architecture-level enforcement).
- [ ] **7.3** Manual browser smoke (Playwright; document outcomes in Beads notes on the doc-touch task):
    - `make install && make build && uv run coffee run`
    - `/` chat: persona switches; send message; partial appears; metrics badges update via OOB.
    - `/explore`: type query → results + EXPLAIN PLAN populate; URL updates with `?q=...`; back button works; charts render (Panels 4+5); Panel 3 cards refresh every 10s.
    - HMR: edit `pages/chat.html.j2` → page hot-swaps without full reload.
    - `browser_console_messages` snapshot: zero errors. Screenshot stashed in Beads notes.
- [ ] **7.4** **Doc-touch** (`oracledb-vertexai-4d6.4.12`): append to `.agents/patterns.md`:
    - HTMX page-vs-partial branching (`if request.htmx` + `HTMXTemplate(...)`).
    - `hx-ext="litestar"` + `ls-for`/`ls-if` for static JSON-to-DOM mapping (when not interactive).
    - Alpine + ApexCharts for chart panels.
    - EXPLAIN PLAN viewer pattern (two driver calls; bind variable risk).
    - `PushUrl` for shareable search URLs.
    - `OOB` swap idiom for multi-region updates from one POST.
    - CSRF: `<meta name="csrf-token">` + `registerHtmxExtension()` ⇒ `X-CSRFToken` header.
    - Tailwind v4 `@source` directive for Jinja template scanning.
    - **CLI split** — `coffee` for production app commands (run / bulk-embed / clear-cache / model-info / load-fixtures / export-fixtures), `manage.py` for infra + db + assets. Mirrors `dma/accelerator`'s `dma`-vs-`manage.py` split. Hand-rolled `rich_click` group; do **not** call `litestar_group()` from `coffee`. Protected by `test_cli_surface.py`.

---

## Out of Scope (defer to other chapters)

- Knowledge-base / guide consolidation — Ch 5.
- README quickstart rewrite (full pass) — Ch 5. Ch 4's doc-touch limited to the dev-command sentence.
- CLI command pruning (`bulk-embed`, `export-fixtures`) — Ch 5.
- Streaming chat (PRD: "not yet canonical").
- Authentication / multi-user (PRD out-of-scope).
- Inertia.js path (PRD: HTMX is the chosen story).
- Heatmap panel (dropped per user direction).
- TypeScript SDK regeneration (`generate_sdk=False`; no React consumer).
- `hx-boost="true"` on nav links (decision: full reload, two-page app).
- `htmx-ext-response-targets` (decision: server-side `Retarget` is sufficient).
- Cross-page `TriggerEvent` orchestration (chat triggering explore-page metrics refresh) — only meaningful with multiple tabs open; not in scope for v1.
