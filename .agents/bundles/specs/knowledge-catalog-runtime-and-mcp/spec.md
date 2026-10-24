---
type: Spec
flow_id: knowledge-catalog-runtime-and-mcp
title: Knowledge Catalog Runtime Service, Agent Tooling, and MCP Surfaces
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-10-12T18:30:00Z
updated_at: 2026-10-12T18:40:00Z
description: Implement KnowledgeCatalogService with Live GCP (searchEntries + lookupContext) and <2ms Local Snapshot/Oracle fallback modes, register it in Dishka DomainServiceProvider, expose lookup_knowledge_catalog via CatalogController (LitestarMCP /mcp), bind lookup_catalog_context into AgentOrchestrationService, and add Dataplex MCP Toolbox config in tools/lib/utils.py.
tags:
  - feature
  - knowledge-catalog
  - mcp
  - a2a
  - ai
parent_prd: knowledge-catalog-grounding-demo
research: []
---

# Flow: Knowledge Catalog Runtime Service, Agent Tooling, and MCP Surfaces

**Flow ID:** `knowledge-catalog-runtime-and-mcp`
**Parent PRD:** [`knowledge-catalog-grounding-demo`](../knowledge-catalog-grounding-demo/spec.md)
**Depends On:** [`knowledge-catalog-foundation`](../knowledge-catalog-foundation/spec.md)

---

## Specification

### Code Analysis Summary

Files examined:

- `src/app/domain/system/services/__init__.py:1-7` — Exports `BASE_SYSTEM_INSTRUCTION`, `CacheService`, `MetricsService`, and `PersonaManager`.
- `src/app/ioc/_domain.py` — Defines `DomainServiceProvider(Provider)` with `scope = Scope.REQUEST`, injecting `OracleAsyncDriver` and `SQLFileLoader` (`src/app/ioc/_database.py`) and calling `Settings.from_env()`.
- `src/app/domain/system/controllers/__init__.py:1-14` & `_system.py:1-24` — Exports `MetricsController`, `SystemController`, and `controllers: list[type[Controller]] = [MetricsController, SystemController]` auto-registered by `AutowirePlugin` (`src/app/server/plugins.py:114`).
- `src/app/domain/ai/services/_agent.py:22-165` & `src/app/domain/ai/runtime/_stream.py:50-294` — `AgentOrchestrationService.stream_conversation_turn` executes turns over `SpecTree` and forwards `final_metadata` to `AgentStreamService.adapt(..., final_metadata=...)`.
- `src/app/domain/chat/schemas/_forms.py`, `src/app/domain/chat/controllers/_helpers.py:23-131` & `_chat.py:67-113` — Parses `CoffeeChatForm` and streams `POST /api/chat/stream`.
- `src/app/domain/ai/a2a/_card.py:1-40` — Defines `COFFEE_AGENT_CARD` and `build_agent_card`.
- `tools/lib/utils.py:241-264` — Defines `build_mcp_toolbox_oracle_server_config()` and `build_antigravity_mcp_config(*, include_sqlcl: bool = True, include_mcp_toolbox: bool = True)`.

### Relevant Patterns

- [Core Platform (`lib/`, `ioc/`, `server/`, `cli/`)](../../knowledge/domains/core-lib-ioc-server-cli.md) — `src/app/ioc/` modules must never use `from __future__ import annotations`; controller routes use `Inject[T]`.
- [Architecture Patterns](../../knowledge/patterns/architecture.md) — Named SQL queries (`select-catalog-column-metadata`) resolved via `SQLFileLoader` (`sql_loader.get_sql(...)`) without importing `app.config`.
- [Code Style Patterns](../../knowledge/patterns/code-style.md) — Zero inline `#` comments in Python files, PEP 585/604 typing, Google-style docstrings.

### Requirements

- **KC-REQ-03 (Dual-Mode `KnowledgeCatalogService` & Dishka DI Registration)**:
  - Implement `KnowledgeCatalogService` in `src/app/domain/system/services/_catalog.py` supporting:
    1. **Live GCP Mode** (`mode="live"` or `mode="auto"` with a non-placeholder `project_id`): Calls `POST https://dataplex.googleapis.com/v1/projects/{project}/locations/{location}:lookupContext` using `httpx.AsyncClient` and `google.auth` ADC bearer tokens, falling back gracefully to the local snapshot on network/auth errors.
    2. **Local Snapshot + Live Oracle 26ai Mode** (`mode="local"` or fallback): Resolves matching `CatalogEntrySummary` items (`oracle:cymbal-coffee:product`, `oracle:cymbal-coffee:store`, `oracle:cymbal-coffee:store_product_inventory`, etc.) from `knowledge_catalog_context.json`, merges live `select-catalog-column-metadata` annotations from Oracle 26ai when `driver` is present, and renders the `lookupContext` YAML bundle in `< 2ms`.
    3. **Disabled Mode** (`enabled=False` or `mode="off"`): Returns an empty `CatalogContextPayload` (`enabled=False`, `mode="disabled"`, `context_yaml=""`).
  - Re-export `KnowledgeCatalogService` in `src/app/domain/system/services/__init__.py` alongside existing exports and register `provide_knowledge_catalog_service` on `DomainServiceProvider` in `src/app/ioc/_domain.py`.
- **KC-REQ-04 (`CatalogController`, `LitestarMCP` Tool, Agent Grounding, A2A Skill & Dataplex Toolbox Config)**:
  - Create `CatalogController(PublicController)` in `src/app/domain/system/controllers/_catalog.py` exposing `GET /api/catalog/context` (`mcp_tool="lookup_knowledge_catalog"`) returning `CatalogContextPayload` and `GET /api/catalog/entries` returning `CatalogEntryList`, and register `CatalogController` in `src/app/domain/system/controllers/__init__.py` (`controllers` list).
  - Bind a closure-bound `lookup_catalog_context` tool on `get_coffee_spec_tree()`, inject `catalog_service: KnowledgeCatalogService | None = None` into `AgentOrchestrationService`, parse `use_knowledge_catalog: bool = True` in `CoffeeChatForm`, and populate `sql_phases` (`sql_key="lookup-knowledge-catalog"`) and `search_metrics` (`catalog_enabled`, `catalog_mode`, `catalog_ms`, `catalog_entries`) via `AgentStreamService.adapt(..., final_metadata=final_metadata)`.
  - Add `knowledge_catalog_grounding` skill to `src/app/domain/ai/a2a/_card.py` and add `MCP_TOOLBOX_DATAPLEX_SERVER_NAME = "dataplex-toolbox"` and `build_mcp_toolbox_dataplex_server_config()` to `tools/lib/utils.py`.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `KC-REQ-03` | `2.1` | `behavior_tdd` | `src/app/domain/system/services/_catalog.py`, `src/app/domain/system/services/__init__.py`, `src/app/ioc/_domain.py` | `src/tests/unit/domain/system/test_catalog_service.py` |
| `KC-REQ-04` | `2.2` | `behavior_tdd` | `src/app/domain/system/controllers/_catalog.py`, `src/app/domain/system/controllers/__init__.py`, `src/app/domain/ai/services/_agent.py`, `src/app/domain/chat/schemas/_forms.py`, `src/app/domain/chat/controllers/_helpers.py`, `src/app/domain/chat/controllers/_chat.py`, `src/app/domain/ai/a2a/_card.py`, `tools/lib/utils.py` | `src/tests/unit/domain/system/controllers/test_catalog.py`, `src/tests/unit/domain/ai/a2a/test_a2a.py` |

---

## Implementation Plan

### Phase 1: Runtime Service, Agent Tooling & MCP Surfaces

- [ ] 2.1 Implement `KnowledgeCatalogService` in `src/app/domain/system/services/_catalog.py` and register in `DomainServiceProvider` (`src/app/ioc/_domain.py`)
- [ ] 2.2 Implement `CatalogController` (`mcp_tool="lookup_knowledge_catalog"`), agent turn grounding/telemetry in `AgentOrchestrationService` and `CoffeeChatController`, A2A skill, and Dataplex MCP Toolbox config

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `knowledge-catalog-runtime-and-mcp` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - `KnowledgeCatalogService` uses `select-catalog-column-metadata` from `catalog.sql` when an active `OracleAsyncDriver` is provided and falls back cleanly to the committed snapshot when offline or when `driver=None`.
  - `build_catalog_sql_phase` populates `runtime_ms`, `row_count`, `cache_status`, `binds`, and `parameters` to match `src/resources/telemetry.js::renderSqlPhase`.
- **Newest Discoveries**:
  1. `AgentStreamService.adapt` (`src/app/domain/ai/runtime/_stream.py:50-56, 242-294`) natively accepts `final_metadata` and merges `sql_phases` and `search_metrics` into the terminal `final` SSE frame.
- **Blockers & Unblock Conditions**: Depends on `knowledge-catalog-foundation`.
- **Next Exact Step**: Claim and execute Task `2.1` (`tasks/2.1.md`) after `knowledge-catalog-foundation` completes.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/knowledge-catalog-grounding-demo/research/research_knowledge_catalog_demo_20261012/research.md`
  - `.agents/bundles/knowledge/domains/core-lib-ioc-server-cli.md`
  - `.agents/bundles/knowledge/domains/ai-and-protocols.md`
