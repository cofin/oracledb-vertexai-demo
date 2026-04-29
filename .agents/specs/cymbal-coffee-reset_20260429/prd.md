# Master PRD: Cymbal Coffee Reset — Modern ADK 2.0 + Oracle 23ai Reference

*PRD ID: `cymbal-coffee-reset_20260429`*
*Created: 2026-04-29*

---

## North Star

Make `oracledb-vertexai-demo` the canonical, learn-from-it reference for **Google ADK 2.0 + sqlspec native vectors + Litestar + HTMX**.

The published `litestar:litestar-ai-serving` and `litestar:sqlspec` skill docs **already cite this repo, file-by-file, as the canonical reference app** — but the codebase has drifted from what those docs describe. This PRD closes the gap. Every line of code earns its place; every pattern matches the published skill.

A new contributor should grok the entire app cold in 30 minutes.

---

## Why now

Three concrete drifts created this PRD:

1. **sqlspec is 18 minor versions behind** (0.28.1 → 0.46.x). Native Oracle `VECTOR` type handlers, `OracleAsyncADKStore`, `SQLSpecSessionService`, and `create_filter_dependencies()` all exist now — but the codebase carries hand-rolled `array.array('f', ...)` workarounds and a custom-resolved-DI pattern in ADK tools because they pre-date those features.
2. **Google ADK released 2.0b1** with graph-based `BaseNode`/`Workflow` orchestration, partial resume, parallel tool dispatch, and HITL pause/resume. The current runner uses the 1.x flat-agent pattern.
3. **Vertex AI deprecated `text-embedding-004` on 2026-01-14** and `gemini-2.0-*` chat models are superseded. The repo still references both.

Beyond version churn: the `intent_exemplar` vector lookup was added as a *speedup* but is now the only thing keeping interactive chat fast — the bottleneck is the Vertex AI embedding API call (~100-300ms) for the user query. The embedding call must happen inline before vector search runs. ADK 2.0's parallel tool dispatch + Gemini 2.5 Flash-Lite structured output eliminates this entire round trip from the perceived latency.

---

## Key outcomes

- Codebase matches the published skill docs **exactly** — file paths, function signatures, named SQL keys, provider shape.
- Native Oracle 23ai vector indexing: HNSW + INMEMORY at full `gemini-embedding-001` quality (3072 dims).
- ADK 2.0 graph runner replaces the manual-DI tool wrapping; intent classification runs in parallel with retrieval; perceived intent latency drops to ~0ms.
- React + TanStack frontend deleted; replaced with HTMX + Alpine.js + ApexCharts via `litestar-vite` template mode. **Visual polish bar matches the React version, on a fraction of the code.**
- Knowledge base and docs collapse from 23 timestamped artifacts + 16 guides to `patterns.md` + 3 evergreen guides + a 5-minute-quickstart README.

---

## Roadmap (Sagas / Chapters)

Execution order: **1 → 2 → (3 ‖ 4 in parallel after 2 lands) → 5**

### Chapter 1 — `foundation-bump_20260429`
**The substrate.** Deps + schema + fixtures are tightly coupled, so they ship together.

- Bump `sqlspec` 0.28.1 → 0.46.x; `google-adk` → 2.0b1; `python-oracledb` to current; switch to unified `google-genai` SDK.
- Embedding model → `gemini-embedding-001` @ **3072 dims**; chat → `gemini-2.5-flash`; classification (Ch 3) → `gemini-2.5-flash-lite`.
- Modify `0001_cymball_coffee_products.sql` baseline: `VECTOR(3072, FLOAT32)`; add HNSW `ORGANIZATION INMEMORY NEIGHBOR GRAPH ... WITH TARGET ACCURACY 95 PARAMETERS (TYPE HNSW, NEIGHBORS 40, EFCONSTRUCTION 500)` for `product.embedding` and `intent_exemplar.embedding`; mark `product` table `INMEMORY`.
- Document `vector_memory_size` setup (recommend 4G for the demo) in `tools/oracle/`.
- Regenerate all fixture embeddings with `gemini-embedding-001`, recompress `.json.gz`.
- Delete every `array.array('f', ...)` site — sqlspec's native vector handlers do it now.

### Chapter 2 — `accelerator-restructure_20260429`
**Structural shape.** Mirror `~/code/g/dma/accelerator` — without throwing out Dishka.

- Add `lib/service.py` with `SQLSpecAsyncService` base (`paginate`, `get_or_404`, `exists`, `begin_transaction`) per `sqlspec/references/service-patterns.md`.
- Extract every inline SQL string into `db/sql/*.sql` files; wire `db_manager.load_sql_files()` + access via `db_manager.get_sql("name")`.
- Collapse 4 Dishka providers → 1 `DomainServiceProvider` + 1 `LitestarPersistenceProvider` + APP-singletons (Vertex client, ADKRunner, OracleAsyncADKStore, SQLSpecSessionService).
- Adopt `create_filter_dependencies()` from `sqlspec.extensions.litestar.providers` for list endpoints.
- Update `patterns.md` so it stops lying about the codebase.

### Chapter 3 — `adk2-runner_20260429`
**The agent rebuild.** Rebuild the runner on ADK 2.0 graph workflows; eliminate the slow path.

- Migrate `ADKRunner` to ADK 2.0 `BaseNode`/`Workflow` architecture (single sequential workflow node).
- Delete `request_container_var` + `_resolve_request_container` workaround in tools — use ADK 2.0's native context injection.
- Replace exemplar-lookup intent classification: new `classify_intent` tool that calls `gemini-2.5-flash-lite` with **enum-schema structured output** (`response_mime_type="text/x.enum"`); register as a **parallel async tool** alongside `search_products` so its latency hides behind retrieval.
- Keep `intent_exemplar` table — but as **offline-eval ground truth** + a charted "ground-truth vs live classification" comparison surfaced on the explore page (Ch 4 hooks here).
- HTTP 503 credential guard retained.
- Persona system (`PersonaManager`) retained.

### Chapter 4 — `htmx-vite-frontend_20260429`
**Green-field UI.** Delete React. Build a tasteful HTMX UI that's still visually rich.

- Delete `src/js/` entirely (React, TanStack, generated OpenAPI client, all `.test.tsx` stubs).
- New frontend inputs live at repo-root `vite.config.ts` / `package.json` plus `src/resources/{main.js,styles.css,public/}`. Vite runs in `mode="template"` via `litestar-vite`; bundle output lands in `src/app/domain/web/static/dist/`: Tailwind v4 + **Alpine.js** (lightweight reactivity) + **ApexCharts** (visualization).
- Wire `HTMXPlugin()` + `hx-ext="litestar"` for client-side JSON rendering on chart data.
- Two pages, one layout:
  - `chat.html.j2` — reactive HTMX chat (incremental partial swaps, persona switcher, session-id header pattern).
  - `explore.html.j2` — combines the old `performance` + `vector-demo` into one *Vector Explore* page with panels:
    1. Live search box → similarity-score distribution (ApexCharts bar)
    2. Top-K results with similarity bars
    3. Classification ground-truth-vs-live comparison (from Ch 3)
    4. Cosine-similarity heatmap of recent queries
    5. **Oracle EXPLAIN PLAN viewer** — runs `EXPLAIN PLAN FOR <vector search SQL>` + `DBMS_XPLAN.DISPLAY` against the live query; shows the optimizer's choice of HNSW vector index range scan, target accuracy, partition pruning, etc. Educational gold.
- Server returns HTML partials for chat, JSON for chart data; `vite_hmr()` in dev.

### Chapter 5 — `prune-and-document_20260429`
**Make it readable cold.** A new contributor should grok the entire app in 30 minutes.

- Archive 23 timestamped knowledge files; keep `patterns.md` + exactly 3 guides: `architecture.md`, `oracle-vector-search.md`, `adk-patterns.md`.
- CLI trim: keep `python manage.py init`, `python manage.py database upgrade`, `coffee load-fixtures`, `coffee run`, `coffee model-info`, `coffee clear-cache`, and Ch 3's `coffee classify-compare`. Delete `coffee bulk-embed` (folded into fixtures) and `coffee export-fixtures` from the canonical app CLI.
- Remove dead frontend test stubs.
- Rewrite root README as 5-minute quickstart.
- `patterns.md` final pass: drop obsolete gotchas; document HNSW+INMEMORY recipe, parallel-classification trick, ADK 2.0 runner shape, named-SQL pattern, EXPLAIN-on-explore-page idiom.

### Chapter 6 — `documentation-setup_20260429`
**The learning base.** Transform the repo into a premier learning resource with Sphinx.

- Sphinx + Material theme + Mermaid diagrams.
- Narrative deep dives into Oracle 23ai and Vertex AI.
- Autodoc API reference.

### Chapter 7 — `vector-calculator_20260429`
**The utility.** Add a creative client-side widget to the Explore page for storage estimation.

- 7th Panel on the Explore page: **Vector Storage Size Requirement Calculator**.
- Pure client-side (Alpine.js) widget inside `explore.html.j2`.
- Oracle 23ai specific semantics:
  - Vector formats: FLOAT32 (4B), FLOAT64 (8B), INT8 (1B), BINARY (dims/8).
  - Index overhead: HNSW adjacency lists (M * dims * 4 bytes per vector).
  - SGA Pool estimation: Total raw + index size.
- Presets: Gemini (768, 3072), OpenAI (1536), Cohere (1024, 4096).
- Interactive sliders for N (rows) and d (dimensions).
- Creative visualizations (comparing to physical media: Floppy, CD, DVD, Blu-ray).

---

## Global Constraints

These apply to **every** chapter. Reviewers should reject PRs that violate them.

1. **Keep Dishka.** It's simpler than removing it given the existing service shape and matches the official `litestar:litestar-ai-serving` skill docs.
2. **No `from __future__ import annotations` in Dishka provider modules** — runtime introspection breaks.
3. **No backward-compat shims.** This is a reference app; breaking changes are fine, but they must be clean.
4. **Simple > clever.** If you need a comment to explain it, it's too complex. Default to writing no comments.
5. **No new dependencies without justification.** Every package in `pyproject.toml` and `package.json` must earn its place.
6. **Match the published skill docs exactly.** When in doubt: `litestar:litestar-ai-serving`, `litestar:sqlspec`, `litestar:litestar-htmx`, `litestar:litestar-vite` are the canonical references.
7. **Async I/O everywhere.** No sync DB calls in handlers.
8. **Typed adapters and `schema_type=` for every query result.** No raw dicts leaking out of the data layer.
9. **One named SQL file per domain.** No inline SQL strings in services after Ch 2.
10. **Visual polish ≥ current React version on Ch 4.** "Simple HTMX" is not a license to ship something ugly.

---

## Out of Scope

- Multi-tenant auth / users (single anonymous session is fine for the demo).
- SAQ / background workers (no async batch inference yet).
- Streaming chat responses (the canonical doc explicitly says streaming "not yet canonical").
- pgvector / non-Oracle vector backends (Oracle 23ai is the point).
- Inertia.js path (HTMX is the chosen frontend story).
- New product/store domain features. Trim, don't add.

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| ADK 2.0b1 API churn before GA | Pin exact version; isolate ADK calls behind `AIRunner` so a future bump touches one file. |
| 3072-dim vectors blow `vector_memory_size` on dev laptops | Document the 4G recommendation; demo dataset is small enough that memory pressure is low. |
| HTMX rebuild looks worse than the React version | Frontend chapter has explicit "visual polish ≥ current" acceptance criterion; mockup before implement. |
| EXPLAIN PLAN scope creep on Ch 4 | Ship as a single read-only panel using `DBMS_XPLAN.DISPLAY`; no plan-diff tooling, no AST-rendered plan trees. |
| `intent_exemplar` removed too aggressively | Keep the table + fixtures; only move it off the hot path. The "ground truth vs live" panel keeps it relevant. |
| Embedding regen time/cost on Ch 1 | Use the embedding cache table (already exists) so partial reruns are cheap. |

---

## Acceptance (PRD-level)

PRD is complete when:

- All 6 chapters are merged.
- `make install && make test && make lint` is green from a clean clone.
- The 5-minute quickstart in README actually works for a new contributor.
- Published skill citations to this repo (in `litestar:litestar-ai-serving` and `litestar:sqlspec`) match the file layout exactly.
- `patterns.md` reflects the codebase as it actually is, not as it was.
- **Vector Storage Calculator** is functional on the Explore page and accounts for Oracle 23ai formats.

---

## Beads master epic

- **Master**: `oracledb-vertexai-4d6`
- **Ch 1** `foundation-bump_20260429` → `oracledb-vertexai-4d6.1`
- **Ch 2** `accelerator-restructure_20260429` → `oracledb-vertexai-4d6.2` (blocked by Ch 1)
- **Ch 3** `adk2-runner_20260429` → `oracledb-vertexai-4d6.3` (blocked by Ch 2)
- **Ch 4** `htmx-vite-frontend_20260429` → `oracledb-vertexai-4d6.4` (blocked by Ch 2)
- **Ch 5** `prune-and-document_20260429` → `oracledb-vertexai-4d6.5` (blocked by Ch 3 and Ch 4)
- **Ch 6** `documentation-setup_20260429` → `oracledb-vertexai-4d6.6` (blocked by Ch 5)
- **Ch 7** `vector-calculator_20260429` → `oracledb-vertexai-4d6.7` (blocked by Ch 4)
