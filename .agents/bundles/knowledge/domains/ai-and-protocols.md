---
type: Guide
title: AI & Protocols Domain (`domain/ai/`)
description: Native AgentRuntime, AgentOrchestrationService, LitestarMCP 0.15 controllers, and LitestarA2A executor
tags:
  - ai
  - mcp
  - a2a
  - gemini-3.8-flash
---

# AI & Protocols Domain (`domain/ai/`)

## 1. Runtime Package (`src/app/domain/ai/runtime/`)

- `_types.py`: `BaseStruct` models (`Content`, `Part`, `FunctionCall`, `FunctionResponse`, `AgentEvent`, `Usage`, `EventActions`).
- `_context.py`: `CallContext` carrying `session_id`, `invocation_id`, `turn`, `state`, `request_id`, and request-scoped `services` (`CoffeeToolContext`).
- `_tools.py`: `Tool`, `declare()`, and `execute_parallel()` for concurrent tool dispatch with `msgspec.convert(..., strict=False)` argument coercion and strict unknown/missing required argument validation.
- `_model.py`: `GeminiModelClient` wrapping `google-genai` (`gemini-3.8-flash`) with thought-part filtering (`thought=True`), fallback `call_<uuid>` IDs when `FunctionCall.id` is omitted, HTTP 429 exponential backoff, and token usage reporting.
- `_loop.py`: `AgentRuntime.execute_turn()` implementing step budgets (`TurnBudget`), specialist delegation (`SpecTree`), per-spec generation temperature overrides, and event persistence.
- `_store.py`: `OracleSessionStore` (`agent_session`) and `OracleEventStore` (`agent_event`) using named SQL from `src/app/db/sql/ai-runtime.sql`.
- `_stream.py`: `AgentStreamService` converting runtime turns and grounded results into SSE frames (`session`, `tool_call`, `tool_end`, `delta`, `ping`, `final`) while filtering duplicate aggregated `tool_call` and `delta` events.

## 2. Orchestration Service (`src/app/domain/ai/services/`)

`AgentOrchestrationService` coordinates each user turn:
1. Checks `CacheService` when no location context or active multi-turn session history is present.
2. Computes a 3072-dimension query embedding (`embedding_purpose="query"`).
3. Runs `HybridRouteResolver.resolve_turn()` (`hybrid-search-turn` + `hybrid-term-hits`).
4. Dispatches deterministic grounded routes (`PRODUCT_RAG`, `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, `ORDER_STATUS`) via `GroundedRouteService` or invokes `AgentRuntime.execute_turn()` for `GENERAL_CONVERSATION` with closure-bound tools (`search_products`, `get_product_details`, `find_nearby_stores`, `check_product_availability`, `check_order_status`).
5. Records `search_metrics` (including `ai_ms`) via `MetricsCollector` and caches eligible stateless responses.

## 3. MCP 0.15 & A2A 1.0 (`src/app/domain/ai/mcp/` & `src/app/domain/ai/a2a/`)

- `CoffeeMCPController` (`_controllers.py`): Route-annotated MCP tools (`search_products`, `find_nearby_stores`, `check_store_inventory`, `ask_coffee_sommelier`).
- `CoffeeSkillController` (`_skills.py`) & `CoffeePromptController` (`_prompts.py`): Expose MCP skills and prompt templates.
- `CoffeeAgentExecutor` (`a2a/_executor.py`) & `build_agent_card` (`a2a/_card.py`): Bridge A2A 1.0 JSON-RPC requests into `AgentOrchestrationService` using a per-request Dishka child container.
