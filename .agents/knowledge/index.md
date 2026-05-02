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
| [htmx-vite-frontend_20260429](htmx-vite-frontend_20260429.md) | 2026-04-29 | htmx, vite, tailwind, litestar, jinja, frontend, cli, oracle, explain-plan, vanilla-js, vector-calculator | Ch 4: source-tree flatten + CLI restructure + HTMX/Vite frontend rebuild — delete React, build /explore page with EXPLAIN PLAN viewer and vector calculator |
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
