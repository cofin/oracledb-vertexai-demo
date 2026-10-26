---
name: review-oracle-sqlspec
description: Review Oracle 26ai SQL, SQLSpec 0.69.0 async services and inline LOB configuration, HNSW vector search, Hybrid RRF queries, litestar-queues pool isolation, and APEX 26.1 SQL/PLSQL tooling.
---

# Oracle 26ai & SQLSpec Review (`review-oracle-sqlspec`)

Reviews SQL files (`src/app/db/sql/`, including `src/app/db/sql/deploy/configure-apex-cdn.sql` and `src/app/db/sql/deploy/revert-apex-cdn.sql`), baseline migrations (`src/app/db/migrations/`), SQLSpec `0.69.0` settings and services (`src/app/lib/settings/_database.py`, `src/app/lib/service.py`, `src/app/lib/text_search.py`), `litestar-queues` Oracle pool isolation, APEXlang application sources (`src/apex/cymbal-coffee-ops/`), and Oracle/APEX provisioning tools (`tools/oracle/adb.py`, `tools/oracle/apex_catalog.py`, `tools/oracle/apex_lang.py`, `tools/oracle/apex_vertex.py`, `tools/oracle/cli/apex.py`).

## Capsule Constraints

- Do not call disabled GHOP tools (`run_command`, `code_search`, `invoke_subagent`, `define_subagent`, `manage_subagents`, `read_url_content`, `search_web`, `schedule`, `generate_image`). Use `view_file`, `grep_search`, `find_by_name`, and `list_dir` only.
- Before emitting any review comment, read `references/false-positive-suppressions.md` and `references/oracle-sqlspec-checklist.md`. Never flag patterns listed in `references/false-positive-suppressions.md`.
