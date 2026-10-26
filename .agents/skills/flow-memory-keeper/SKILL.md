---
name: flow-memory-keeper
description: Use at task, phase, flow, sync, archive, finish, revise, or failure checkpoints to keep Flow specs clean, capture learnings and failures, elevate durable patterns, and refine this skill with project-specific nuances
---

# Flow Memory Keeper

## Purpose

This project-local skill prevents Flow work from drifting into stale specs, missing learnings, or half-archived folders.

Use it whenever work is completed, paused, blocked, revised, synced, or archived.

<workflow>

## Mandatory Outcomes

Before claiming a task, phase, or flow is complete:

1. Ensure `spec.md` is readable and current through the normal Flow sync process.
2. Capture concrete learnings in the flow's `learnings.md`.
3. Capture failures, false starts, blockers, and recovery notes when they would help a future session.
4. If the user had to repeat a correction or showed frustration that something was forgotten, flag that as a workflow gap and capture it explicitly.
5. Elevate durable patterns to evidence-backed `.agents/bundles/knowledge/patterns/<topic>.md` chapters.
6. Update chapters recursively under `.agents/bundles/knowledge/` when the current-state knowledge base changed, preserving project-shaped relative paths, indexes, and links.
7. If the flow is complete, archive it cleanly and leave the active spec area uncluttered.
8. Capture validated repo-native commands and verification workflows in `.agents/bundles/knowledge/workflow.md` when they were discovered or corrected during the work.

## Completion Protocol

### Task or Phase Completion

1. Append a concise entry to `.agents/bundles/specs/<flow_id>/learnings.md`:
   - what changed
   - why it changed
   - files touched
   - commands or checks that mattered
   - canonical repo commands that future agents should reuse
   - gotchas, failures, and recoveries worth remembering
   - any repeated user correction or frustration that revealed a missing default, checklist item, or workflow rule
2. Move reusable guidance into a topic-specific `.agents/bundles/knowledge/patterns/<topic>.md` chapter.
3. If the work changed architecture, conventions, tooling, operational behavior, or canonical project commands, recursively locate and update the relevant chapter under `.agents/bundles/knowledge/` at its existing project-shaped relative path; keep `.agents/bundles/knowledge/workflow.md` as the stable command default.
4. Promote repeated user corrections or frustration into an obvious durable rule instead of leaving it as a one-off note.
5. Run the normal Flow sync step so `spec.md` reflects the latest state.

### Failure Capture

Capture failure notes whenever one of these happened:

- a hypothesis was wrong
- a command or tool failed in a non-obvious way
- a harness integration behaved differently than expected
- a backend migration exposed a hidden assumption
- a repeated reminder from the user revealed a workflow gap
- the user seemed frustrated that something obvious was forgotten again

Failure notes belong in `learnings.md`, but keep them short and reusable. Focus on what future agents should avoid or check earlier.

### Flow Archive

When a flow is finished:

1. Confirm final reconciliation and verification ran through the Flow state contract.
2. Ensure `learnings.md` is not missing critical discoveries.
3. Elevate the stable patterns and current-state knowledge before archiving.
4. Apply the archive state operation: synthesize current-state knowledge, append
   one bundle-log entry, then delete the completed spec directory recorded by
   the approved archive inventory. Do not create a resident archive tree.
5. Confirm the completed spec directory is absent and no stale scratch file
   remains in the active specs area.

</workflow>

<guardrails>

## Skill Refinement Loop

This skill should improve over time.

When you discover a repeated project nuance, add or revise a short rule below instead of keeping the lesson only in session memory.

Only keep:

- durable project-specific rules
- recurring harness quirks
- recurring workflow misses
- validated project-native command wrappers that should become defaults
- user corrections or frustration that clearly indicate a missing default or checklist item
- archive/sync/learnings habits that proved necessary

Do not keep:

- one-off narrative history
- temporary debugging logs
- duplicate rules already captured elsewhere

</guardrails>

<validation>

Before claiming a task, phase, or flow is complete, verify:

- [ ] `spec.md` was synced through the normal Flow process
- [ ] `learnings.md` captures the durable lessons, failures, and recoveries
- [ ] reusable guidance was elevated to an evidence-backed `.agents/bundles/knowledge/patterns/<topic>.md` chapter when appropriate
- [ ] nested chapters, indexes, and links under `.agents/bundles/knowledge/` reflect current-state knowledge without flattening
- [ ] repeated user corrections or frustration were promoted into an explicit rule when applicable
- [ ] canonical repo commands and verification flows were captured when they were learned or corrected
- [ ] completed flows were contracted without a resident archive tree or stale active-spec clutter

</validation>

## Project Nuances

- This consumer skill is installed at `.agents/skills/flow-memory-keeper/SKILL.md`;
  `.agents/skills/` is the only operational project-skill authority.
- Inventory UI selectors in `PageController` (`src/app/domain/web/controllers/_pages.py`) must be data-driven from `StoreService` (`src/app/domain/products/services/_stores.py`) and seeded fixtures (`StoreService.get_all_stores()` or `StoreService.list_with_count`), not hardcoded store preset arrays.
- Domain implementation modules use private `_*` filenames re-exported via package `__init__.py` facades, schemas inherit from `FrozenBaseStruct` or `CamelizedFrozenStruct` (`src/app/lib/schema.py`), data services inherit from `OracleLoaderService` or `OracleAsyncService` (`src/app/lib/service.py`), and Dishka wiring uses `create_container()` / `get_providers()` in `src/app/ioc/__init__.py` (`ConfigProvider`, `DBProvider`, `AIProvider`, `DomainServiceProvider`).
- SQLSpec `0.69.0` defaults `fetch_lobs` to `False` (returning `CLOB`/`BLOB` columns under 1 GB directly as inline Python `str` / `bytes`), while `DatabaseSettings.get_queue_config()` (`session_key="queue_db_session"` in `src/app/lib/settings/_database.py`) isolates `OracledbAsyncQueueStore`'s background worker pool and config mutations from `config.db`.
- When joining HNSW vector searches to relational tables (`vector-search-products-by-store` in `src/app/db/sql/products.sql`), isolate `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST 50 ROWS ONLY` (or `:limit`) inside a CTE before joining or re-sorting by store stock status and applying the outer `FETCH FIRST :limit ROWS ONLY` so Oracle 26ai preserves the HNSW `VECTOR INDEX ACCESS` plan.
- When updating OKF chapters, operational skills, or archiving a completed Flow spec, verify that no markdown file under `.agents/bundles/` or `.agents/skills/` retains retired symbol names, broken relative links to a contracted `.agents/bundles/specs/<flow_id>/` directory, or non-existent backticked repository paths (`src/tests/unit/test_okf_layout.py` enforces relative link resolution across `.agents/bundles/` and retired-symbol hygiene across active agent docs and `.agents/skills/`, while `.agents/skills/ghop-review-manager/scripts/validate_agentic_review.py` enforces backticked repository path existence across `review-*` skills).
