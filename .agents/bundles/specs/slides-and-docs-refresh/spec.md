---
type: Spec
flow_id: slides-and-docs-refresh
title: Slides, Sphinx Documentation, and Knowledge Bundle Refresh
state: in_progress
plan_revision: 1
plan_commit: null
state_revision: 1
current_task: "5.1"
last_operation: claim_task
operation_targets:
  - slides-and-docs-refresh:5.1
last_verified_checkpoint: null
created_at: 2026-10-12T17:35:00Z
updated_at: 2026-10-12T20:33:50Z
description: Rewrite SLIDES.md to showcase single-query Oracle 26ai Hybrid RRF search (BM25-style lexical ranking + HNSW vector similarity) and off-menu term_hits detection, and update AGENTS.md, README.md, Sphinx docs, Terraform config, and OKF knowledge bundles.
tags:
  - docs
  - slides
  - hybrid-search
  - oracle
parent_prd: coffee-agent-stabilization-and-hybrid-search
research: []
---

# Flow: Slides, Sphinx Documentation, and Knowledge Bundle Refresh

**Flow ID:** `slides-and-docs-refresh`
**Parent PRD:** [`coffee-agent-stabilization-and-hybrid-search`](../coffee-agent-stabilization-and-hybrid-search/spec.md)
**Depends On:** [`oracle-queues`](../oracle-queues/spec.md)

---

## Specification

### Code Analysis Summary

Files examined on `feat/gemini-embeddings` (`@3a3cbd1`):

- `SLIDES.md:1-600` — Still narrates the ADK + `FlashLiteIntentClassifier` two-step pipeline (`Gemini 2.5 Flash-Lite` classifier $\rightarrow$ separate `VECTOR_DISTANCE` search) and describes the off-menu `"Folgers"` problem in Appendix B without showing how in-database lexical term hits + RRF solve it in one round trip.
- `AGENTS.md`, `README.md`, `docs/**/*.md`, `tools/deploy/terraform/cloudrun.tf`, `.agents/bundles/product/{product,tech-stack}.md`, and `.agents/bundles/knowledge/guides/*.md` — Reference removed `ORACLE_ADK_IN_MEMORY`, `sqlspec[adk]`, `src/app/ioc.py` (single file), and `FlashLiteIntentClassifier` (`PL-11`, `PL-15`).

### Relevant Patterns

- [Oracle Database Guide](../../knowledge/guides/oracle-database.md) — Named SQL, HNSW `FETCH APPROX`, and Oracle Text `MULTI_COLUMN_DATASTORE` conventions.
- [Agentic AI Runtime Guide](../../knowledge/guides/agentic-ai-runtime.md) — Native `AgentRuntime`, `OracleSessionStore`/`OracleEventStore`, MCP, and A2A architecture.

### Requirements

- **REQ-11 (Slides, Documentation, Terraform & OKF Knowledge Synchronization)**:
  - Update `SLIDES.md` so the architecture flow, SQL deep-dive slides, latency breakdown, and Appendix B (`"Folgers"` off-menu guard) showcase **one Oracle 26ai Hybrid Search query (`hybrid-search-turn`)** combining BM25-style lexical ranking (Oracle Text `CONTAINS`/`SCORE` with `MULTI_COLUMN_DATASTORE`, plus a note on Oracle 26ai `VECTOR(..., SPARSE)` for external BM25/SPLADE encoders) and `VECTOR_DISTANCE` (`FETCH APPROX`) via **Reciprocal Rank Fusion (RRF, $k=60$)**—eliminating the pre-router LLM call and extra retrieval round trip.
  - Update `AGENTS.md`, `README.md`, `docs/**` (verifying all `literalinclude` anchors and `sphinx-build -W`), `tools/deploy/terraform/cloudrun.tf`, `.agents/bundles/product/{product,tech-stack}.md`, and `.agents/bundles/knowledge/**` (adding `.agents/bundles/knowledge/guides/hybrid-search.md`).

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `REQ-11` | `5.1` | `documentation_validation` | `SLIDES.md` | `SLIDES.md` structure & SQL consistency check |
| `REQ-11` | `5.2` | `documentation_validation` | `AGENTS.md`, `README.md`, `docs/**`, `tools/deploy/terraform/cloudrun.tf`, `.agents/bundles/product/**`, `.agents/bundles/knowledge/**` | `uv run sphinx-build -W -b html docs docs/_build/html` |

---

## Implementation Plan

### Phase 1: Presentation Narrative & Documentation Synchronization

- [x] 5.1 Rewrite `SLIDES.md` for single-query Oracle 26ai Hybrid RRF routing, BM25-style lexical ranking, and `term_hits` off-menu detection
- [ ] 5.2 Synchronize `AGENTS.md`, `README.md`, Sphinx `docs/**`, `cloudrun.tf`, and `.agents/bundles/{product,knowledge}/**`

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `slides-and-docs-refresh` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - `SLIDES.md` describes the lexical leg accurately as **"BM25-style lexical ranking (Oracle Text `CONTAINS`/`SCORE`)"** and notes Oracle 26ai `VECTOR(..., SPARSE)` for external BM25/SPLADE sparse encoders.
- **Newest Discoveries**:
  1. `SLIDES.md`, `AGENTS.md`, `docs/**`, and `cloudrun.tf` still reference `FlashLiteIntentClassifier` and `ORACLE_ADK_IN_MEMORY` (`PL-11`, `PL-15`).
- **Blockers & Unblock Conditions**: Depends on `oracle-queues`.
- **Next Exact Step**: Claim and execute Task `5.1` (`tasks/5.1.md`) after `oracle-queues` completes.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/hybrid-rrf-retrieval/research/research_oracle_hybrid_rrf_20261012/research.md`
  - `.agents/bundles/knowledge/guides/oracle-database.md`
  - `.agents/bundles/knowledge/guides/agentic-ai-runtime.md`
