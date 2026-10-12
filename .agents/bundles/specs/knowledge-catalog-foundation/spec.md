---
type: Spec
flow_id: knowledge-catalog-foundation
title: Oracle 26ai USER_ANNOTATIONS_USAGE Harvester, OKF v0.2 Bundle & coffee sync-catalog CLI
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-10-12T18:24:00Z
updated_at: 2026-10-12T18:24:00Z
description: Add named SQL queries for Oracle 26ai USER_ANNOTATIONS_USAGE and USER_TAB_COLUMNS, CatalogSettings, typed Knowledge Catalog msgspec schemas, committed offline context snapshot + OKF v0.2 catalog bundle, and the uv run coffee sync-catalog CLI command pushing Custom Entries and Global System Aspects (655216118709) to dataplex.googleapis.com/v1.
tags:
  - feature
  - knowledge-catalog
  - oracle
  - okf
  - cli
parent_prd: knowledge-catalog-grounding-demo
research: []
---

# Flow: Oracle 26ai `USER_ANNOTATIONS_USAGE` Harvester, OKF v0.2 Bundle & `coffee sync-catalog` CLI

**Flow ID:** `knowledge-catalog-foundation`
**Parent PRD:** [`knowledge-catalog-grounding-demo`](../knowledge-catalog-grounding-demo/spec.md)
**Depends On:** None

---

## Specification

### Code Analysis Summary

Files examined:

- `src/app/db/migrations/0001_cymball_coffee_products.sql:18-264` — Defines native Oracle 26ai `ANNOTATIONS(...)` on `product`, `store`, `store_product_inventory`, `response_cache`, `embedding_cache`, and `search_metric`, plus column and HNSW index annotations (`Display`, `Description`, `Data_Role`, `Privacy`, `Embedding_Model`, `Embedding_Dimensions`, `Embedding_Purpose`, `Distance`, `Enum_Values`, `Cache_Role`, `Maps_Baseline`, `AI_Surface`).
- `src/app/config.py:131` — Calls `db_mgr.load_sql_files(BASE_DIR / "db" / "sql")`, which automatically loads every `*.sql` file in `src/app/db/sql/`.
- `src/app/lib/settings.py:210-486` (and planned `src/app/lib/settings/` package) — Defines frozen `@dataclass(frozen=True, slots=True)` settings classes loaded via `Settings.from_env()`.
- `src/app/domain/system/schemas/__init__.py:1-40` — Exports system domain `msgspec` schemas (`CamelizedBaseStruct`).
- `src/app/cli/commands.py:147-223` & `src/app/cli/utils.py:21-54` — Declares `@cli.command(...)` Click commands using `@async_inject`, delegating workflow logic to `src/app/cli/_helpers/`.

### Relevant Patterns

- [Architecture Patterns](../../knowledge/patterns/architecture.md) — Named SQL in `src/app/db/sql/*.sql`; thin CLI declarations in `src/app/cli/commands.py` with workflow helpers in `src/app/cli/_helpers/`.
- [Code Style Patterns](../../knowledge/patterns/code-style.md) — SPDX headers (`Apache-2.0`), PEP 604 unions, zero inline `#` comments, `from_json` / `to_json` from `app.utils.serialization`.
- [Testing Patterns](../../knowledge/patterns/testing.md) — `@pytest.mark.anyio` unit tests under `src/tests/unit/<module_path>/test_*.py`.

### Requirements

- **KC-REQ-01 (Oracle 26ai Annotation SQL, `CatalogSettings` & Typed Schemas)**:
  - Create `src/app/db/sql/catalog.sql` with named queries `select-catalog-table-annotations`, `select-catalog-column-metadata`, and `select-catalog-index-annotations` querying `USER_ANNOTATIONS_USAGE` and `USER_TAB_COLUMNS`.
  - Add `CatalogSettings` (`enabled`, `mode`, `project_id`, `location`, `entry_group_id`, `glossary_id`, `snapshot_path`, `context_budget`, `timeout_seconds`) in `src/app/lib/settings.py` (and `src/app/lib/settings/_catalog.py` when modularized) exposed as `settings.catalog`.
  - Create `src/app/domain/system/schemas/_catalog.py` defining `OracleAnnotationRow`, `OracleColumnMetadataRow`, `CatalogColumnMetadata`, `CatalogGoldenQuery`, `CatalogGlossaryTerm`, `CatalogEntrySummary`, `CatalogContextPayload`, `CatalogEntryList`, and `CatalogSyncReport`, re-exported in `src/app/domain/system/schemas/__init__.py`.
- **KC-REQ-02 (`coffee sync-catalog` CLI, Committed Snapshot & OKF v0.2 Bundle)**:
  - Create `src/app/db/fixtures/knowledge_catalog_context.json` containing the canonical Cymbal Coffee Knowledge Catalog entries (`product`, `store`, `store_product_inventory`, `response_cache`, `embedding_cache`, `search_metric`), their harvested Oracle 26ai annotations, steward-certified `guidelines` (2-Tier Inventory Precedence, Off-Menu Brand Guardrail, Request-Scoped Coordinate Privacy), Golden SQL `queries`, and Business Glossary terms.
  - Create `src/app/cli/_helpers/catalog.py` implementing `DATAPLEX_V1_BASE_URL`, `build_default_catalog_snapshot`, `write_catalog_snapshot`, `load_catalog_snapshot`, `render_lookup_context_yaml`, `harvest_oracle_catalog_entries`, `export_okf_catalog_bundle`, `push_entries_to_knowledge_catalog`, and `run_sync_catalog_workflow`.
  - Register `@cli.command(name="sync-catalog")` in `src/app/cli/commands.py` supporting `--push`, `--export-okf`, `--from-fixture`, and `--dry-run`.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `KC-REQ-01` | `1.1` | `behavior_tdd` | `src/app/db/sql/catalog.sql`, `src/app/lib/settings.py`, `src/app/domain/system/schemas/_catalog.py`, `src/app/domain/system/schemas/__init__.py` | `src/tests/unit/app/domain/system/test_catalog_schemas.py` |
| `KC-REQ-02` | `1.2` | `behavior_tdd` | `src/app/db/fixtures/knowledge_catalog_context.json`, `src/app/cli/_helpers/catalog.py`, `src/app/cli/commands.py`, `.agents/bundles/knowledge/catalog/index.md` | `src/tests/unit/app/cli/test_sync_catalog.py` |

---

## Implementation Plan

### Phase 1: Metadata Extraction SQL, Schemas & `coffee sync-catalog` CLI

- [ ] 1.1 Add `src/app/db/sql/catalog.sql`, `CatalogSettings`, and `src/app/domain/system/schemas/_catalog.py` contracts
- [ ] 1.2 Implement `src/app/db/fixtures/knowledge_catalog_context.json`, `src/app/cli/_helpers/catalog.py` (Oracle harvester, OKF v0.2 exporter, and `dataplex.googleapis.com/v1` REST pusher), and `uv run coffee sync-catalog`

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `knowledge-catalog-foundation` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - Populate global system aspects (`655216118709.global.{schema,overview,guidelines,queries}`) on `Entry` payloads so `lookupContext` assembles them natively without custom aspect types.
  - Use `httpx` + `google.auth` ADC for `dataplex.googleapis.com/v1` REST calls instead of adding a new `google-cloud-dataplex` dependency.
- **Newest Discoveries**:
  1. `src/app/config.py:131` auto-loads all `*.sql` files in `src/app/db/sql/`, so adding `src/app/db/sql/catalog.sql` registers the queries automatically.
- **Blockers & Unblock Conditions**: None
- **Next Exact Step**: Claim and execute Task `1.1` (`tasks/1.1.md`).
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/knowledge-catalog-grounding-demo/research/research_knowledge_catalog_demo_20261012/research.md`
  - `.agents/bundles/knowledge/guides/oracle-database.md`
  - `.agents/bundles/knowledge/patterns/code-style.md`
