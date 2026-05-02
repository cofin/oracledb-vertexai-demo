# Flow: Vector Storage Size Calculator (vector-calculator_20260429)

*Chapter 7 of [cymbal-coffee-reset_20260429](../cymbal-coffee-reset_20260429/prd.md)*
*Beads epic: `oracledb-vertexai-4d6.7` (blocked by Ch 4)*

---

## Specification

### Objective

Add a creative, highly interactive "Vector Storage Size Requirement Calculator" widget to the Explore page. This tool helps users perform "back-of-the-napkin" math for their vector database capacity planning, specifically tailored to Oracle 26ai `VECTOR` types and HNSW indexing.

### Requirements

1. **Integrated UI**: Add a calculator panel to `src/app/domain/web/templates/pages/explore.html.j2`.
2. **Client-Side Driven**: Zero server-side round-trips for the calculator logic. Implemented as vanilla Vite-bundled JavaScript because Alpine.js is no longer part of the active frontend stack.
3. **Oracle 26ai Semantics**:
   - **Data Types**: Support FLOAT32, FLOAT64, INT8, and BINARY.
   - **HNSW Indexing**: Account for adjacency list overhead based on the `M` parameter.
   - **Vector Memory**: Estimate the SGA `Vector Memory` pool requirements.
4. **Interactive Controls**:
   - Sliders/Inputs for **Row Count (N)**: 1,000 to 100M.
   - Sliders/Inputs for **Dimensions (d)**: 1 to 4096.
   - Format Selection: Dropdown/Radio for format (FLOAT32, FLOAT64, INT8, BINARY).
   - Index Type Selection: HNSW, IVF, or None.
   - HNSW `M` parameter slider: 8 to 128 (default 16).
5. **Creative Visualizations**:
   - **Compression Impact**: Visual indicator of storage savings when using INT8/BINARY.
   - Compare total size to physical objects (e.g., "Fits on a Floppy Disk", "12 CD-ROMs", "Half a Blu-ray").
   - Real-time "Impact Gauge" for Vector Memory.
6. **Model Presets**:
   - **Gemini (768 / 3072)**
   - **OpenAI (1536 / 3072)**
   - **Cohere (1024 / 4096)**

### Mathematical Logic (Verified 2026-04-29)

**1. Raw Storage (R):**
- **FLOAT64**: $R = N \times d \times 8$ bytes
- **FLOAT32**: $R = N \times d \times 4$ bytes (Baseline)
- **INT8**: $R = N \times d \times 1$ byte (**4x Compression** vs FLOAT32)
- **BINARY**: $R = N \times \lceil d / 8 \rceil$ bytes (**32x Compression** vs FLOAT32)

**2. Index Overhead (I):**
- **HNSW (Hierarchical Navigable Small World)**:
  - $I = N \times M \times d \times 4$ bytes (Adjacency lists)
  - *Best for recall and dynamic datasets; higher memory footprint.*
- **IVF (Inverted File)**:
  - $I \approx N \times d \times 4$ (Raw data) + small partition overhead.
  - *Best for large static datasets; lower memory footprint.*

**3. Total Footprint:** $T = R + I$ (if Index enabled).

**4. Compression Visualizer:**
- Show a "Savings" percentage when selecting INT8 or BINARY compared to FLOAT32.
- "Space Saved: 75%" (for INT8) or "Space Saved: 96.8%" (for BINARY).

---

## Implementation Plan

### Phase 1: UI Scaffold (`oracledb-vertexai-4d6.7.1`)

- [x] **1.1** Add the calculator panel container to `src/app/domain/web/templates/pages/explore.html.j2`.
- [x] **1.2** Implement the Layout: Left column for inputs, Right column for visual results.
- [x] **1.3** Style with Tailwind v4 utilities to match the existing theme.

### Phase 2: Client-Side Calculator Logic (`oracledb-vertexai-4d6.7.2`)

- [x] **2.1** Define `src/resources/vector-calculator.js` with initial state.
- [x] **2.2** Implement `calculateVectorFootprint()` updating `rawSize`, `indexSize`, and `totalSize`.
- [x] **2.3** Add model presets logic to quickly set `dimensions` and `format`.
- [x] **2.4** Wire sliders and inputs with `data-*` hooks.

### Phase 3: Creative Visualizations (`oracledb-vertexai-4d6.7.3`)

- [x] **3.1** Implement the "Physical Media Comparison" logic.
- [x] **3.2** Add a "Vector Memory" gauge.
- [x] **3.3** Add a "Back-of-napkin" summary card with formatted byte sizes (KB, MB, GB, TB).

### Phase 4: Verification & Learnings (`oracledb-vertexai-4d6.7.4`)

- [x] **4.1** Verify calculations against the formula contract in unit tests.
- [x] **4.2** Build and page-render smoke checks for the Explore page.
- [x] **4.3** Update `patterns.md` with the "Vector Footprint" estimation formulas.

---

## Acceptance Criteria

- The 7th Panel appears on `/explore`.
- Changing sliders/inputs immediately updates the estimated sizes.
- Selecting a model preset (e.g., Gemini 3072) correctly sets dimensions.
- HNSW toggle correctly adds/removes the index overhead from the total.
- Storage sizes are formatted correctly (e.g., "1.24 GB").
- Visual comparison to physical media is present and accurate.
- Zero server-side logs appear during calculator usage (confirms pure client-side).

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Mismatched HNSW overhead formula | Use the conservative `M * d * 4` per-vector estimate from `oracle-performance.md`. |
| Performance lag on large calculations | Formula is simple O(1) math; no impact expected on client. |
| UI Clutter | Use a clean grid layout; hide HNSW params when toggle is off. |
