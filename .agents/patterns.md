# Project Patterns

> Consolidated learnings and patterns from all flows.
> This file is the single source of truth for project conventions.

<!-- truth: start -->
## Code Conventions

- **Licensing & Copyright:** Use concise SPDX identifiers at the top of every source file.
  - **Python/Shell/SQL:** Use `# SPDX-FileCopyrightText: 2024 Google LLC` and `# SPDX-License-Identifier: Apache-2.0`.
  - **JS/TS:** Use `// SPDX-FileCopyrightText: 2024 Google LLC` and `// SPDX-License-Identifier: Apache-2.0`.
  - **Mandatory:** Full license blocks are deprecated in favor of SPDX identifiers. All new files MUST include these headers.
- ADK runner lives at `app/domain/chat/services/adk.py` and is wired as an APP-scoped Dishka provide.
- Keep migration README updated with concrete baseline tables and type usage after schema modernization.
- Beads is authoritative for task status; markdown artifacts should mirror Beads via sync after status changes.

## Architecture Patterns

- **Litestar App Composition:** Keep app setup thin. Compose routes, plugins, dependencies, and middleware strictly from domain modules. Use async I/O universally.
- **Dishka DI:** Prefer centralized Dishka setup (`setup_dishka`) with `DomainPlugin(use_dishka_router=True)` and handler-level `Inject[T]` over route-level `@inject`.
- Dishka router integration (`Inject[ADKRunner]` on handlers, no route decorators) keeps DI explicit and framework-native.
- **SQLSpec Data Access:**
  - Always use typed adapters and context managers (`async with config.create_driver() as db:`).
  - Use `schema_type` to map typed results instead of raw dictionaries.
  - Prefer the query builder (`sql.select().to_statement()`) or `SQLFileLoader` over raw string concatenation.

## Gotchas & Warnings

- `make test` used `.ONESHELL` without `set -e`, which allowed false-green runs when pytest failed; enforce fail-fast in the test target.
- Integration tests using SQLSpec Oracle pool under `pytest-anyio` + xdist can hit event-loop binding issues; reset/close `db.pool_instance` in function-scoped fixtures to avoid cross-loop pool reuse.
- Cache integration tests should use unique keys per test run to remain deterministic under parallel workers.
- Fixture load ordering should include `store` before dependent semantic tables to keep imports deterministic.
- Product reads should normalize Oracle boolean nullability (`NVL(in_stock, TRUE)`) for stable typed API responses.
- **`OracleAsyncConfig` keyword-arg rename (sqlspec ≥ 0.46):** the constructor accepts `connection_config=` (was `pool_config=`). The old name is silently absorbed by `**kwargs` — credentials never reach the pool and every CLI fails with `DPY-4001 "no credentials specified"`. Audit any new sqlspec adapter wiring for this when bumping sqlspec.
- **Oracle 23ai vector pool / HNSW INMEMORY indexes:** any `CREATE VECTOR INDEX … ORGANIZATION INMEMORY NEIGHBOR GRAPH` requires a non-zero `vector_memory_size` allocated *before* the DDL runs (`ORA-51962` otherwise). `vector_memory_size` is a STATIC parameter — the change is SPFILE-only and only takes effect after a restart. The dev container handles this in `tools/oracle/on_init/00_configure_vector_memory.sql`; for shared/Autonomous DBs use `tools/oracle/configure_vector_memory.sql` as SYSDBA.
- **Oracle Database Free Edition memory cap:** Free locks `sga_max_size` / `sga_target` (~1.5 GB SGA + 0.5 GB PGA = 2 GB hard ceiling) and rejects bumps with `ORA-56752`. The vector pool must therefore fit *inside* the existing SGA — 512 MB is the project default and gives ~25× headroom for the demo dataset (~1100 vectors at 3072 dims). Standard/Enterprise/Autonomous have no such cap.
- **`V$SGAINFO` row name for the vector pool:** the row is reported as `Vector Memory Area`, not `Vector Memory`. Verification SQL must match either label; the on_startup script in this repo does.
- **Embedding dim ↔ DDL coupling:** `VECTOR(N, FLOAT32)` columns and the embedding model output are co-versioned. When changing dims (e.g. `text-embedding-004` 768 → `gemini-embedding-001` 3072), modify the baseline DDL, set `output_dimensionality=N` on `EmbedContentConfig`, and regenerate fixtures — there is no implicit truncation/padding at the DB layer.
- **Stale fixture vectors against a new schema:** the fixture loader skips vector payloads whose length doesn't match the `VECTOR(N)` column with a one-shot warning per column. Stale `*.json.gz` files therefore load against an updated dim; `bulk-embed` then fills in fresh embeddings via Vertex AI.

## HTMX + Vite Frontend Patterns (Ch 4)

- **Page-vs-partial branching on `request.htmx`:** controllers that serve both a full page and an HTMX swap target take `request: HTMXRequest` and return `Response[Struct] | HTMXTemplate`. On `request.htmx` return `HTMXTemplate(template_name="partials/...", context=..., push_url=f"/explore?q={quote(query)}")`; otherwise return `Response(content=Struct(...))`. The same endpoint serves JSON to JS clients and HTML to HTMX clients without duplicating logic.
- **`HTMXTemplate(push_url=...)` writes the `HX-Push-Url` header at construction time** — there is no `.push_url` attribute on the response. Tests assert via `response.headers["HX-Push-Url"]`. Same pattern for `re_target` / `re_swap` / `trigger_event`.
- **`hx-ext="litestar"` + `<template ls-for>` / `<template ls-if>` for static JSON-to-DOM mapping:** when a panel just needs to render a JSON array as HTML cards (no interactive state), prefer client-side `ls-*` templating over server-rendered partials. Hosts the JSON contract on the API endpoint; frontend stays dumb. Use server partials only when the rendering needs auth-sensitive fields, complex conditionals, or heavy formatting.
- **Alpine + ApexCharts for chart panels:** charts live in `x-data` factories (e.g. `latencyChart()` / `classifyCompareChart()`) inline at the bottom of the page template. The factory `fetch`-es its endpoint, sets `missing = true` on a non-OK response (so `x-show="missing"` toggles a hint), and instantiates `new ApexCharts(this.$refs.<host>, opts).render()` in its `init()`. Never use `innerHTML` to inject error/missing UI — bind via Alpine `x-show` for the same UX without an XSS surface.
- **EXPLAIN PLAN viewer (two driver calls):** Oracle EXPLAIN PLAN requires two separate sqlspec `driver` calls — `db_manager.get_sql("explain-plan-vector-search")` (the `EXPLAIN PLAN FOR ...` DDL) followed by `db_manager.get_sql("explain-plan-display")` (`SELECT plan_table_output FROM TABLE(DBMS_XPLAN.DISPLAY())`). Both queries must be named SQL — `test_named_sql_loading.py::test_no_inline_sql_strings_in_domain_services` rejects inline SQL in service methods. **Bind-variable risk:** `EXPLAIN PLAN` does not actually bind `:query_vector` for shape inspection; if you change the bind types, EXPLAIN may not reflect the production cost.
- **OOB swap idiom for multi-region updates from one POST:** when a single endpoint updates multiple parts of the page (e.g. chat append + metrics badge refresh), return a partial whose root contains `<div hx-swap-oob="true" id="metrics-badges">...` blocks alongside the primary swap target. The OOB blocks land in their respective host elements; the primary content lands in `hx-target`.
- **CSRF for HTMX:** include `<meta name="csrf-token" content="{{ request.scope['csrf_token'] }}">` in `base.html.j2`. Wire HTMX to forward it via `htmx:configRequest` or use `registerHtmxExtension()` to populate the `X-CSRFToken` header on every non-GET request. GET-only endpoints (charts, EXPLAIN PLAN) skip the token plumbing.
- **Tailwind v4 `@source` directive for Jinja template scanning:** Tailwind v4 needs `@source "../templates"` in your CSS entry point so the JIT compiler scans `.html.j2` files for utility classes. Without it, Tailwind silently emits a CSS bundle missing classes used by templates. CI smoke greps for at least 3 known utility classes in the built bundle.
- **`vite.config.ts` `publicDir` is project-root-relative, not resourceDir-relative:** Vite copies `<projectRoot>/<publicDir>` wholesale into `bundleDir` at build time. Setting `resourceDir: "src/resources"` does **not** make Vite copy `src/resources/public/` into the bundle dir — you must explicitly set `publicDir: "src/resources/public"` in `vite.config.ts`. Without it, brand assets silently fail to ship and pages 404 on logos/favicons.
- **`HTMXPlugin()` is built into `litestar.plugins.htmx` (Litestar 2.x):** there is no separate `litestar-htmx` PyPI package to install. Adding it as a direct dep is wrong. The `HTMXRequest` / `HTMXTemplate` / `TriggerEvent` / `PushUrl` symbols all import from `litestar.plugins.htmx`.
- **`litestar-vite` mode='template' for HTMX apps (not 'spa'):** `ViteConfig(mode="template", dev_mode=settings.vite.DEV_MODE, ...)` pairs with `TemplateConfig` and `HTMXPlugin()`. Vite bundles JS/CSS sprinkles; Litestar returns Jinja partials enriched with `hx-*` attributes. Bundle dir co-locates with the web domain peer-package (`src/app/domain/web/static/dist/`) so templates and bundle output stay together.
- **CLI split — `coffee` vs `manage.py`:** `coffee` exposes only production-app commands (`run` / `bulk-embed` / `clear-cache` / `model-info` / `load-fixtures` / `export-fixtures`) via a hand-rolled `rich_click` group. **Do not call `litestar_group()` from `coffee`** — that drags in litestar-builtin `info` / `routes` / `schema` / `sessions` AND materializes `app.config.db` even on `--help`. Migrations + assets + infra all live exclusively on `manage.py` (`database upgrade`, `assets build`, `infra start-local-container`). Mirrors `dma/accelerator`'s `dma`-vs-`manage.py` split.

## Engineering Conventions (Ch 4 mid-phase corrections)

These six rules surfaced during Phase 5 review and now apply to every new endpoint plus any pre-existing untyped surface a phase touches. Spec'd in `htmx-vite-frontend_20260429/spec.md`'s Engineering Conventions section.

1. **Typed msgspec Structs at every public API boundary** — never `dict[str, Any]`. Same for service methods that feed those handlers; a typed return beats handing the caller a dict to subscript.
2. **Direct schema imports** — `from app.domain.system.schemas import MetricsSummary`, never `from app.domain.system import schemas` followed by `schemas.MetricsSummary`. The namespace-prefix style is banned for new code.
3. **`from_json` / `to_json` from `app.utils.serialization`** — re-exports of `sqlspec.utils.serializers`, mirroring `dma/accelerator/src/py/dma/utils/serialization.py`. `json.loads` / `json.dumps` is banned for new code; use the shared utils so the serialization stack is uniform.
4. **`schema_type=` on every sqlspec `select` / `select_one_or_none`** — rows map directly into Structs at the driver layer, not via Python casting. Pair an internal `*Row` Struct with a public Struct when row shape and surface API differ (e.g. `CacheStatsRow` → `CacheStats`).
5. **Push aggregation null-handling to SQL via `COALESCE`** — `COALESCE(AVG(...), 0)` / `COALESCE(COUNT(*), 0)` so rows arrive as concrete numbers. No `value or 0` Python null-handling on aggregate output.
6. **Inline single-use locals** — `return await svc.x(self.validate_message(query))`, not a temporary. Bookkeeping locals that span branches (e.g. a `detailed_timings` dict in `vector_search_demo`) are fine; the rule is about pointless intermediate names.

## Testing Patterns

- Maintain both lightweight chat UI and richer dashboard UI tests to keep quick-path and analytics-path regressions visible.
- UI verification is safer when tests assert rendered contextual fields (products/stores/results), not only final answer text.
- **HTMX-flavored API tests use the `htmx_client` fixture** in `src/tests/conftest.py` — it pre-sets `HX-Request: true` on the `AsyncTestClient` so partial-branch handlers get exercised without per-test header setup.
- **Test modules that hit `Inject[Service]` need autouse mocks for the whole DI chain** — Litestar resolves all handler parameters before the body runs, so even an early-return validation path triggers full Dishka construction. Monkey-patch `Service.__init__` to a no-op AND `Service.method` to `AsyncMock` because Dishka builds the instance, not just calls the method.
- **404 body is empty under `raise_server_exceptions=False`** — assert only `status_code == 404`; the helpful detail string is consumed by the after-exception hook before serialization. Real-browser responses still see the hint via the rendered template.

## Context for AI Assistants

- Persona-aware system prompt composition (`BASE_SYSTEM_INSTRUCTION` + persona overlay) keeps one static ADK agent reusable while preserving behavioral flexibility.
- Preserve generated API/types artifacts and route scaffolding early (`litestar assets generate-types`) to reduce frontend/backend contract drift.
- Modern Oracle baseline is already captured in `0001_cymball_coffee_products.sql` with `BOOLEAN`, `JSON`, and `VECTOR` columns plus `store` table parity.
- Maintaining `.agents/knowledge/index.md` as a compact registry makes cross-flow recall faster than searching raw specs.
- During migration from legacy guides, preserving concise gotchas in `patterns.md` yields better downstream implementation quality.
<!-- truth: end -->
