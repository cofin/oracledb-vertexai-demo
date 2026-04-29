# Learnings: cymbal-coffee-reset_20260429 (Master PRD)

> Synthesized notes from PRD work and chapter implementations. Synced from Beads via `/flow:sync`.

## PRD-level architectural decisions (2026-04-29, planning phase)

These were captured as Beads notes on the master epic `oracledb-vertexai-4d6` and inform every chapter:

1. **Keep Dishka.** Removing it would create more code churn than collapsing 4 providers to 1, and the official `litestar:litestar-ai-serving` skill docs document Dishka providers as the canonical pattern for this exact kind of app. Dishka providers MUST NOT use `from __future__ import annotations` — runtime introspection breaks.

2. **Replace embedding-lookup intent classification with Gemini-2.5-Flash-Lite structured-output, dispatched as a parallel async tool alongside retrieval.** Research showed the bottleneck was the embedding API call (~100-300ms), not vector search itself. BINARY vectors don't help (Hamming distance degrades cosine-trained Gemini vectors). The `intent_exemplar` table is retained as offline ground-truth + a comparison panel on Ch 4's explore page.

3. **Oracle 23ai vector index recipe:** HNSW with `ORGANIZATION INMEMORY NEIGHBOR GRAPH`, `WITH TARGET ACCURACY 95`, `PARAMETERS (TYPE HNSW, NEIGHBORS 40, EFCONSTRUCTION 500)`. Product table also marked `INMEMORY` for fast base-table fetch after index hit. Recommend `vector_memory_size=4G` for the demo. 3072-dim FLOAT32 ≈ 16KB/row including HNSW overhead.

4. **Frontend = HTMX + Tailwind v4 + Alpine.js + ApexCharts via litestar-vite mode=template.** React/TanStack deleted entirely. Visual polish must match or exceed the React version on the explore page (which combines old `performance` + `vector-demo` into one page with 5 panels including a live Oracle EXPLAIN PLAN viewer).

## Refinement pass (2026-04-29)

`flow:code-reviewer` surfaced 11 critical gaps across the four chapter specs. All addressed in-place. Patterns worth carrying forward:

5. **Phase 0 HALT GATE** for chapters that depend on unverified third-party API surfaces (ADK 2.0b1 imports for Ch 3; HTMX `litestar` extension JS path for Ch 4). The gate task forces an executor to smoke-test the import surface before writing any production code. If the surface differs from what the spec assumes, the executor records the actual surface in Beads notes and updates downstream phase snippets — *before* burning effort on guessed APIs.
6. **Cross-chapter file contracts must be pinned.** `dist/classify-compare.json` written by Ch 3 task 3.7 and read by Ch 4 task 4.5 must agree on absolute path (cwd-resolved repo-root). Soft cross-chapter deps (Ch 4 reads Ch 3 output) are documented in the spec but not blocked at the Beads dep-graph level — Ch 3 and Ch 4 can run in parallel per the PRD's execution plan, with the explore-page panel showing a 404 hint until Ch 3 lands.
7. **Provider-count contradictions are an executor footgun.** Ch 2's first draft had the Objective paragraph saying "1 + 1 + APP-singletons" while Acceptance said `== 3`. Always check the math.
8. **Latent bug:** `request_container_var` (Ch 3 deletion target) is **never `.set()` anywhere** — verified via `grep -rn`. Every ADK tool call today builds a brand-new Dishka container. Closure-bound tools fix this incidentally.
9. **Intent exemplar fixture is at 768 dims, 1019 rows, 7.0 MB gzipped** — verified 2026-04-29. Not anomalous; expected ~25–28 MB at 3072 dims. Ch 1 regenerates.

## Revision pass after source flatten (2026-04-29)

10. **Forward-looking specs must use the flattened layout:** Python code is `src/app`, tests are `src/tests`, Vite inputs are root `vite.config.ts` plus `src/resources`, templates live in `src/app/domain/web/templates`, and build output is `src/app/domain/web/static/dist`. `src/py` and `src/js` should appear only as historical completed-work evidence or explicit deletion targets.
11. **CLI ownership is split:** `coffee` is the hand-rolled app CLI (`run`, `load-fixtures`, `clear-cache`, `model-info`, future `classify-compare`); migrations/assets/infrastructure stay on `python manage.py ...`. New plans should not route through `uv run app`, `coffee assets`, `coffee upgrade`, or `coffee_demo_group`.
12. **Release versioning:** Python app modules should import/re-export `app.__metadata__.__version__`; `bump-my-version` should update package metadata (`pyproject.toml`, optional root `package.json`) rather than app source literals. `uv.lock` is regenerated after the bump.
