# Knowledge Entry: documentation-setup_20260429

- **Flow ID:** `documentation-setup_20260429`
- **Description:** Ch 6 — Sphinx Learning App: front-door, walkthrough, three concept pages, internals appendix, autodoc API reference, and GitHub Pages deployment.
- **Completed:** 2026-05-02
- **Beads Epic:** `oracledb-vertexai-4d6.6`
- **Topics:** docs, sphinx, sphinx-immaterial, mermaid, autodoc, github-pages, learning-portal

<!-- truth: start -->
## Summary

The repo ships a Sphinx-based learning portal under `docs/` rendered by
`sphinx-immaterial`, published to GitHub Pages on push to `main`. The site is
narrative-first: a hero front door, an end-to-end walkthrough of one chat
message, three concept deep-dives (vectors in Oracle, RAG, Google ADK), and a
small reference appendix that includes a deliberately narrow autodoc API
section. Code embeds are anchored in the source via `# docs:start-<name>` /
`# docs:end-<name>` markers so refactors do not silently break docs. Every
embed has a one-or-two-sentence framing paragraph above it that names the
file and its role.

## Patterns Elevated (see patterns.md for full list)

- Three-tier IA locked: `index.md` + `tour.md` (front), `concepts/{vector-search,rag,agent-flow}.md` (3 pages — not 2, not 4), `reference/{quickstart,cli,api,internals,developers}.md`.
- `sphinx-immaterial` theme, NOT `shibuya`. Custom admonitions `tour-stop`, `oracle-internals`, `agent-detail` defined in `conf.py`.
- `literalinclude` with `docs:start-*` anchor pairs in source — never inline copy-paste. Each block is preceded by a framing sentence.
- Autodoc scope is narrow: `ADKRunner`, `CacheService`, `MetricsService`, `ProductService`, and the three `domain/*/schemas` packages. Skip CLI, settings, plugin wiring, IoC providers.
- `autodoc_mock_imports` MUST NOT include `oracledb`, `vertexai`, `google.adk`, `google.cloud`, or `google.genai` — they are hard deps and the mock breaks sqlspec's import-time `oracledb.__version__` lookup.
- Build with `sphinx-build -W --keep-going` from day one. `make docs` is the local target; `.github/workflows/docs.yml` deploys to GitHub Pages on push to main via `actions/deploy-pages@v4`.

## Key Files

- `docs/conf.py` — sphinx-immaterial config, autodoc options, MyST extensions, custom admonitions, mermaid backend.
- `docs/index.md` — hero front door with three pill cards and a hero mermaid; toctree captions for Concepts and Reference.
- `docs/tour.md` — single end-to-end walkthrough (4 steps, 4 mermaid diagrams).
- `docs/concepts/{vector-search,rag,agent-flow}.md` — three concept deep-dives.
- `docs/reference/api.md` — autodoc directives for the locked-scope classes.
- `docs/reference/internals.md` — HNSW neighbor graph, parallel-vs-sequential gantt, dashboard-metric mapping.
- `docs/_static/{custom.css,cymbal-coffee-logo.svg,cymbal-coffee-cup.svg}` — hero pills, Material card hover lift, brand assets.
- `.github/workflows/docs.yml` — Pages CI: build with `-W`, upload artifact, deploy.
- `Makefile` — `docs` (build), `docs-serve` (sphinx-autobuild on :8002), `docs-clean`.

## Sphinx Configuration Notes

- Theme palette: green primary + amber accent; light/dark toggle.
- `html_logo` = wordmark SVG (white fill matching white topbar text).
- `html_title = ""` — suppresses redundant theme text next to the logo.
- Right-hand "on this page" sidebar hidden via `custom.css` (`.md-sidebar--secondary { display: none; }`) — pages are short enough that lost width matters more than in-page jump links.
- Mermaid via `sphinxcontrib.mermaid`, `mermaid_version = "11.4.1"` for the CDN ESM bundle.
<!-- truth: end -->
