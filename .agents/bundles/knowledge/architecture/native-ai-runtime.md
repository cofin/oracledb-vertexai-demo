---
type: Guide
title: Native Agentic AI Runtime
description: Re-entrant AgentRuntime, GeminiModelClient, SpecTree delegation, Oracle 26ai persistence, SSE streaming, MCP 0.15, and A2A 1.0
tags:
  - ai
  - agent-runtime
  - gemini-3.8-flash
  - mcp
  - a2a
---

# Native Agentic AI Runtime

The AI subsystem in `src/app/domain/ai/` provides a native, zero-overhead agent runtime built directly on `google-genai` (`gemini-3.8-flash`), `msgspec`, and SQLSpec Oracle 26ai stores.

## 1. Execution Flow

```text
CoffeeChatController (POST /api/chat/stream)
  -> AgentOrchestrationService (Scope.REQUEST)
     1. Response cache lookup (skipped when location context is active)
     2. VertexAIService.get_text_embedding(..., embedding_purpose="query")
     3. HybridRouteResolver.resolve_turn() -> single-query Oracle 26ai Hybrid RRF
     4. Grounded deterministic path (PRODUCT_RAG, STORE_LOCATION, PRODUCT_AVAILABILITY, ORDER_STATUS)
        OR Native AgentRuntime.execute_turn() (GENERAL_CONVERSATION with closure-bound tools)
  -> AgentStreamService.stream() -> SSE frames (session, tool_call, tool_end, delta, ping, final)
```

## 2. Core Primitives (`src/app/domain/ai/runtime/`)

- **Wire Types (`_types.py`)**: `msgspec.Struct` models (`Content`, `Part`, `FunctionCall`, `FunctionResponse`, `AgentEvent`, `Usage`) with camelCase wire aliasing and `kw_only=True`.
- **Schema Translator (`_schema.py`)**: `translate_to_gemini_schema()` converts Python 3.12+ and `msgspec.Struct` annotations into Gemini-compatible OpenAPI schemas.
- **Tool Registry & Parallel Dispatch (`_tools.py`)**: `declare()` inspects tool signatures, coerces LLM arguments via `msgspec.convert(..., strict=False)`, and `execute_parallel()` runs tool calls concurrently with `asyncio.gather()`.
- **Model Client (`_model.py`)**: `GeminiModelClient` wraps `genai.Client` (`gemini-3.8-flash` on `VERTEX_AI_CHAT_LOCATION="global"`), suppresses internal `thought=True` parts, retries transient HTTP 429 errors with exponential backoff, and tracks token usage.
- **Re-Entrant Execution Loop (`_loop.py`)**: `AgentRuntime.execute_turn()` enforces `TurnBudget` step limits (`TOOL_LIMIT_EXCEEDED` / `TURN_LIMIT_EXCEEDED`), supports `SpecTree` specialist delegation with `<ACTIVE_SESSION_CONTEXT>` prompt fencing, and persists events atomically.
- **Oracle Persistence (`_store.py`)**: `OracleSessionStore` (`agent_session`) and `OracleEventStore` (`agent_event`) persist multi-turn conversation history via named SQL in `src/app/db/sql/ai-runtime.sql`.
- **SSE Stream Adapter (`_stream.py`)**: `AgentStreamService` drains events asynchronously, emits 5-second `ping` keep-alives, and emits a terminal `final` frame carrying the complete `ChatResponse` telemetry contract.

## 3. LitestarMCP 0.15 & LitestarA2A Integration

- **MCP (`src/app/domain/ai/mcp/`)**: Mounted at `POST /mcp` with `CoffeeMCPController` (`mcp_tool=` route annotations), `CoffeeSkillController`, and `CoffeePromptController`.
- **A2A (`src/app/domain/ai/a2a/`)**: Mounted at `POST /a2a` with `CoffeeAgentExecutor` and `GET /.well-known/agent-card.json` (`build_agent_card`).
- **Authentication**: Protected by constant-time `hmac.compare_digest` bearer/header checks when `MCP_API_KEY` is set.
