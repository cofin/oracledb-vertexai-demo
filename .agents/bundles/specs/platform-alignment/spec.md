---
type: Spec
flow_id: platform-alignment
title: Settings, DI, Services, LitestarMCP 0.15, and Security Alignment
state: active
plan_revision: 1
plan_commit: feecf59
state_revision: 3
current_task: "3.3"
last_operation: 20261012T193300Z-flow-executor-complete-3-2-00
operation_targets:
  - "3.2"
  - "3.3"
last_verified_checkpoint: 7d190aa
created_at: 2026-10-12T17:35:00Z
updated_at: 2026-10-12T19:33:00Z
description: Align the repository with Litestar reference platform conventions by modularizing lib/settings/ and ioc/, splitting monolithic domain services into private _*.py modules, dropping sqlspec[adk], upgrading to litestar-mcp>=0.15.0 (SkillController, PromptController, TurnBudget, AgentStreamFrame, SpanManager), hardening CSRF and optional MCP_API_KEY security, and enforcing Ruff TID251 banned-api rules.
tags:
  - refactor
  - architecture
  - litestar
  - mcp
  - security
parent_prd: coffee-agent-stabilization-and-hybrid-search
research: []
---

# Flow: Settings, DI, Services, LitestarMCP 0.15, and Security Alignment

**Flow ID:** `platform-alignment`
**Parent PRD:** [`coffee-agent-stabilization-and-hybrid-search`](../coffee-agent-stabilization-and-hybrid-search/spec.md)
**Depends On:** [`hybrid-rrf-retrieval`](../hybrid-rrf-retrieval/spec.md)

---

## Specification

### Code Analysis Summary

Files examined on `feat/gemini-embeddings` (`@3a3cbd1`):

- `pyproject.toml:8-48, 224-230` — Still declares `sqlspec[adk,litestar,oracledb,performance]>=0.65.0` (which pulls in `google-adk`), leaves `google-genai` and `tenacity` as undeclared transitive dependencies, pins `litestar-mcp[a2a,opentelemetry]>=0.14.0`, and contains stale `pydantic` deprecation filters (`PL-03`).
- `src/app/lib/settings.py:1-583` — Monolithic 583-line settings file with deprecated `ORACLE_ADK_IN_MEMORY` naming.
- `src/app/lib/log/_middleware.py:13, 93` — Calls `settings = get_settings()` at module import time (`PL-06`) and accesses `message["headers"]` directly on `http.response.start`, raising `KeyError` when ASGI responses omit `headers` (`PL-10`).
- `src/app/ioc.py:1-147`, `src/app/domain/products/services/services.py:1-460`, `src/app/domain/system/services/services.py:1-195` — Monolithic provider and service modules instead of modular `src/app/ioc/{_config,_database,_ai,_domain}.py` and private `_*.py` service modules re-exported via `__init__.py`.
- `src/app/domain/ai/runtime/*` & `src/app/domain/ai/mcp/*` — Hand-rolls primitives (`TurnBudget`, `AgentStreamFrame`, `SkillController`, `PromptController`, `SpanManager`) that are now first-party in `litestar-mcp[a2a,google-genai,opentelemetry]>=0.15.0`.
- `src/app/server/{asgi,core,plugins}.py` — `PublicController` disables CSRF across all routes (`exclude_from_csrf=True`, `PL-08`), `/mcp` and `/a2a` lack optional `MCP_API_KEY` header enforcement, `GET /health` is missing alongside `GET /api/system/health`, and `server/asgi.py` carries redundant sys.path/env boilerplate.

### Relevant Patterns

- [Dishka Dependency Injection](../../knowledge/patterns/dishka-di.md) — Provider modules in `src/app/ioc/` must never use `from __future__ import annotations`.
- [SQLSpec Services](../../knowledge/patterns/sqlspec-services.md) — Private `_*.py` service implementation modules re-exported cleanly in `domain/<feature>/services/__init__.py`.

### Requirements

- **REQ-08 (Dependencies, Modular Settings, Modular DI & Service Split)**:
  - Update `pyproject.toml`: drop `adk` from `sqlspec[...]`, add explicit `google-genai>=1.68.0` and `tenacity>=9.0.0`, upgrade to `litestar-mcp[a2a,google-genai,opentelemetry]>=0.15.0`, and remove stale ADK `filterwarnings`.
  - Split `src/app/lib/settings.py` into `src/app/lib/settings/{__init__,_env,_app,_server,_database,_ai,_maps,_log,_otel}.py` while keeping `from app.lib.settings import Settings, get_settings, reload_settings` backwards-compatible (`ORACLE_AGENT_IN_MEMORY` primary env var with `ORACLE_ADK_IN_MEMORY` fallback).
  - Fix `src/app/lib/log/_middleware.py` to resolve settings lazily inside `__init__` and use `list(message.get("headers", []))`.
  - Split `src/app/domain/products/services/services.py` into `_products.py`, `_embedding.py`, `_stores.py`, `_inventory.py`, `_maps.py` and `src/app/domain/system/services/services.py` into `_health.py` and `_cache.py`.
  - Split `src/app/ioc.py` into `src/app/ioc/{__init__,_config,_database,_ai,_domain}.py` (zero `from __future__ import annotations`).
- **REQ-09 (LitestarMCP 0.15 Primitives, Security Boundaries & Ruff `TID251` Gates)**:
  - Adopt `litestar-mcp>=0.15.0` primitives (`SkillController`, `PromptController`, `TurnBudget`, `AgentStreamFrame`, `SpanManager`) alongside `domain/ai/protocols/` and typed `CoffeeToolContext` / `RunContextRegistry`.
  - Create `src/app/lib/security.py::build_security_config` and `src/app/server/mcp/_config.py::build_mcp_config`: re-enable CSRF protection (`opt={"exclude_from_csrf": False}`) on browser cookie-session POST routes in `CoffeeChatController`, keep `/mcp` and `/a2a` CSRF-exempt (`exclude_from_csrf=True`), and support optional `MCP_API_KEY` header authentication (`X-API-Key`).
  - Add root `GET /health` alias, simplify `src/app/server/asgi.py`, and configure Ruff `TID251` `banned-api` rules (`orjson`, `google.adk`, `litestar.plugins.htmx`).

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `REQ-08` | `3.1` | `characterization` | `pyproject.toml`, `src/app/lib/settings/**`, `src/app/lib/log/_middleware.py` | `src/tests/unit/app/lib/test_settings.py`, `src/tests/unit/app/lib/test_log_middleware.py` |
| `REQ-08` | `3.2` | `characterization` | `src/app/domain/products/services/**`, `src/app/domain/system/services/**`, `src/app/ioc/**`, `src/app/lib/di.py`, `src/app/lib/service.py`, `src/app/cli/utils.py` | `src/tests/unit/app/test_ioc_and_services.py` |
| `REQ-09` | `3.3` | `behavior_tdd` | `src/app/domain/ai/protocols/**`, `src/app/domain/ai/mcp/**`, `src/app/domain/ai/runtime/**`, `src/app/domain/ai/services/agent_service.py` | `src/tests/unit/app/domain/ai/test_mcp_controllers.py` |
| `REQ-09` | `3.4` | `behavior_tdd` | `src/app/lib/security.py`, `src/app/server/mcp/_config.py`, `src/app/server/plugins.py`, `src/app/server/core.py`, `src/app/server/asgi.py`, `src/app/domain/chat/controllers/_chat.py`, `src/app/domain/system/controllers/_system.py`, `pyproject.toml` | `src/tests/unit/app/server/test_security_and_mcp.py` |

---

## Implementation Plan

### Phase 1: Modular Settings, Dependencies, Services & Dishka DI Package

- [x] 3.1 Drop `sqlspec[adk]`, upgrade `litestar-mcp>=0.15.0`, split `src/app/lib/settings/` package, and fix `log/_middleware.py`
- [x] 3.2 Split `products/services/` and `system/services/` into private `_*.py` modules and modularize `src/app/ioc/`

### Phase 2: LitestarMCP 0.15 Primitives, Security Hardening & Lint Gates

- [~] 3.3 Adopt `litestar-mcp>=0.15.0` `SkillController`, `PromptController`, `TurnBudget`, `AgentStreamFrame`, `SpanManager`, and `domain/ai/protocols/`
- [ ] 3.4 Implement `build_security_config`, `build_mcp_config`, chat CSRF opt-in, optional `MCP_API_KEY` auth, `GET /health`, and Ruff `TID251` gates

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `platform-alignment` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - Split `lib/settings/` and `ioc/` into cohesive sub-modules while preserving top-level imports (`app.lib.settings`, `app.ioc`).
  - Browser cookie-session chat POST endpoints opt into CSRF (`exclude_from_csrf: False`); `/mcp` and `/a2a` stay CSRF-exempt with optional `MCP_API_KEY` header authentication.
- **Newest Discoveries**:
  1. `src/app/lib/log/_middleware.py` calls `get_settings()` at import time and raises `KeyError: 'headers'` on headerless ASGI start messages (`PL-06`, `PL-10`).
  2. `PublicController` sets `exclude_from_csrf=True` on all routes in `litestar-security` 0.6.0 (`PL-08`).
- **Blockers & Unblock Conditions**: Depends on `hybrid-rrf-retrieval`.
- **Next Exact Step**: Claim and execute Task `3.1` (`tasks/3.1.md`) after `hybrid-rrf-retrieval` completes.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/coffee-agent-stabilization-and-hybrid-search/research/research_codebase_audit_and_reference_patterns_20261012/research.md`
  - `.agents/bundles/knowledge/patterns/dishka-di.md`
  - `.agents/bundles/knowledge/guides/architecture.md`
