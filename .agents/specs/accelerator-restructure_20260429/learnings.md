# Learnings: accelerator-restructure_20260429

> Notes captured during implementation. Synced from Beads task notes via `/flow:sync`.

_No implementation notes yet — chapter not started._

## Pre-implementation findings (planning phase, 2026-04-29)

- Accelerator's `lib/service.py` is a **pure re-export facade** — there is no custom subclass. The codebase delegates everything to sqlspec's `SQLSpecAsyncService`. Mimic that exactly.
- Accelerator uses **5 providers** but the count is misleading: 3 of them (`LitestarPersistenceProvider`, `CliPersistenceProvider`, `WorkerPersistenceProvider`) are scope-specific copies of the same driver-providing logic. We only need the Litestar variant for now; CLI and Worker can be added if/when SAQ lands.
- The `current_price`/`price` mismatch at `services.py:47` has a band-aid mapping at line 119 that has been silently degrading vector-search response shape since the column was renamed. Reviewers missed it because the band-aid remapped onto the `distance` field — type checker happy, semantics wrong.
- Filter dependencies are **purely additive** to the controller `dependencies` dict — no risk of clobbering hand-rolled deps if the rewrite is methodical.
