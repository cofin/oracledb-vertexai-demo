---
type: Guide
title: AI & Protocols Domain (`domain/ai/`)
description: Native AgentRuntime, AgentOrchestrationService, LitestarMCP 0.15 route-annotated tools and controllers, and LitestarA2A executor
tags:
  - ai
  - mcp
  - a2a
  - gemini-3.8-flash
---

# AI & Protocols Domain (`domain/ai/`)

## 1. Runtime & Protocols (`src/app/domain/ai/runtime/` & `src/app/domain/ai/protocols/_runtime.py`)

- `_types.py`: `FrozenBaseStruct` models (`Content`, `Part`, `FunctionCall`, `FunctionResponse`, `AgentEvent`, `AgentLimits`, `Usage`) with `kw_only=True` and `thought_signature` preservation.
- `_context.py` & `protocols/_runtime.py`: `CallContext` carrying `session_id`, `invocation_id`, `turn`, `state`, and request-scoped `services` (`CoffeeToolContext` via `tool_context`), paired with `SessionStoreProtocol`, `EventStoreProtocol`, and `ModelClientProtocol`.
- `_schema.py`: `GEMINI_ALLOWED_KEYS` and `translate_to_gemini_schema()` converting Python 3.12+ and `msgspec.Struct` annotations into lowercase OpenAPI JSON Schema objects for `google-genai`.
- `_tools.py`: `Tool`, `ToolDeclaration`, `declare()`, and `execute_parallel()` for concurrent tool dispatch with `msgspec.convert(..., strict=False)` argument coercion and strict unknown/missing required argument validation.
- `_spec.py`: `AgentSpec`, `GenerationConfig`, `SpecTree` (specialist `transfer_to_agent` injection), and `fence_context_block()`.
- `_model.py`: `GeminiModelClient` wrapping `google-genai` (`gemini-3.8-flash` on `location="global"`) with thought-part filtering (`thought=True`), fallback `call_<uuid>` IDs when `FunctionCall.id` is omitted, HTTP 429 exponential backoff, and token `Usage` reporting (shared by `AgentRuntime` and `ApexAIController`).
- `_loop.py`: `AgentRuntime.execute_turn()` implementing `TurnBudget` enforcement (`TOOL_LIMIT_EXCEEDED` / `TURN_LIMIT_EXCEEDED`, re-exporting `BudgetExceededError`), OpenTelemetry `SpanManager` tracing, `ACTIVE_SESSION_CONTEXT` prompt fencing, `SpecTree` specialist delegation, and per-spec generation temperature configuration.
- `_store.py`: `OracleSessionStore` (`agent_session`) and `OracleEventStore` (`agent_event`) extending `OracleLoaderService` with named SQL from `src/app/db/sql/ai-runtime.sql` and inline SQLSpec `0.69.0` CLOB string reads (`fetch_lobs=False`).
- `_stream.py`: `AgentStreamService.adapt()`, `AgentStreamFrame`, `to_agent_stream_frame()`, and `build_tool_preview()` converting runtime turns and grounded results into SSE frames (`session`, `tool_call`, `tool_end`, `delta`, `ping`, `final`) while filtering duplicate aggregated `tool_call` and `delta` events.

## 2. Orchestration Services (`src/app/domain/ai/services/`)

`AgentOrchestrationService` (`_agent.py`, supported by session extractors in `_history.py` and `CallContext`-injected tools in `_tools.py`) coordinates each user turn:
1. Checks `CacheService` (`make_response_cache_key`) when no location context or active multi-turn session history (`has_session_context`) is present.
2. Computes a 3072-dimension query embedding (`embedding_purpose="query"`) via `VertexAIService`.
3. Runs `HybridRouteResolver.resolve_turn()` (`hybrid-search-turn` + `hybrid-term-hits`).
4. Dispatches deterministic grounded routes (`PRODUCT_RAG`, `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, `ORDER_STATUS`) via `GroundedRouteService` or invokes `AgentRuntime.execute_turn()` for `GENERAL_CONVERSATION` with `build_coffee_tools()` (`search_products`, `get_product_details`, `find_nearby_stores`, `check_product_availability`, `check_order_status`) and `get_coffee_spec_tree()`.
5. Records Hybrid RRF retrieval telemetry (`search_time_ms`, `embedding_time_ms`, `oracle_time_ms`, `similarity_score`, `result_count`) into `search_metric` via `MetricsService.record_search()` during routing, attaches `ai_ms` and `total_ms` to the terminal SSE `final` frame `search_metrics` payload, and caches eligible stateless responses in `response_cache` via `CacheService`.

## 3. MCP 0.15 & A2A 1.0 (`src/app/domain/ai/mcp/`, `src/app/domain/ai/a2a/`, `src/app/server/mcp/_config.py`)

- **Route-Annotated MCP Tools**: `LitestarMCP` 0.15 discovers `mcp_tool=` handlers directly on domain controllers (`ProductController.get_product` as `get_product`, `StoreController.store_inventory_data` as `get_store_inventory`, and `VectorController.vector_search` as `search_products`).
- **Skills & Prompts (`src/app/domain/ai/mcp/`)**: `CoffeeSkillController` (`_skills.py`), `CoffeePromptController` (`_prompts.py`), and `.agents/skills` (`MCPSkillsConfig` in `src/app/server/mcp/_config.py`) expose MCP skills and prompt templates at `POST /mcp`.
- **A2A (`src/app/domain/ai/a2a/`)**: `CoffeeAgentExecutor`, `build_a2a_call_context`, and `resolve_a2a_user_id` (`_executor.py`) plus `build_agent_card` and `COFFEE_AGENT_CARD` (`_card.py`) serve A2A 1.0 JSON-RPC requests at `POST /a2a` and `GET /.well-known/agent-card.json` using per-request Dishka child containers.
