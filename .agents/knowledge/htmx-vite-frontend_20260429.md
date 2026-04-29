# Knowledge Entry: htmx-vite-frontend_20260429

- **Flow ID:** `htmx-vite-frontend_20260429`
- **Description:** Ch 4 — Source-tree flatten + CLI restructure + HTMX/Vite frontend rebuild (delete React, build /explore page with EXPLAIN PLAN viewer)
- **Completed:** 2026-04-29
- **Beads Epic:** `oracledb-vertexai-4d6.4`
- **Topics:** htmx, vite, alpine, tailwind, litestar, jinja, frontend, cli, oracle, explain-plan

<!-- truth: start -->
## Summary

Ch 4 deleted the React + TanStack Router + Bun + Biome frontend wholesale and rebuilt it on HTMX 2.0.10 + Tailwind v4 + Alpine.js + ApexCharts via `litestar-vite` mode=`template` + `litestar.plugins.htmx`. In the same chapter, the source tree was flattened (`src/py/{app,tests}` → `src/{app,tests}`, `src/js/` deleted entirely, `vite.config.ts` + `package.json` move to repo root). The `coffee` CLI was restructured: it became a hand-rolled `rich_click` group exposing only production-app commands (run/bulk-embed/clear-cache/model-info/load-fixtures/export-fixtures); migrations + assets + infra moved exclusively to `manage.py`. The chapter delivered two server-rendered pages — chat (feature parity with the deleted React) and explore (vector search, EXPLAIN PLAN viewer, metrics summary, latency time-series).

## Patterns Elevated (see patterns.md for full list)

- HTMX page-vs-partial branching on `request.htmx` (one endpoint, two response shapes).
- `HTMXTemplate(push_url=, re_target=, re_swap=, trigger_event=)` writes headers at construction time — no setter API.
- `hx-ext="litestar"` + `<template ls-for>` / `<template ls-if>` for static JSON-to-DOM mapping when interactivity isn't required.
- Alpine + ApexCharts factories (`x-data`/`x-init`/`x-show`/`x-cloak`/`x-ref`) inline at the bottom of page templates; never imperative `innerHTML`.
- Oracle EXPLAIN PLAN viewer: two driver calls (`EXPLAIN PLAN FOR ...` + `DBMS_XPLAN.DISPLAY()`); both must be named SQL.
- `litestar-vite` mode=`template` + `HTMXPlugin()` (built-in to Litestar 2.x; no separate PyPI dep).
- `vite.config.ts` `publicDir` is project-root-relative — must be set explicitly to `src/resources/public` for brand assets to ship.
- CLI split: `coffee` (rich_click, no `litestar_group()`) for app commands; `manage.py` for infra/db/assets. Mirrors `dma/accelerator`'s `dma` vs `manage.py`.
- Engineering conventions: typed Structs at every API boundary, direct schema imports, `from_json` not `json.loads`, `schema_type=` on every sqlspec select, `COALESCE` in SQL for null-safe aggregates, inline single-use locals.

## Key Files

- `src/app/domain/web/controllers/_pages.py` — chat + explore page routes
- `src/app/domain/web/templates/{base,_nav}.html.j2` — Tailwind-themed shell with `hx-ext="litestar"`
- `src/app/domain/web/templates/pages/chat.html.j2` — persona switcher + HTMX partial swap
- `src/app/domain/web/templates/pages/explore.html.j2` — 5 panels with mixed HTMX partials, `ls-for` blocks, and inline Alpine factories
- `src/app/domain/web/templates/partials/{search_result,search_result_list,plan_lines,_chat_response,_flash,_metrics_badges,message,chat_error}.html.j2`
- `src/app/domain/products/controllers/_vector.py` — `vector_search_demo` (HTMX/JSON branching) + `explain_plan` endpoint
- `src/app/domain/products/services/services.py` — `OracleVectorSearchService.explain_search_plan` (two driver calls)
- `src/app/domain/system/controllers/_metrics.py` — typed `MetricsSummary` / `MetricsTimeSeries`
- `src/app/domain/products/schemas/_products.py` — `VectorDemo`, `VectorDemoMatch`, `ExplainPlan` Structs
- `src/app/domain/system/schemas/_metrics.py` — `MetricsSummary{cards}`, `MetricsTimeSeries{labels,series}`, `PerformanceStats`, `CacheStats`
- `src/app/db/sql/system.sql` — `metrics-time-series` + `explain-plan-display` named queries (with `COALESCE`)
- `src/app/db/sql/products.sql` — `explain-plan-vector-search` named query
- `src/resources/{main.js,styles.css,public/}` — frontend entry + brand assets
- `vite.config.ts` + `package.json` + `tsconfig.json` at repo root
- `manage.py` (root) — rich_click group: init/install/doctor/infra/database/assets
- `src/app/cli/main.py` — coffee rich_click group (no `litestar_group()`)
- `src/tests/conftest.py` — `htmx_client` fixture
- `src/tests/unit/test_cli_surface.py` — architectural enforcement of CLI split (8 tests including `test_coffee_help_does_not_construct_db_config`)
- `src/tests/unit/test_repo_layout_invariants.py` — 32 invariants locking pyproject/Makefile/.gitignore/Dockerfile contracts
- `tools/deploy/docker/run/Dockerfile{,.distroless}` — npm ci against root package.json, COPY src/, CMD ["coffee", "run", ...]

## Learnings (verbatim from spec.md learnings.md, organized by phase)

### Phase 1 (source-tree flatten + CLI restructure)
- `src/py/` flatten broke 80+ Python files importing `app.config` etc. — `manage.py` had to bump `sys.path` for `src/`. Locked via `test_manage_py_help_runs_without_error`.
- `litestar_group()` fingerprints leak into `coffee --help`: it brought in `info`, `routes`, `schema`, `sessions` which we don't want for a production CLI. Hand-rolled `rich_click` group fixes it. Architectural assertion lives in `test_coffee_help_does_not_construct_db_config`.

### Phase 2 (delete React)
- Brand assets at `src/js/public/` had to be rescued before `git rm -rf src/js/`. They moved to `src/resources/public/`. Phase 6 surfaced that vite.config.ts also needed `publicDir: "src/resources/public"` for them to ship.

### Phase 3 (frontend scaffold)
- Tailwind v4 needs `@source "../templates"` directive in `styles.css` to scan `.html.j2` for utilities. Without it, the bundle is silently incomplete.
- Vite bundle dir is co-located with the web domain peer-package (`src/app/domain/web/static/dist/`) so templates and assets stay together. The path appears in `vite.config.ts`, `ViteConfig.paths.bundle_dir`, and `.gitignore` — they must agree.

### Phase 4 (TemplateConfig + HTMXPlugin + FlashPlugin)
- `Litestar` config keyword is `template_config=`, not `templates=`.
- `HTMXPlugin` is built into `litestar.plugins.htmx`, not a separate PyPI package — adding `litestar-htmx` to `dependencies` is wrong.
- `flash(request, msg)` Jinja global is `get_flashes()`, not `get_flashed_messages()`. Each call pops messages — render-once semantics.
- Litestar's `File(...)` accepts `media_type=`, not `content_type=`. Without it, `.ico` serves as `application/octet-stream`.
- `controllers = [...]` in domain `__init__.py` triggers Ruff `RUF067` — drop the assignment; `DomainPlugin` auto-discovers via `find_controllers_in_module()`.

### Phase 5 (explore page + 3 endpoints + 6 engineering conventions)
- `HTMXTemplate(push_url=...)` writes `HX-Push-Url` header at construction time; there's no `.push_url` attribute. Tests assert on `response.headers["HX-Push-Url"]`.
- `MetricsChart` / `scatter_data` / `breakdown_data` were unused holdovers from a React-dashboard era — replaced with Phase 5 typed Structs.
- `test_named_sql_loading::test_no_inline_sql_strings_in_domain_services` is a real invariant — extracted EXPLAIN PLAN SQL into named queries (`explain-plan-vector-search` + `explain-plan-display`).
- 404 body is empty under `raise_server_exceptions=False` — tests assert only `status_code == 404`; the detail string only renders in real browser responses.
- Alpine `x-show` toggles beat imperative DOM mutation: same UX, no XSS surface.
- Mid-phase user direction crystallized into 6 engineering conventions now spec'd in spec.md's Engineering Conventions section.

### Phase 6+7 (toolchain finalize + browser smoke)
- `vite.config.ts` `publicDir` is project-root-relative, not resourceDir-relative — must be set explicitly even when `resourceDir` is configured. Surfaced when chat-page logo 404'd in Playwright smoke.
- Granian `coffee run` ignores shell-export `VITE_DEV_MODE` overrides because python-dotenv re-loads `.env` after the shell environment. Settings-loaded env vars take precedence over shell exports.
- Vite dev-mode auto-port-pick can race the `hot` file: plugin writes auto-picked port to `.litestar.json`, vite.config.ts strictPort writes 5173 to `hot`. Templates render one URL, Vite binds the other. Workaround: use prod mode for browser smoke.
- `make build` was Python-only before Phase 6.2 — never rebuilt the frontend bundle. Now chains `manage.py assets build` then `uv build`.
- `make lint` skipped frontend type-checking before Phase 6.2 — now chains `frontend-typecheck` (npx tsc --noEmit) after pyright.
- Dockerfile `CMD` was `app run` — `app` was never a registered console script. Fixed to `coffee run`.
<!-- truth: end -->
