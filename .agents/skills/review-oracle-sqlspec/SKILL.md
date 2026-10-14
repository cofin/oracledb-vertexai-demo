---
name: review-oracle-sqlspec
description: Review Oracle 26ai SQL, SQLSpec async drivers, HNSW vector search, Hybrid RRF queries, and litestar-queues LOB pool isolation.
---

# Oracle 26ai & SQLSpec Review (`review-oracle-sqlspec`)

Reviews SQL files (`src/app/db/sql/`), baseline migrations (`src/app/db/migrations/`), SQLSpec services, and `litestar-queues` Oracle configurations.

## Capsule Constraints

- Do not call disabled GHOP tools (`run_command`, `code_search`, `invoke_subagent`, `define_subagent`, `manage_subagents`, `read_url_content`, `search_web`, `schedule`, `generate_image`). Use `view_file`, `grep_search`, `find_by_name`, and `list_dir` only.
- Before emitting any review comment, read `references/false-positive-suppressions.md` and `references/oracle-sqlspec-checklist.md`. Never flag patterns listed in `references/false-positive-suppressions.md`.
