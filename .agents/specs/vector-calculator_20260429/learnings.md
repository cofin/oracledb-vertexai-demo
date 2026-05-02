# Learnings: Vector Storage Size Calculator (vector-calculator_20260429)

## [2026-04-29] - Research Phase
- **Oracle 23ai Vector Types**: FLOAT32, FLOAT64, INT8, BINARY.
- **Compression**: INT8 is 4x smaller than FLOAT32; BINARY is 32x smaller.
- **HNSW Overhead**: Estimated as $M \times d \times 4$ bytes per vector.
- **IVF Overhead**: Generally lower than HNSW, focused on cluster centroids.

## [2026-05-02] - Implementation Phase
- **Spec drift handled**: the original plan called for Alpine.js, but UI
  recovery removed Alpine from the current frontend. The calculator now uses
  a dedicated vanilla Vite module (`src/resources/vector-calculator.js`) wired
  to Jinja through `data-*` attributes and makes no fetch/HTMX calls.
- **Explore panel added**: `src/app/domain/web/templates/pages/explore.html.j2`
  now renders a full-width Vector storage calculator panel with row/dimension
  sliders, FLOAT64/FLOAT32/INT8/BINARY formats, HNSW/IVF/None index selection,
  HNSW M control, model presets, byte totals, media comparison, compression
  savings, and Vector memory gauge.
- **Tests added**: `src/tests/unit/src/resources/test_explore_frontend.py`
  pins the client-only calculator contract and `src/tests/integration/app/domain/web/controllers/test_pages.py`
  pins Explore page rendering.
- **Validation**: focused Explore tests passed and `./node_modules/.bin/vite build`
  passed with the existing large bundle warning.
