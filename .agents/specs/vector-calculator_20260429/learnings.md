# Learnings: Vector Storage Size Calculator (vector-calculator_20260429)

## [2026-04-29] - Research Phase
- **Oracle 23ai Vector Types**: FLOAT32, FLOAT64, INT8, BINARY.
- **Compression**: INT8 is 4x smaller than FLOAT32; BINARY is 32x smaller.
- **HNSW Overhead**: Estimated as $M \times d \times 4$ bytes per vector.
- **IVF Overhead**: Generally lower than HNSW, focused on cluster centroids.
