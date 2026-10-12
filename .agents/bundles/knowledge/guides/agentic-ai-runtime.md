---
type: Guide
title: Native Agentic AI Runtime Guide
description: Architecture, execution loop, streaming SSE adapter, Oracle 26ai persistence, MCP, and A2A protocol integration
tags:
  - ai
  - agent-runtime
  - gemini-3.8-flash
  - mcp
  - a2a
  - oracle-26ai
---

# Native Agentic AI Runtime Guide

This guide documents the native dynamic agentic intelligence platform in `src/app/domain/ai/`, powered by Gemini 3.8 Flash, Oracle Database 26ai, LitestarMCP, and LitestarA2A.

## 1. High-Level Architecture

The AI subsystem is structured as a generic, decoupled domain service:

```text
HTTP / SSE Clients (Chat UI, HTMX)
         │
         ▼
CoffeeChatController (PublicController)
         │
         ▼
AgentOrchestrationService (REQUEST scope)
         │
         ├─► Hybrid RRF Turn Routing (HybridRouteResolver -> hybrid-search-turn + hybrid-term-hits)
         ├─► Grounded Route Composers (PRODUCT_RAG, STORE_LOCATION, PRODUCT_AVAILABILITY, ORDER_STATUS)
         ├─► Session / Context (CallContext, OracleSessionStore, OracleEventStore)
         ▼
AgentRuntime.run_stream() (APP scope, GENERAL_CONVERSATION fallback)
         │
         ├─► Prompt Fencing & Specialist Delegation (SpecTree, AgentSpec)
         ├─► Model Interaction (GeminiModelClient -> google-genai -> gemini-3.8-flash)
         ├─► Dynamic Tool Dispatch (Tool, declare(), execute_parallel())
         ▼
AgentStreamService.stream()
         │
         ▼
SSE Frames: session -> tool_call -> tool_end -> delta -> ping -> final (full ChatResponse payload)
```

Simultaneously, the same domain services and tools are exposed machine-to-machine via:
- **Model Context Protocol (`LitestarMCP`)**: Stateless `POST /mcp` with skill definitions and tool declarations.
- **Agent-to-Agent Protocol (`LitestarA2A`)**: Standard JSON-RPC at `POST /a2a` with public discovery at `GET /.well-known/agent-card.json`.

---

## 2. Core Primitives & Wire Contracts (`app.domain.ai.runtime`)

All internal message and event structures use zero-copy, high-performance `msgspec.Struct`:

- `Content(role: "user" | "model", parts: list[Part])`: Native Gemini-compatible conversation turn representation.
- `Part(text, function_call, function_response, thought)`: Atomic payload element supporting text deltas, tool invocations, and structured outputs.
- `FunctionCall(id, name, args)` / `FunctionResponse(id, name, response)`: Strict tool execution wire formats.
- `AgentEvent(agent, content, partial, actions, usage, finish_reason)`: Streaming event emitted by the runtime loop.
- `CallContext(session_id, invocation_id, turn, state, request_id)`: Per-turn invocation context passed to closure-bound tool executions.

Schema conversion from Python type annotations or msgspec structures to Gemini JSON schema is handled by `translate_to_gemini_schema()`, generating compliant OpenAPI-style schemas.

---

## 3. Tool Declaration & Parallel Dispatch

Tools are declared using `declare(handler, name=..., description=...)`:

```python
from app.domain.ai.runtime import CallContext, declare


async def find_nearby_stores(ctx: CallContext, query: str, limit: int = 3) -> dict[str, Any]:
    """Find nearby coffee shops matching query.

    Args:
        ctx: Active turn invocation context.
        query: Search location or query string.
        limit: Maximum results to return.
    """
    store_service: StoreService = ctx.state["store_service"]
    stores = await store_service.search_nearby(query, limit=limit)
    return {"stores": [s.to_dict() for s in stores]}

store_tool = declare(find_nearby_stores)
```

Key invariants:
- **Argument Coercion**: `Tool.invoke()` uses `msgspec.convert(..., strict=False)` to validate model arguments against parameter type hints.
- **Parallel Execution**: `execute_parallel(tools, calls, ctx)` executes independent tool calls concurrently via `asyncio.gather()`.
- **Request-Scoped Isolation**: Tools access request-scoped dependencies (database driver, domain services) through `ctx.state` without global state.

---

## 4. Model Client & Gemini 3.8 Flash Acceleration

`GeminiModelClient` wraps the `google-genai` client targeting `gemini-3.8-flash`:

- **Thought Token Suppression**: Parts with `thought: True` are excluded from emitted events to keep consumer streams clean.
- **Streaming Output**: Asynchronous generator yielding `AgentEvent` instances with partial text deltas and function calls.
- **Backoff & Rate Limit Handling**: Automatic retry with exponential backoff on transient rate limits (HTTP 429).
- **Token Accounting**: Usage metadata is mapped into `Usage(prompt_tokens, output_tokens, total_tokens, cached_tokens)`.

---

## 5. Oracle Database 26ai Persistence

Sessions and event histories are persisted in Oracle 26ai using SQLSpec named queries in `src/app/db/sql/ai-runtime.sql`:

- `OracleSessionStore`: Manages `AGENT_SESSION` rows with session metadata and JSON state payloads (`save_session`, `get_session`, `delete_session`).
- `OracleEventStore`: Manages ordered event logs in `AGENT_EVENT` (`append_event`, `list_events`, `delete_events`).
- Event histories are reconstructed cleanly into `Content` and `AgentEvent` streams across conversation turns.

---

## 6. Execution Loop & Terminal-Aware SSE Streaming

The runtime execution loop in `AgentRuntime.execute_turn()` supports:
- **Turn & Step Budgets**: Configurable step limits prevent runaway tool loops, emitting a terminal event with `finish_reason="TOOL_LIMIT_EXCEEDED"` if exhausted.
- **Hierarchical Delegation**: `SpecTree` enables a root coordinator to route subtasks to specialist specs with prompt fencing:
  ```text
  <<<BEGIN_SYSTEM_INSTRUCTION>>>
  Role: Coffee Menu Specialist
  ...
  <<<END_SYSTEM_INSTRUCTION>>>
  ```
- **SSE Stream Adapter (`AgentStreamService`)**:
  - Drains queue asynchronously with periodic keep-alive pings (`type: ping`) every 5 seconds to prevent browser or proxy timeouts.
  - Formats structured event frames: `session`, `tool_call`, `tool_end` (with bounded character previews), `delta`, `ping`, and `final` (including aggregated search and token metrics).
  - Handles client cancellations and guarantees queue producer task cleanup.

---

## 7. Multi-Protocol Protocols (MCP & A2A)

### Model Context Protocol (`LitestarMCP`)
- Mounted at `POST /mcp` in `src/app/server/plugins.py`.
- Exposes route-level annotated controllers as tools via `mcp_tool="search_coffee_products"`.
- Configures local skill discovery via `MCPSkillsConfig(paths=[Path(".agents/skills")])`.
- Authentication is delegated to `litestar-security` using `route_opt={"auth": public()}`.

### Agent-to-Agent Protocol (`LitestarA2A`)
- Mounted at `POST /a2a` via `LitestarA2A` and `a2a-sdk`.
- Advertises agent capabilities at `GET /.well-known/agent-card.json` (`COFFEE_AGENT_CARD`).
- Executes incoming A2A messages via `CoffeeAgentExecutor`, bridging them into `AgentOrchestrationService`.
