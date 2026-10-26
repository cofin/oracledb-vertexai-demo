---
type: Spec
flow_id: knowledge-catalog-demo-ux-and-docs
title: Knowledge Catalog Demo UI Toggle, Telemetry Inspector, Slides, and Documentation
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-10-12T18:31:00Z
updated_at: 2026-10-12T18:42:00Z
description: Add the Knowledge Catalog Grounding (ON/OFF) toggle in chat.html.j2 and main.js, add the K (Knowledge Catalog) telemetry chip and Context X-Ray popover details in telemetry.js, and document the Knowledge Catalog + Oracle 26ai ANNOTATIONS + OKF v0.2 architecture and "Breaking the Context Ceiling" demo script across SLIDES.md, .agents/bundles/knowledge/architecture/knowledge-catalog.md, AGENTS.md, README.md, and docs/.
tags:
  - feature
  - knowledge-catalog
  - ui
  - telemetry
  - docs
parent_prd: knowledge-catalog-grounding-demo
research: []
---

# Flow: Knowledge Catalog Demo UI Toggle, Telemetry Inspector, Slides, and Documentation

**Flow ID:** `knowledge-catalog-demo-ux-and-docs`
**Parent PRD:** [`knowledge-catalog-grounding-demo`](../knowledge-catalog-grounding-demo/spec.md)
**Depends On:** [`knowledge-catalog-runtime-and-mcp`](../knowledge-catalog-runtime-and-mcp/spec.md)

---

## Specification

### Code Analysis Summary

Files examined:

- `src/app/domain/web/templates/pages/chat.html.j2:30-108` — Renders the left `chat-sidebar` (persona picker, `#metrics-badges`, clear chat button) and `#chat-form` hidden inputs (`persona`, `location_consent`, `latitude`, `longitude`, `accuracy`).
- `src/resources/main.js:16-95` — Initializes `initPersonaPicker()` and handles delegated click events on `document.body` (`[data-use-location]`, `[data-telemetry-close]`, `[data-clear-chat]`, `[data-telemetry-detail]`).
- `src/resources/telemetry.js:6-343` — Renders sidebar metrics (`renderMetrics`) and per-message telemetry chips (`renderMessageTelemetry`) that open `[data-ui-popover-root='chat']` (`showTelemetryPopover` + `renderSqlPhase`).
- `SLIDES.md:1-241`, `.agents/bundles/knowledge/index.md:1-40`, `AGENTS.md:1-190`, `README.md`, `docs/concepts/agent-flow.md`, `docs/mcp-antigravity.md`, `docs/reference/cli.md`, `docs/reference/api.md` — Walkthrough slides, OKF v0.2 knowledge guides, and Sphinx documentation.

### Relevant Patterns

- [Architecture Patterns](../../knowledge/patterns/architecture.md) — Server-rendered Jinja templates (`chat.html.j2`) paired with modular ES modules in `src/resources/`.
- [OKF v0.2 Bundles](../../knowledge/index.md) — Durable engineering guides live under `.agents/bundles/knowledge/architecture/` with valid OKF v0.2 frontmatter.

### Requirements

- **KC-REQ-05 (Chat UI Grounding Toggle & `K` Telemetry Chip)**:
  - Add a **Knowledge Catalog Grounding (`ON` / `OFF`)** control in the left sidebar of `src/app/domain/web/templates/pages/chat.html.j2` (`data-kc-toggle`, `aria-pressed="true"`, `data-kc-status`) and a hidden `<input type="hidden" name="use_knowledge_catalog" value="true" data-kc-input>` inside `<form data-chat-form="true">`.
  - Wire `[data-kc-toggle]` click handling in `src/resources/main.js` so toggling between **Grounding ON** and **Grounding OFF** updates `[data-kc-input]` and `[data-kc-status]` (`LookupContext + Oracle 26ai Annotations active` vs `Ungrounded mode (catalog context omitted)`).
  - Extend `renderMetrics` and `renderMessageTelemetry` in `src/resources/telemetry.js` to inspect `phasesFor(payload, "lookup-knowledge-catalog")` and `metrics.catalog_enabled` / `metrics.catalog_ms`, rendering a clickable **`K` (`Knowledge Catalog`)** telemetry chip that opens the telemetry popover showing matched entry URIs (`oracle:cymbal-coffee:product`, `oracle:cymbal-coffee:store`, `oracle:cymbal-coffee:store_product_inventory`), active Oracle 26ai `Privacy` and `Data_Role` rules (`store.latitude/longitude`), steward guidelines, and the `dataplex.googleapis.com/v1:lookupContext` YAML bundle.
- **KC-REQ-06 (Presentation Slides, OKF Knowledge Guide & Sphinx Documentation)**:
  - Create `.agents/bundles/knowledge/architecture/knowledge-catalog.md` and link it in `.agents/bundles/knowledge/index.md` and `AGENTS.md`.
  - Add slides to `SLIDES.md` covering the combined **Oracle 26ai `ANNOTATIONS` + Google Cloud Knowledge Catalog `lookupContext` + OKF v0.2** grounding architecture and the **"Breaking the Context Ceiling"** presenter walkthrough.
  - Update `README.md`, `docs/concepts/agent-flow.md`, `docs/mcp-antigravity.md`, `docs/reference/cli.md`, and `docs/reference/api.md` to document `uv run coffee sync-catalog`, `GET /api/catalog/context` (`mcp_tool="lookup_knowledge_catalog"`), `GET /api/catalog/entries`, and the Dataplex MCP Toolbox server.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `KC-REQ-05` | `3.1` | `behavior_tdd` | `src/app/domain/web/templates/pages/chat.html.j2`, `src/resources/main.js`, `src/resources/telemetry.js` | `src/tests/unit/domain/web/test_chat_catalog_ui.py` |
| `KC-REQ-06` | `3.2` | `documentation_validation` | `SLIDES.md`, `.agents/bundles/knowledge/architecture/knowledge-catalog.md`, `.agents/bundles/knowledge/index.md`, `AGENTS.md`, `README.md`, `docs/concepts/agent-flow.md`, `docs/mcp-antigravity.md`, `docs/reference/cli.md`, `docs/reference/api.md` | `src/tests/unit/domain/web/test_chat_catalog_ui.py` |

---

## Implementation Plan

### Phase 1: Interactive Demo UI, Telemetry Chip & Documentation

- [ ] 3.1 Add Knowledge Catalog Grounding (`ON`/`OFF`) toggle in `chat.html.j2` + `main.js` and `K` (`Knowledge Catalog`) telemetry chip in `telemetry.js`
- [ ] 3.2 Add Knowledge Catalog architecture & "Breaking the Context Ceiling" demo slides to `SLIDES.md`, create `.agents/bundles/knowledge/architecture/knowledge-catalog.md`, and update `AGENTS.md`, `README.md`, and `docs/`

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `knowledge-catalog-demo-ux-and-docs` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - Reuse `telemetry.js::renderSqlPhase` and `showTelemetryPopover` for the `K` (`Knowledge Catalog`) chip so clicking `K` opens the existing accessible dialog with zero duplicate modal code.
- **Newest Discoveries**:
  1. Delegated click handlers for chat controls live in `src/resources/main.js:59-87` rather than `src/resources/chat-stream.js`.
- **Blockers & Unblock Conditions**: Depends on `knowledge-catalog-runtime-and-mcp`.
- **Next Exact Step**: Claim and execute Task `3.1` (`tasks/3.1.md`) after `knowledge-catalog-runtime-and-mcp` completes.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/knowledge-catalog-grounding-demo/research/research_knowledge_catalog_demo_20261012/research.md`
  - `.agents/bundles/knowledge/architecture/system-architecture.md`
