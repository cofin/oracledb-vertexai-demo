# Knowledge Entry: cymbal-coffee-reset_20260429

- **Flow ID:** `cymbal-coffee-reset_20260429`
- **Description:** Master PRD — modernize the demo onto ADK 2.0 + Oracle 26ai (3072-dim HNSW INMEMORY) + sqlspec 0.46 + HTMX/Vite, eliminate workarounds, and align with the canonical `litestar:litestar-ai-serving` and `litestar:sqlspec` skill docs.
- **Completed:** 2026-05-02
- **Beads Epic:** `oracledb-vertexai-4d6`
- **Topics:** modernization, adk2, oracle-26ai, hnsw, sqlspec, dishka, vector-search, intent-classification, frontend, cli, restructure
- **Sub-flows with their own knowledge entries:** [htmx-vite-frontend_20260429](htmx-vite-frontend_20260429.md) (Ch 4)

<!-- truth: start -->
## Summary

The reset PRD shipped in nine chapters across two months. It modernized the
demo onto ADK 2.0 graph workflows with parallel intent classification, native
Oracle 26ai 3072-dim HNSW INMEMORY vectors, sqlspec 0.46 named-SQL services
with a 3-provider Dishka container, and an HTMX + Tailwind + vanilla-Vite
frontend that replaced the React/TanStack stack wholesale. Two corrective
PRDs (UI regression recovery, test-suite reorganization) closed alongside the
main chapters.

## Architectural Decisions (load-bearing)

1. **Keep Dishka.** Removing it would create more code churn than collapsing
   four providers to three. Dishka providers MUST NOT use
   `from __future__ import annotations` — runtime introspection breaks under
   PEP 563 string forward refs.
2. **Intent classification = Gemini 2.5 Flash-Lite structured output**, not
   embedding-lookup. Bottleneck is the embedding API call (~100-300ms), not
   vector search. BINARY vectors do not help (Hamming distance degrades
   cosine-trained Gemini vectors). Dispatched as a parallel async tool
   alongside retrieval.
3. **Oracle vector index recipe:** HNSW `ORGANIZATION INMEMORY NEIGHBOR GRAPH`
   `WITH TARGET ACCURACY 95 PARAMETERS (TYPE HNSW, NEIGHBORS 40, EFCONSTRUCTION 500)`.
   Product table also `INMEMORY`. `vector_memory_size=4G` recommended;
   3072-dim FLOAT32 ≈ 16 KB/row including HNSW overhead.
4. **Frontend = HTMX + Tailwind v4 + vanilla Vite modules + ApexCharts via
   litestar-vite mode=template.** React/TanStack and Alpine.js deleted entirely.

## Per-Chapter Highlights (knowledge already in patterns.md / guides)

- **Ch 1 — Foundation Bump:** sqlspec 0.46 + ADK 2.0b1 + 3072-dim HNSW INMEMORY
  schema rewrite + Vertex `gemini-embedding-001` with `task_type` discipline.
- **Ch 2 — Domain/Service Restructure:** `lib/service.py` is a re-export of
  `SQLSpecAsyncService`; named SQL files for everything that benefits from
  `.where(...)` chaining or non-trivial SELECT shape; 3 Dishka providers
  (`LitestarPersistenceProvider`, `IntegrationsProvider`, `DomainServiceProvider`).
  msgspec Struct naming is entity-noun + intent qualifier (`Product`,
  `ProductCreate`, `ProductMatch`) — no `DTO` / `Result` / `Response` suffixes.
  `current_price`/`price` band-aid removed; `1 - VECTOR_DISTANCE(..., COSINE)`
  is the single source of similarity scores — math lives in SQL.
- **Ch 3 — ADK 2.0 Runner:** `Workflow` with `START` fanout to a
  `FunctionNode` intent classifier and an `LlmAgent` coffee_turn, joined at a
  `JoinNode`. Closure-bound tools captured per-request. Removed dead
  `request_container_var` / `worker_container_var` family (zero callers
  verified). `text/x.enum` mode for the Flash-Lite classifier; raises on
  unknown labels (no defensive fallback). Placeholder Vertex config raises a
  typed 503 before ADK runs. See
  [ADK Agent Patterns](guides/adk-agent-patterns.md).
- **Ch 4 — HTMX/Vite Frontend:** see
  [htmx-vite-frontend_20260429](htmx-vite-frontend_20260429.md).
- **Ch 5 — Prune & Document:** active guide set collapsed to three
  (`architecture.md`, `oracle-vector-search.md`, `adk-agent-patterns.md`).
  `.agents/archive/` is ignored disposable history; durable lessons
  synthesize into `.agents/knowledge/` or `.agents/patterns.md` BEFORE
  archive cleanup. README rewritten to a 5-minute quickstart.
  `manage migrate` requires `--no-prompt` for non-interactive walkthroughs.
- **Ch 7 — Vector Calculator:** vanilla Vite module
  `src/resources/vector-calculator.js` powers the Explore page's vector
  storage estimator (FLOAT64/32/INT8/BINARY × HNSW/IVF/None). Client-only,
  no fetch/HTMX. INT8 is 4× smaller than FLOAT32; BINARY is 32× smaller.
  HNSW Vector Pool sizing uses Oracle's rough `1.3 * rows * dimensions *
  element_size` estimate; exact HNSW/IVF sizing belongs to the DBMS_VECTOR
  advisor.
- **Ch 8 (corrective) — UI Regression Recovery:** restored shared shell,
  popovers, structured `sql_phases` telemetry, and the ApexCharts dashboard.
  Removed the descoped classify-compare panel/endpoint/schema. Vector demo
  endpoint accepts both HTMX form and JSON body shapes. `hx-ext="litestar"`
  scoped out of HTML-swap panels. The current product/version label is
  `Oracle 26ai`, not `Oracle 23ai` even though older planning text mentions
  the latter.
- **Ch 9 (corrective) — Test Suite Reorganization:** strict `unit` /
  `integration` module-path layout under `src/tests/`. Layout guard rejects
  top-level test buckets and direct
  `src/tests/{unit,integration}/test_*.py`. Repo path helpers in
  `src/tests/support/`. Shared per-worker Oracle DDL + fixture loading;
  function-scoped driver/session fixtures stay small. Tests that mutate
  products use unique SKUs plus targeted cleanup. `make lint` only checks
  tracked files via pre-commit, so run `uv run ruff check src/tests`
  directly when test files are still untracked.

## Where to look next

- Active patterns: `.agents/patterns.md`.
- Architecture map: `.agents/knowledge/guides/architecture.md`.
- ADK runner internals: `.agents/knowledge/guides/adk-agent-patterns.md`.
- Oracle vectors: `.agents/knowledge/guides/oracle-vector-search.md`.
- HTMX/Vite frontend: `.agents/knowledge/htmx-vite-frontend_20260429.md`.
- Project-wide guide: `.agents/knowledge/project-guide.md`.
<!-- truth: end -->
