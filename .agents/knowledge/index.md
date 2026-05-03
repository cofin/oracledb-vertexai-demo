# Knowledge Base

> Current-state learnings from completed flows.
> For actionable patterns, see [patterns.md](../patterns.md).
> Do not rely on `.agents/archive/`; durable content must be synthesized here.

## Cohesive Guide

- [Project Knowledge Guide](project-guide.md) - current architecture, data,
  AI, store/location/inventory/maps plans, settings cleanup, frontend, testing,
  operations, and Flow-memory policy synthesized from completed work.

## Entries

| Flow ID | Completed | Topics | Summary |
|---------|-----------|--------|---------|
| [cymbal-coffee-reset_20260429](cymbal-coffee-reset_20260429.md) | 2026-05-02 | modernization, adk2, oracle-26ai, hnsw, sqlspec, dishka, vector-search, intent-classification, frontend, cli, restructure | Master PRD: nine-chapter modernization onto ADK 2.0 + Oracle 26ai HNSW INMEMORY + sqlspec 0.46 + HTMX/Vite + 3-provider Dishka. Two corrective PRDs included. |
| [htmx-vite-frontend_20260429](htmx-vite-frontend_20260429.md) | 2026-04-29 | htmx, vite, tailwind, litestar, jinja, frontend, cli, oracle, explain-plan, vanilla-js, vector-calculator | Ch 4: source-tree flatten + CLI restructure + HTMX/Vite frontend rebuild — delete React, build /explore page with EXPLAIN PLAN viewer and vector calculator |
| [vector-calculator_20260429](vector-calculator_20260429.md) | 2026-05-02 | vector, calculator, oracle-26ai, explore, vanilla-vite, frontend-only | Ch 7: client-only Oracle vector storage estimator on the Explore page (rows × dimensions × format × index) |
| [ui-regression-recovery_20260501](ui-regression-recovery_20260501.md) | 2026-05-01 | htmx, ui, telemetry, apexcharts, sql-phases, classify-compare-removal, regression | Corrective PRD: shared shell + structured `sql_phases` telemetry + ApexCharts dashboard restoration + classify-compare descope |
| [test-suite-reorganization_20260501](test-suite-reorganization_20260501.md) | 2026-05-01 | testing, pytest, oracle-fixtures, layout-guard, ruff | Corrective PRD: strict unit/integration module-path layout, layout guard, shared per-worker Oracle fixtures |
| [pyapp-packaging_20260429](pyapp-packaging_20260429.md) | 2026-05-02 | pyapp, packaging, onefile, release, github-actions, docker, distroless, glibc, cargo-zigbuild, multi-arch | PyApp onefile (Bundle-Patch-Compile) + dual-arch GitHub Releases (linux x86_64 + aarch64) + distroless container wrapping the verified binary |
| [documentation-setup_20260429](documentation-setup_20260429.md) | 2026-05-02 | docs, sphinx, sphinx-immaterial, mermaid, autodoc, github-pages, learning-portal | Ch 6: Sphinx learning portal — three-tier IA, locked autodoc scope, literalinclude anchor convention, GitHub Pages CI |

## Guides

- [ADK Agent Patterns](guides/adk-agent-patterns.md) - current ADK 2 runner
  process flow, Litestar session bridge, Product RAG grounding, SSE streaming,
  response cache, display history, and clear-chat behavior.
- [Architecture](guides/architecture.md) - package boundaries and service
  ownership.
- [Oracle Vector Search](guides/oracle-vector-search.md) - vector SQL and
  Oracle search behavior.

## Topic Index

<!-- Topics are added automatically during flow archival -->

- **htmx**: htmx-vite-frontend_20260429
- **vite**: htmx-vite-frontend_20260429
- **tailwind**: htmx-vite-frontend_20260429
- **litestar**: htmx-vite-frontend_20260429
- **jinja**: htmx-vite-frontend_20260429
- **frontend**: htmx-vite-frontend_20260429
- **cli**: htmx-vite-frontend_20260429
- **oracle**: htmx-vite-frontend_20260429
- **explain-plan**: htmx-vite-frontend_20260429
- **vanilla-js**: htmx-vite-frontend_20260429
- **vector-calculator**: htmx-vite-frontend_20260429
- **adk**: guides/adk-agent-patterns.md
- **runner**: guides/adk-agent-patterns.md
- **chat**: guides/adk-agent-patterns.md
- **session**: guides/adk-agent-patterns.md
- **store-location**: project-guide.md
- **inventory**: project-guide.md
- **maps**: project-guide.md
- **settings**: project-guide.md
- **configuration**: project-guide.md
- **pyapp**: pyapp-packaging_20260429
- **packaging**: pyapp-packaging_20260429
- **onefile**: pyapp-packaging_20260429
- **release**: pyapp-packaging_20260429
- **github-actions**: pyapp-packaging_20260429, documentation-setup_20260429
- **docker**: pyapp-packaging_20260429
- **distroless**: pyapp-packaging_20260429
- **glibc**: pyapp-packaging_20260429
- **cargo-zigbuild**: pyapp-packaging_20260429
- **multi-arch**: pyapp-packaging_20260429
- **docs**: documentation-setup_20260429
- **sphinx**: documentation-setup_20260429
- **sphinx-immaterial**: documentation-setup_20260429
- **mermaid**: documentation-setup_20260429
- **autodoc**: documentation-setup_20260429
- **github-pages**: documentation-setup_20260429
- **learning-portal**: documentation-setup_20260429
- **modernization**: cymbal-coffee-reset_20260429
- **adk2**: cymbal-coffee-reset_20260429
- **oracle-26ai**: cymbal-coffee-reset_20260429, vector-calculator_20260429
- **hnsw**: cymbal-coffee-reset_20260429
- **sqlspec**: cymbal-coffee-reset_20260429
- **dishka**: cymbal-coffee-reset_20260429
- **vector-search**: cymbal-coffee-reset_20260429
- **intent-classification**: cymbal-coffee-reset_20260429
- **restructure**: cymbal-coffee-reset_20260429
- **calculator**: vector-calculator_20260429
- **explore**: vector-calculator_20260429
- **vanilla-vite**: vector-calculator_20260429
- **frontend-only**: vector-calculator_20260429
- **ui**: ui-regression-recovery_20260501
- **telemetry**: ui-regression-recovery_20260501
- **apexcharts**: ui-regression-recovery_20260501
- **sql-phases**: ui-regression-recovery_20260501
- **classify-compare-removal**: ui-regression-recovery_20260501
- **regression**: ui-regression-recovery_20260501
- **testing**: test-suite-reorganization_20260501
- **pytest**: test-suite-reorganization_20260501
- **oracle-fixtures**: test-suite-reorganization_20260501
- **layout-guard**: test-suite-reorganization_20260501
- **ruff**: test-suite-reorganization_20260501
