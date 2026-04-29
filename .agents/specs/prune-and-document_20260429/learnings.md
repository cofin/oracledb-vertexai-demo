# Learnings: prune-and-document_20260429

> Notes captured during implementation. Synced from Beads task notes via `/flow:sync`.

_No implementation notes yet — chapter not started._

## Pre-implementation findings (planning phase, 2026-04-29)

- The `.agents/` knowledge base accumulated **8 timestamped notes + 8 guides** plus 7 archived spec dirs since the project began. Most decisions live in code now; the notes are valuable history but noise to a new contributor.
- **Migration `0001_cymball_coffee_products.sql` is already minimal** — no dead DDL or commented-out experimental code. Ch 1 handles the only required edits (HNSW, 3072, INMEMORY, MD5→SHA256 comment).
- `manage.py init` may pull deleted commands — audit during Phase 3.
- `.gitignore` must NOT exclude `.agents/archive/` — historical context is part of the repo per PRD.
- A 5-minute quickstart bound is ambitious but achievable: the bottleneck is usually `make install-uv && make install` (uv-cached makes this fast on warm machines). Time it on a fresh container to validate.
- `coffee bulk-embed` and `coffee export-fixtures` are useful for maintainers but pollute the contributor CLI. Move to `tools/dev/` rather than delete entirely.
