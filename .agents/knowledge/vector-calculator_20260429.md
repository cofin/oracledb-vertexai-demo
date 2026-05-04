# Knowledge Entry: vector-calculator_20260429

- **Flow ID:** `vector-calculator_20260429`
- **Description:** Ch 7 — client-only Oracle vector storage estimator on the Explore page (rows × dimensions × format × index → byte total).
- **Completed:** 2026-05-02
- **Beads Epic:** `oracledb-vertexai-4d6.7`
- **Topics:** vector, calculator, oracle-26ai, explore, vanilla-vite, frontend-only

<!-- truth: start -->
## Summary

The Explore page renders a full-width Vector Storage Calculator panel with
row/dimension sliders, format selector (FLOAT64 / FLOAT32 / INT8 / BINARY),
index selector (HNSW / IVF / None), model presets, byte totals,
compression savings, and a Vector memory gauge. The
widget is client-only — no fetch/HTMX calls — implemented as a vanilla Vite
module bound to Jinja markup through `data-*` attributes.

## Patterns Elevated (see patterns.md for full list)

- Interactive Explore widgets are vanilla Vite modules under
  `src/resources/`, imported by `main.js`, and bound to Jinja through
  `data-*` attributes. Do NOT use Alpine.js — it was removed from the active
  frontend stack during UI regression recovery.
- Client-only widgets do not perform fetch/HTMX calls unless the panel
  explicitly needs server data.
- Oracle 26ai vector formats: FLOAT64, FLOAT32, INT8, BINARY. INT8 is 4×
  smaller than FLOAT32; BINARY is 32× smaller. Both lossy compared to
  FLOAT32.
- HNSW Vector Pool sizing uses Oracle's documented rough estimate:
  `1.3 * rows * dimensions * element_size`. Exact HNSW/IVF sizing belongs to
  `DBMS_VECTOR.INDEX_VECTOR_MEMORY_ADVISOR`; the client calculator should not
  invent neighbor-count or IVF partition overhead formulas.

## Key Files

- `src/resources/vector-calculator.js` — client-only estimator module.
- `src/app/domain/web/templates/pages/explore.html.j2` — full-width calculator panel with sliders, selectors, byte totals, media comparison, and Vector memory gauge.
- `src/tests/unit/src/resources/test_explore_frontend.py` — pins the client-only calculator contract.
- `src/tests/integration/app/domain/web/controllers/test_pages.py` — pins Explore page rendering.

## Validation

`./node_modules/.bin/vite build` (passes with the existing large-bundle
warning); focused Explore tests; `make lint`; `make test`.
<!-- truth: end -->
