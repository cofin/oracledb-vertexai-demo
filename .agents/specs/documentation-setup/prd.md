# Master PRD: Sphinx Learning App — The Oracle + Vertex AI Curriculum

*PRD ID: `documentation-setup_20260429`*
*Created: 2026-04-29*
*Status: Complete — closed in Beads 2026-05-02*
*Last reviewed: 2026-05-02*

---

## Locked Decisions (2026-05-02)

After ultrathink planning pass, the PRD's original "5 sequential chapters of
production content" was re-shaped around a **new-user-first information
architecture**. Beads phase IDs (6.1–6.5) are unchanged; what each phase
*produces* is sharpened.

**Front-door title + tagline (locked 2026-05-02):**

- H1: `Ground Beans to Grounded Answers`
- Hero tagline: `Building Agentic Apps with Google and Oracle.`

The "grounded" wordplay is intentional and load-bearing: coffee grounds on
one side, RAG grounding on the other. The two-line shape (short product
arc + literal site purpose) is preserved across iterations.

**Three-tier information architecture:**

```
docs/
├── index.md              ← Tier 1 front door: hero diagram + 3-line pitch + 2 CTAs
├── tour.md               ← Tier 1 centerpiece: a chat message, end to end
├── concepts/             ← Tier 2: pick a concept, go deep (3 pages, locked)
│   ├── vector-search.md  ← HNSW + 3072-dim + INMEMORY
│   ├── rag.md            ← retrieval → grounding → response
│   └── agent-flow.md     ← parallel intent + tool calling
└── reference/            ← Tier 3: only when needed (autodoc lives here)
    ├── quickstart.md
    ├── cli.md
    ├── api.md            ← autodoc, narrowly scoped
    └── internals.md      ← HNSW internals, perf dashboard, latency timeline
```

**Concept page count:** 3 (vector-search / rag / agent-flow) — not 2 or 4.

**Autodoc scope:** buried under `reference/api.md`, **not** a top-level nav
item. API doc is *not* the focus of this site; it's a learning portal.
Autodoc covers only `ADKRunner`, `CacheService`, `MetricsService`,
`ProductService`, and the `domain/*/schemas` msgspec structs. Skip CLI,
settings, plugin wiring.

**Diagram budget (11 total):**
- 1 hero (front door)
- 4 tour stops (one per step in the end-to-end story)
- 3 concept diagrams (one per concept page)
- 3 internals (HNSW neighbor graph, parallel-vs-sequential latency timeline,
  performance dashboard explainer)
- Every diagram caption completes the sentence "This shows how…"

**Source-stable code embeds:** every `literalinclude` block uses
`# docs:start-<name>` / `# docs:end-<name>` anchor markers in the source so
that refactors don't silently break docs.

**Theme:** `sphinx-immaterial` (final lock 2026-05-02). Earlier Beads-side
drift toward `shibuya` (sqlspec pattern) is reverted. Rationale:
- This site is API-dense *and* learning-dense — Material's feature density
  (sticky TOC, code annotations, light/dark palette toggle, dismissable
  banners, custom admonitions) outperforms minimalist themes for scanning a
  reference app.
- The 3-tier IA (Tour / Concepts / Reference) is exposed via the persistent
  left sidebar (`navigation.expand` + `navigation.sections`) rather than
  `navigation.tabs`. Tabs were tried and dropped — the sidebar reads better
  on smaller viewports and avoids duplicating navigation in two places.
- Custom admonitions (`tour-stop`, `oracle-internals`, `agent-detail`) are
  defined in `conf.py` and used as MyST `:::{tour-stop}` blocks — the tour
  page reads as a labelled walkthrough, not a wall of text.
- Branding: `green` primary + `amber` accent, with custom Cymbal Coffee
  brand assets (`docs/_static/cymbal-coffee-logo.svg` for the wordmark in
  the top bar; `docs/_static/cymbal-coffee-cup.svg` for the favicon).
  `html_title = ""` suppresses redundant theme text next to the wordmark.

**Build discipline:** `make docs` builds with `-W --keep-going` from day 1
(warnings-as-errors). `make docs-serve` runs `sphinx-autobuild` on port 8002.
GH Actions deploys to GitHub Pages.

---

## North Star

Transform `oracledb-vertexai-demo` from a repository into a **production-grade educational platform**. The documentation should be a "learning app" in itself, providing a narrative-first experience that explains *how* Oracle 26ai Vector Search, Google ADK 2.0, and Vertex AI work together, using rich visualizations and diagrams.

---

## Why now

The "Cymbal Coffee Reset" (Chapters 1–5) modernizes the codebase to ADK 2.0 and Oracle 26ai best practices. While Chapter 5 cleans up the existing markdown guides, it stops short of a professional, integrated documentation site. To be a true "reference app," we need a searchable, structured, and visually compelling portal that developers can use to learn the stack.

---

## Key outcomes

- **Sphinx-based Portal**: A modern, responsive site using the `sphinx-immaterial` theme.
- **Narrative-First Curriculum**: Content focuses on concepts (RAG, Vector Search, Agentic Workflows) rather than just API semantics.
- **Rich Visualizations**: Mermaid.js diagrams for ADK 2.0 graphs and Oracle execution plans.
- **Automated API Reference**: Stays in sync with the post-refactor codebase via `autodoc` and `napoleon`.
- **Integrated Search**: Blazing fast search across all learning content.

---

## Roadmap (Sagas / Chapters)

### Chapter 1 — Foundation & Scaffolding
**The structure.** Set up the Sphinx environment and basic configuration.

- Initialize `docs/` with Sphinx.
- Configure `sphinx-immaterial` theme with project branding (Cymbal Coffee colors).
- Enable essential extensions: `autodoc`, `napoleon`, `intersphinx`, `viewcode`, `sphinx_copybutton`, `sphinx_design`.
- Add `docs/build` to `.gitignore`.

### Chapter 2 — Narrative Learning Content
**The curriculum.** Convert and expand the "evergreen guides" from Ch 5 into narrative sections.

- **Vector Search Deep Dive**: How HNSW and INMEMORY work in Oracle 26ai. Use `literalinclude` to show the SQL.
- **RAG & Graph RAG**: Explaining the retrieval-augmented generation flow.
- **Vertex AI Integration**: How embeddings (3072-dim) and chat models are used.
- Move Ch 5 guides (`architecture.md`, `oracle-vector-search.md`, `adk-agent-patterns.md`) into Sphinx content.

### Chapter 3 — Agentic Visualizations
**The agentic flow.** Map the ADK 2.0 graph workflows using Mermaid.

- **Diagram 3.1: ADK 2.0 Workflow Graph**:
  - Visualize the `coffee-assistant` graph: `ClassifyIntent` and `ProductSearch` nodes running in **parallel async fan-out**, converging at a `ResponseGenerator` node.
  - Show the context injection points for the Vertex AI model.
- **Diagram 3.2: Retrieval-Augmented Data Flow**:
  - Map the path: `User Input` → `Embedding Service` → `Oracle HNSW Scan` → `ADK Context` → `Gemini Reasoning` → `Final Response`.
- **Diagram 3.3: Tool Protocol**:
  - Visualize the interaction between the ADK Runner and the `AgentToolsService` (closure-bound tool pattern).

### Chapter 4 — Oracle Internals & Visuals
**Inside the DB.** Visualizing how vector indexing and live performance feel.

- **Diagram 4.1: HNSW Neighbor Graph**:
  - Conceptual visualization of Hierarchical Navigable Small Worlds within the Oracle SGA.
  - Explain the `ORGANIZATION INMEMORY NEIGHBOR GRAPH` layout.
- **Diagram 4.2: Intent Classification Performance**:
  - Visualize the "Parallel vs Sequential" latency delta (showing how classification time is "hidden" behind search time).
- **Diagram 4.3: Performance Dashboard Explainer**:
  - Annotated screenshot of `/explore` showing what each live metric measures and which Oracle/ADK call it maps to.

### Chapter 5 — API Reference & Final Polish
**The reference.** Automated docs for the core domain.

- Configure `autodoc` to scan `src/app/`.
- Focus on `services`, `controllers`, and `adk` modules.
- Add a "Developer Guide" section (installation, management CLI).
- Final UI polish and navigation optimization.

---

## Tech Stack (Docs)

- **Engine**: Sphinx 8.x (pinned `>=8.0,<9`)
- **Theme**: `sphinx-immaterial>=0.13.0` — see Locked Decisions for rationale
- **Theme add-ons**: `sphinx-design` (cards/grids), `sphinx-copybutton`
- **Diagrams**: `sphinxcontrib-mermaid`
- **Markup**: `myst-parser` (Markdown-first) with `attrs_block`,
  `colon_fence`, `deflist`, `linkify`, `tasklist` extensions
- **API Docs**: `autodoc`, `napoleon` (Google docstrings),
  `sphinx-autodoc-typehints`
- **Live reload**: `sphinx-autobuild` on `:8002`, watching `src/`
- **Deployment**: GitHub Actions + GitHub Pages
- **Environment**: `uv` (`dependency-groups.docs`) + `Makefile`
  (`docs`, `docs-serve`, `docs-clean`)

---

## Technical Patterns (from sqlspec)

### 1. Makefile Integration
Standard doc targets are wired in Ch 6.1:
- `make docs`: `sphinx-build -W --keep-going -b html docs docs/_build/html`
- `make docs-serve`: `sphinx-autobuild --port 8002 --watch src docs docs/_build/html`
- `make docs-clean`: `rm -rf docs/_build`

### 2. CI/CD Pipeline
A GitHub Actions workflow (`.github/workflows/docs.yml`) will automate the documentation lifecycle:
- Triggered on push to `main`.
- Uses `uv` for dependency management.
- Employs a `tools/build_docs.py` script to handle build artifact movement and `.nojekyll` creation.
- Deploys to GitHub Pages using the official `actions/deploy-pages`.

### 3. Sphinx Configuration (`conf.py`)
- **Theme**: `sphinx-immaterial` with Cymbal Coffee branding — custom
  `_static/cymbal-coffee-logo.svg` wordmark, `_static/cymbal-coffee-cup.svg`
  favicon, `fontawesome/brands/github` repo icon, `green` primary + `amber`
  accent, light/dark palette toggle, `html_title = ""`.
- **Navigation features**: persistent sidebar via `navigation.expand` +
  `navigation.sections` (no `navigation.tabs` — tried, dropped); `toc.follow`
  + `toc.sticky` for the right-side TOC; `navigation.instant` for SPA-feel
  page transitions.
- **Repo wiring**: `repo_url` points at `cofin/oracledb-vertexai-demo`
  (the live remote), with `edit_uri = "edit/main/docs"`.
- **Diagrams**: `sphinxcontrib.mermaid` is the active mermaid backend;
  `mermaid_version = "11.4.1"` loads the CDN ESM bundle.
- **Code experience**: `content.code.annotate` + `content.code.copy`, plus
  `sphinx_copybutton` for fallback.
- **Custom admonitions**: `tour-stop`, `oracle-internals`, `agent-detail` —
  defined via `sphinx_immaterial_custom_admonitions`; used as MyST
  `:::{tour-stop}` blocks on the tour and concept pages.
- **MyST extensions**: `attrs_block`, `colon_fence`, `deflist`, `fieldlist`,
  `linkify`, `substitution`, `tasklist` so Markdown can express the same
  density as RST.
- **Autodoc mocking**: `autodoc_mock_imports = ["oracledb", "vertexai",
  "google.adk", "google.cloud", "google.genai"]` for CI builds without
  live credentials or Oracle.
- **Custom CSS**: `_static/custom.css` styles the front-door hero (tagline
  font, pill cards, mermaid centering) and adds card hover lift for
  `sphinx-design` grids.

---

## Global Constraints

1. **Learning-First**: Every page must answer "How does this work?" before "What is the API?".
2. **Visual-Rich**: Use Mermaid diagrams for any logic involving more than 2 steps.
3. **Sync with Code**: Use `literalinclude` with markers instead of copy-pasting code snippets.
4. **No Semantic Noise**: Minimize documentation on generic Litestar/SQLSpec boilerplate unless it contributes to the AI/Vector story.
5. **Searchability**: Every major concept (e.g., "HNSW", "3072 dims", "Intent Classification") must be easily findable.
6. **Automated Verification**: Documentation builds MUST pass in CI with warnings-as-errors (`-W` flag).

---

## Out of Scope

- Multi-version documentation support (e.g., `/v1/`, `/v2/`).
- Translation/Localization.
- Manual deployment outside of GitHub Actions.

---

## Acceptance Criteria

- `make docs` builds the site without warnings (`-W` flag).
- `make docs-serve` starts a local server on port 8002.
- GitHub Actions successfully builds and deploys the site to GitHub Pages.
- Every major feature from Chapters 1–4 of the Reset PRD has a corresponding narrative guide.
- The ADK 2.0 runner is fully visualized with Mermaid.
- `autodoc` successfully documents the `ADKRunner` and core services.

---

## Beads master epic

- **Master**: `documentation-setup_20260429`
- **Ch 1** `docs-foundation` — Scaffolding, Makefile, and CI/CD setup.
- **Ch 2** `narrative-content` — Content migration and learning deep-dives.
- **Ch 3** `agentic-visuals` — Mermaid mapping of ADK 2.0.
- **Ch 4** `oracle-internals` — Vector search visuals (no EXPLAIN PLAN
  walkthrough — replaced by performance dashboard explainer).
- **Ch 5** `api-reference` — Autodoc and final polish.

---

## Implementation Status (2026-05-02)

| Phase | Status | Output |
| --- | --- | --- |
| 6.1 Foundation | done | `conf.py`, theme, branding, Makefile, mermaid, custom admonitions, hero front door |
| 6.2 Narrative | done | `tour.md` end-to-end + 3 concept pages + `internals.md` all live; literalincludes anchored with `docs:start-*` markers |
| 6.3 Visuals | done | Hero + 4 tour-stop diagrams + 3 concept diagrams + 3 internals diagrams (HNSW layers, parallel-vs-sequential gantt, dashboard mapping) |
| 6.4 Internals appendix | done | Folded into 6.2 — HNSW, latency timeline, dashboard explainer |
| 6.5 Autodoc + CI | done | `reference/api.md` wired with autodoc for ADKRunner + 3 services + 3 schema packages; `.github/workflows/docs.yml` builds with `-W --keep-going` on push to main and deploys via `actions/deploy-pages@v4` |

### Source-stable code embeds — current anchors

The following `# docs:start-<name>` / `# docs:end-<name>` anchor pairs back
the literalinclude blocks in `tour.md` and the concept pages:

| Anchor | File |
| --- | --- |
| `docs:start-stream-handler` | `src/app/domain/chat/controllers/_chat.py` |
| `docs:start-vertex-embedding` | `src/app/domain/products/services/services.py` |
| `docs:start-search-by-vector` | `src/app/domain/products/services/services.py` |
| `docs:start-vector-search-sql` | `src/app/db/sql/products.sql` |
| `docs:start-hnsw-index` | `src/app/db/migrations/0001_cymball_coffee_products.sql` |
| `docs:start-workflow-fanout` | `src/app/domain/chat/services/workflow.py` |
