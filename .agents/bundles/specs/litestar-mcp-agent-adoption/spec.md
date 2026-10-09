---
type: Spec
id: litestar-mcp-agent-adoption
title: Adopt First-Party LitestarMCP Agent Runtime, SkillController, and PromptController
description: Architecture specification for upgrading to litestar-mcp v0.15.0+, replacing hand-rolled domain/ai/runtime primitives with upstream AgentRuntime, GoogleGenAIClient, and SkillController while retaining Oracle 26ai SQLSpec persistence.
state: ready
parent_prd: null
tags:
  - spec
  - litestar-mcp
  - agent-runtime
  - gemini-3.8-flash
  - oracle-26ai
  - skill-controller
  - a2a
---

# Architecture Specification: Upstream LitestarMCP Agent Runtime Adoption

*Spec ID: `litestar-mcp-agent-adoption`*
*Status: Planned*
*Target Stack: Litestar 2.24+, litestar-mcp 0.15.0+, litestar-security 0.6.0+, google-genai 2.28+, SQLSpec 0.65+, Oracle 26ai*

---

## 1. Executive Summary & North Star

Following the release of [`cofin/litestar-mcp#97`](https://github.com/cofin/litestar-mcp/pull/97) (v0.15.0+), `litestar-mcp` ships first-class agent runtime abstractions, class-based MCP controllers (`SkillController`, `PromptController`), standardized SSE streaming (`AgentStreamFrame`, `iter_agent_stream`), native Vertex AI model clients (`GoogleGenAIClient`), and security context propagation (`ToolContext`).

This specification defines the migration path for **Cymbal Coffee** to adopt these upstream abstractions, allowing us to:
1. **Debloat Hand-Rolled Subsystems**: Delete ~1,200 lines of custom runtime in `src/app/domain/ai/runtime/` (`_loop.py`, `_model.py`, `_stream.py`, `_tools.py`, `_types.py`).
2. **Standardize on `SkillController`**: Unify product search, inventory lookup, and store recommendations into a cohesive `CoffeeSkillController(SkillController)`.
3. **Adopt Upstream `GoogleGenAIClient`**: Replace custom chunk-parsing logic with upstream's native thought-token extraction and `httpx2` client pooling.
4. **Preserve Oracle 26ai ACID Persistence**: Maintain our core differentiator (`OracleSessionStore`, `OracleEventStore`, `AGENT_SESSION`, `AGENT_EVENT`), adapting it cleanly to upstream's `AgentMessage` and `TurnRequest` / `TurnResponse` contracts.
5. **Prepare for `litestar-queues` Background Execution**: Establish a clean architecture ready for `QueuedAgentChatController` when long-running agent workflows are queued.

---

## 2. Component Boundaries & Architecture

```text
HTTP / SSE Clients (Chat UI, HTMX)
         │
         ▼
CoffeeChatController (PublicController)
         │
         ▼
AgentOrchestrationService (REQUEST scope)
         │
         ├─► Intent Classification (FlashLiteIntentClassifier)
         ├─► Session History Adapter (OracleSessionStore, OracleEventStore -> AgentMessage)
         ▼
AgentRuntime.stream_turn() (litestar-mcp APP scope)
         │
         ├─► TurnBudget Enforcement (BudgetExceededError)
         ├─► Model Interaction (litestar_mcp.GoogleGenAIClient -> gemini-3.8-flash)
         ├─► Tools & Skills (CoffeeSkillController: search_coffee, find_stores)
         ▼
AgentStreamFrame (litestar-mcp typed SSE frames)
         │
         ▼
SSE Wire Output: session -> tool_call -> tool_result -> delta -> complete
```

---

## 3. Work Breakdown Structure (Tasks 1–5)

| Task ID | Worksheet Path | Scope & Deliverable | Verification Strategy |
| :--- | :--- | :--- | :--- |
| **task-1** | `tasks/01_upgrade_dep_and_model_client.md` | Upgrade `litestar-mcp[a2a]` dependency in `pyproject.toml`, replace `GeminiModelClient` with upstream `litestar_mcp.GoogleGenAIClient` in `src/app/ioc.py`, and delete `_model.py`. | `characterization` |
| **task-2** | `tasks/02_skill_controller_coffee_tools.md` | Implement `CoffeeSkillController(SkillController)`, consolidate coffee tools, register on `LitestarMCP`, and delete `src/app/domain/ai/runtime/_tools.py`. | `behavior_tdd` |
| **task-3** | `tasks/03_agent_runtime_and_oracle_adapter.md` | Adapt `OracleSessionStore` and `OracleEventStore` to upstream `AgentMessage`, wire upstream `AgentRuntime` with `TurnBudget`, and delete `_loop.py` & `_spec.py`. | `behavior_tdd` |
| **task-4** | `tasks/04_sse_streaming_and_chat_controller.md` | Adopt `AgentStreamFrame` and `iter_agent_stream`, refactor `CoffeeChatController`, and delete `_stream.py` & `_types.py`. | `behavior_tdd` |
| **task-5** | `tasks/05_multi_protocol_verification_and_cleanup.md` | Validate end-to-end A2A discovery (`/.well-known/agent-card.json`), MCP dispatch (`POST /mcp`), and chat SSE streaming. Run full aggregate gates. | `integration_acceptance` |

---

## 4. Acceptance Criteria & Quality Gates

- [ ] All 5 task worksheets are decision-complete with exact signatures and file paths.
- [ ] No application source files modified until implementation phase begins.
- [ ] Every task maps to exactly one verification strategy with initial and final evidence.
- [ ] Upstream `litestar_mcp` types replace duplicated hand-rolled primitives.
- [ ] Real Oracle 26ai database integration tests pass with zero regressions.
- [ ] `make lint` passes with 0 errors across pre-commit, mypy, pyright, and markdownlint.
