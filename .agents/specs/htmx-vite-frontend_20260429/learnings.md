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

## Phase 1 (2026-04-29, commits 82c47df + 6488db1)

- **Sub-phase 1A discovered two pre-existing test-framework breaks** that fail on `main` HEAD before the flatten:
    1. `src/tests/integration/conftest.py` — `OracleAsyncConfig has no attribute pool_instance`. sqlspec ≥0.46 dropped the public `pool_instance` attribute. Fix: removed the assignment; `db.close_pool()` alone is sufficient.
    2. `test_vector_search_returns_typed_product_matches_with_price` — `ProductMatch.similarity_score` is NaN. Bootstrap seeds at least one product with a zero-norm embedding; Oracle's `VECTOR_DISTANCE(zero, x, COSINE)` is NaN; the WHERE filter `1 - VECTOR_DISTANCE(...) > 0.5` should reject NaN but at least one row slips through (Oracle's NaN-comparison semantics + `LOB_BY_VALUE` hint?). Worked around by tightening the conftest to truncate-and-load canonical fixtures via `FixtureLoader` (matches accelerator's pattern). This exposed a separate **FP-precision quirk**: cosine similarity of FP32-stored vectors against an FP64 query lands a few ULPs above 1.0 for self-matches → fixed the assertion bound to `[0, 1] ± 1e-6`.
- **Mypy "no attribute" trap** — `from app import config as app_config` doesn't tell mypy to follow the `config` submodule. Fix: `import app.config as app_config` (explicit submodule import). Caught when manage.py was rewritten in 1.5.
- **CLI restructure architectural test** — `test_coffee_help_does_not_construct_db_config` patches `app.config.db` constructor with a sentinel that raises and asserts `coffee --help` exits 0. This is the canary that proves `--help` no longer materializes the SQLSpec config — the whole reason for the rich_click rewrite. Without this test the regression slips back trivially.
- **Help-text parsing for subprocess CLI tests** — rich_click prints box-drawing chars + ANSI codes that defeat naive substring asserts. Added `_command_names_in_help()` helper that strips ANSI + box chars + parses the Commands panel structure. 13 subprocess tests in `test_cli_surface.py` use it.
- **xdist parallel safety for integration tests** — added `pytest_collection_modifyitems` applying `xdist_group(name="oracle_integration")` so all integration tests serialize on the shared Oracle pool. Without this, `-n 2 --dist=loadgroup` produced 6 concurrent-pool errors.
- **`@click.pass_context` type-ignore needed** in `_create_run_command()` — RichContext vs Context type mismatch; mirrors `dma/accelerator/src/py/dma/cli/commands/server.py:24-58` exactly (same `# type: ignore[arg-type]`).

## Phase 2 (2026-04-29, commits 83cb129 + 4a4373c)

- **Architectural pivot mid-phase: `domain/web/` peer-domain pattern** — original spec said put templates at `src/templates/` and the bundle output at `src/app/server/static/dist/`. After comparing with `dma/accelerator/src/py/dma/domain/web/static/web/` (their Vite bundle lives **inside** the Python web domain), pivoted to:
    - `src/resources/` — Vite INPUT (main.js, styles.css, public/) — sibling of `src/app/`, mirrors canonical jinja-htmx upstream
    - `src/app/domain/web/templates/` — Jinja templates (consumed by Litestar `TemplateConfig`)
    - `src/app/domain/web/static/dist/` — Vite OUTPUT (gitignored, `manage.py assets build` writes manifest.json + hashed bundles here)
    - Tailwind `@source` retargets to `../app/domain/web/templates` (relative to `src/resources/styles.css`)
- **litestar-vite has zero opinion on template location** — confirmed by inspecting `~/code/litestar/litestar-vite/litestar_vite/` source: no `template_dir`, no `templates_dir`, no `TemplateConfig` references. Templates are owned entirely by Litestar's `TemplateConfig(directory=Path(...))`. The plugin only registers Jinja globals (`vite()`, `vite_hmr()`, `vite_static()`, `vite_routes()`) into whatever Jinja engine is configured. `{{ vite('src/resources/main.js') }}` resolves via the input path string from `vite.config.ts` — must match exactly.
- **Sessions are already wired sqlspec-style** — `src/app/config.py:60-61` registers `StoreRegistry(stores={"sessions": OracleAsyncStore(config=db)})` + `ServerSideSessionConfig(store="sessions")`. Direct mirror of accelerator's `_StoreRegistry(stores={"sessions": AsyncpgStore(config=dbc)})` (Postgres). FlashPlugin needs only this middleware to function — no new infrastructure for cross-request notifications.
- **FlashPlugin is small + clean** — `litestar.plugins.flash.FlashPlugin(FlashConfig(template_config=...))`. Pushes via `flash(request, "msg", "category")`; renders via `{% for f in get_flashes() %}` Jinja global (pops from session — render-once semantics). Accelerator does NOT use FlashPlugin; we are the first.
- **`git rm -r src/js` does not delete gitignored content** — node_modules + .vite cache + .litestar.json are gitignored, so they remain on disk after `git rm`. Spec verification "ls src/js 2>&1 errors" requires a follow-up `rm -rf src/js`. Documented in this learning so future deletions know to combine both.
- **23 brand assets locked** — `git ls-files src/js/public/` returned exactly 23 (matches spec). `ls -la` showed 24 entries because of the `.` directory entry. The exact filename list is parametrized in `test_brand_assets_layout.py::test_each_brand_asset_present` as belt-and-braces against silent inventory drift.
- **HTMX wrapper template `partials/_chat_response.html.j2`** — composes `partials/message.html.j2` + OOB `partials/_metrics_badges.html.j2` + OOB `partials/_flash.html.j2` so a single `HTMXTemplate` returns three regions in one round-trip. Cleaner than a per-handler triple OOB concatenation; named consistently with the canonical jinja-htmx example's `book_card.html.j2` pattern.
- **`HTMXTemplate` composes other litestar-htmx response objects via kwargs** — `re_target=` → `Retarget`, `re_swap=` → `Reswap`, `push_url=` → `PushUrl`, `trigger_event=` + `after=` → `TriggerEvent`. The standalone classes are still useful for non-template responses (e.g., `Reswap("none")` after a `flash + side-effect` action).
