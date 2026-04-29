# Master PRD: Sphinx Learning App — The Oracle + Vertex AI Curriculum

*PRD ID: `documentation-setup_20260429`*
*Created: 2026-04-29*
*Status: Ready*

---

## North Star

Transform `oracledb-vertexai-demo` from a repository into a **production-grade educational platform**. The documentation should be a "learning app" in itself, providing a narrative-first experience that explains *how* Oracle 23ai Vector Search, Google ADK 2.0, and Vertex AI work together, using rich visualizations and diagrams.

---

## Why now

The "Cymbal Coffee Reset" (Chapters 1–5) modernizes the codebase to ADK 2.0 and Oracle 23ai best practices. While Chapter 5 cleans up the existing markdown guides, it stops short of a professional, integrated documentation site. To be a true "reference app," we need a searchable, structured, and visually compelling portal that developers can use to learn the stack.

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

- **Vector Search Deep Dive**: How HNSW and INMEMORY work in Oracle 23ai. Use `literalinclude` to show the SQL.
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
**Inside the DB.** Visualizing the "Oracle EXPLAIN PLAN" and vector indexing.

- **Diagram 4.1: HNSW Neighbor Graph**:
  - Conceptual visualization of Hierarchical Navigable Small Worlds within the Oracle SGA.
  - Explain the `ORGANIZATION INMEMORY NEIGHBOR GRAPH` layout.
- **Diagram 4.2: EXPLAIN PLAN Walkthrough**:
  - Breakdown of a live execution plan: `VECTOR INDEX RANGE SCAN`, `VECTOR DISTANCE` filter, and base table row fetch from `INMEMORY` storage.
- **Diagram 4.3: Intent Classification Performance**:
  - Visualize the "Parallel vs Sequential" latency delta (showing how classification time is "hidden" behind search time).

### Chapter 5 — API Reference & Final Polish
**The reference.** Automated docs for the core domain.

- Configure `autodoc` to scan `src/app/`.
- Focus on `services`, `controllers`, and `adk` modules.
- Add a "Developer Guide" section (installation, management CLI).
- Final UI polish and navigation optimization.

---

## Tech Stack (Docs)

- **Engine**: Sphinx 8.x
- **Theme**: `shibuya` (Litestar-branded Material theme)
- **Diagrams**: `sphinxcontrib-mermaid`
- **Markup**: `myst-parser` (for Markdown support) + RST
- **API Docs**: `autodoc`, `napoleon`, `sphinx-autodoc-typehints`
- **Deployment**: GitHub Actions + GitHub Pages
- **Environment**: `uv` + `Makefile`

---

## Technical Patterns (from sqlspec)

### 1. Makefile Integration
The `Makefile` will be updated with standard doc targets to simplify local development:
- `make docs`: Clean build of the documentation.
- `make docs-serve`: Hot-reloading local documentation server using `sphinx-autobuild`.
- `make docs-clean`: Remove build artifacts.

### 2. CI/CD Pipeline
A GitHub Actions workflow (`.github/workflows/docs.yml`) will automate the documentation lifecycle:
- Triggered on push to `main`.
- Uses `uv` for dependency management.
- Employs a `tools/build_docs.py` script to handle build artifact movement and `.nojekyll` creation.
- Deploys to GitHub Pages using the official `actions/deploy-pages`.

### 3. Sphinx Configuration (`conf.py`)
- **Theme Customization**: Use the `shibuya` theme with Cymbal Coffee brand overrides (accent colors, logos).
- **Mermaid Support**: High-fidelity diagrams with interactive features enabled.
- **Autodoc Mocking**: Ensure `autodoc_mock_imports` handles optional or complex dependencies (e.g., `oracledb`, `vertex-ai`) to allow CI builds without a full live environment.

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
- **Ch 4** `oracle-internals` — Vector search and execution plan visuals.
- **Ch 5** `api-reference` — Autodoc and final polish.
