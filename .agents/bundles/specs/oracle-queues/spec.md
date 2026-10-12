---
type: Spec
flow_id: oracle-queues
title: Oracle 26ai Background Task Queues (litestar-queues)
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-10-12T17:35:00Z
updated_at: 2026-10-12T17:35:00Z
description: Configure litestar-queues[sqlspec]>=0.12.0 on Oracle 26ai with a dedicated OracleAsyncConfig preserving fetch_lobs=True on config.db, wire QueuePlugin and AutowirePlugin job discovery, and implement system.cache_cleanup and products.embed_missing tasks plus CLI worker commands.
tags:
  - feature
  - queues
  - oracle
  - litestar
parent_prd: coffee-agent-stabilization-and-hybrid-search
research: []
---

# Flow: Oracle 26ai Background Task Queues (`litestar-queues`)

**Flow ID:** `oracle-queues`
**Parent PRD:** [`coffee-agent-stabilization-and-hybrid-search`](../coffee-agent-stabilization-and-hybrid-search/spec.md)
**Depends On:** [`platform-alignment`](../platform-alignment/spec.md)

---

## Specification

### Code Analysis Summary

Files examined on `feat/gemini-embeddings` (`@3a3cbd1`):

- `pyproject.toml`, `src/app/lib/settings/`, `src/app/server/plugins.py`, `src/app/cli/commands.py` — Background task queues (`litestar-queues`) are not configured anywhere in the repository.
- Promoted research (`research_modern_litestar_oracle_patterns_20261007` and `research_codebase_audit_and_reference_patterns_20261012`) confirmed:
  1. `litestar-queues[sqlspec]>=0.12.0` natively supports the `oracledb` SQLSpec adapter using `FOR UPDATE SKIP LOCKED` and Oracle DDL (`NUMBER(19)`, `TIMESTAMP WITH TIME ZONE`, `CLOB`).
  2. **Critical Oracle LOB Isolation Rule**: `SQLSpecBackend._disable_oracle_lob_wrapping` sets `driver_features["enable_AutoLob"] = False` (`fetch_lobs=False`) on the `OracleAsyncConfig` passed to `SQLSpecBackendConfig`. Passing the main application `config.db` to `SQLSpecBackendConfig` would disable `AutoLob` for all application queries and break `json.loads()` on CLOB columns. Therefore, `DatabaseSettings.get_queue_config()` must instantiate a dedicated `OracleAsyncConfig` (`extension_config={"litestar": {"session_key": "queue_db_session"}}`) exclusively for `SQLSpecBackendConfig`.
  3. Default to `execution_backend="asgi"` (embedded worker in the web process for single-process demo ergonomics) and `wakeup_mode="polling"` (with optional `wakeup_mode="oracle_aq"` when Oracle AQ/TxEventQ hints are enabled).

### Relevant Patterns

- [SQLSpec Services](../../knowledge/patterns/sqlspec-services.md) — `OracleAsyncConfig` lifecycle and session isolation.
- [Dishka Dependency Injection](../../knowledge/patterns/dishka-di.md) — `worker_container_var` / `request_container_var` resolution inside background `@task` functions.

### Requirements

- **REQ-10 (Oracle 26ai `litestar-queues` Configuration, Tasks & Worker CLI)**:
  - Add `litestar-queues[sqlspec]>=0.12.0` to `pyproject.toml`, create `src/app/lib/settings/_queue.py` (`QueueSettings`), and add `DatabaseSettings.get_queue_config()` in `src/app/lib/settings/_database.py` returning a dedicated `OracleAsyncConfig` so `config.db` retains `fetch_lobs=True`.
  - Wire `QueuePlugin` and `AutowirePlugin(..., integrations=["dishka", "queues"])` in `src/app/server/plugins.py` and `src/app/ioc/_database.py`.
  - Create `src/app/lib/jobs.py` (`get_task_container()`), `src/app/domain/system/jobs.py` (`@task("system.cache_cleanup")` with 15-minute cron schedule cleaning expired `response_cache` and stale `agent_session` rows), and `src/app/domain/products/jobs.py` (`@task("products.embed_missing")` refreshing product and `chat_route` embeddings).
  - Add `coffee worker` CLI subcommands and `coffee bulk-embed --enqueue` in `src/app/cli/commands.py`.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `REQ-10` | `4.1` | `behavior_tdd` | `pyproject.toml`, `src/app/lib/settings/_queue.py`, `src/app/lib/settings/_database.py`, `src/app/lib/settings/__init__.py`, `src/app/config.py`, `src/app/server/plugins.py`, `src/app/ioc/_database.py` | `src/tests/unit/app/lib/test_queue_settings.py` |
| `REQ-10` | `4.2` | `behavior_tdd` | `src/app/lib/jobs.py`, `src/app/domain/system/jobs.py`, `src/app/domain/products/jobs.py`, `src/app/db/sql/system.sql`, `src/app/cli/commands.py`, `src/app/cli/main.py` | `src/tests/unit/app/domain/test_background_jobs.py` |

---

## Implementation Plan

### Phase 1: Queue Backend & LOB-Isolated Oracle Config

- [ ] 4.1 Add `litestar-queues[sqlspec]>=0.12.0`, `QueueSettings`, dedicated `DatabaseSettings.get_queue_config()`, and `QueuePlugin` wiring
- [ ] 4.2 Implement `lib/jobs.py`, `system.cache_cleanup` and `products.embed_missing` tasks, `coffee worker` CLI group, and `bulk-embed --enqueue`

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `oracle-queues` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - Construct a separate `OracleAsyncConfig` in `DatabaseSettings.get_queue_config()` for `SQLSpecBackendConfig` so `SQLSpecBackend._disable_oracle_lob_wrapping` does not mutate `config.db`.
  - Default to `execution_backend="asgi"` and `wakeup_mode="polling"` (`QueueSettings`).
- **Newest Discoveries**:
  1. `SQLSpecBackend._disable_oracle_lob_wrapping` sets `driver_features["enable_AutoLob"] = False` on its `OracleAsyncConfig` (`research_codebase_audit_and_reference_patterns_20261012`).
- **Blockers & Unblock Conditions**: Depends on `platform-alignment`.
- **Next Exact Step**: Claim and execute Task `4.1` (`tasks/4.1.md`) after `platform-alignment` completes.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/coffee-agent-stabilization-and-hybrid-search/research/research_modern_litestar_oracle_patterns_20261007/research.md`
  - `.agents/bundles/knowledge/guides/oracle-database.md`
