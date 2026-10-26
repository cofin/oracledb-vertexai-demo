---
type: Guide
title: Native Agentic AI Runtime
description: Re-entrant AgentRuntime, GeminiModelClient, SpecTree delegation, OracleLoaderService 26ai persistence, SSE streaming, MCP 0.15, and A2A 1.0
tags:
  - ai
  - agent-runtime
  - gemini-3.8-flash
  - mcp
  - a2a
---

# Native Agentic AI Runtime

The AI subsystem in `src/app/domain/ai/` provides a native agent runtime built directly on `google-genai` (`gemini-3.8-flash`), `FrozenBaseStruct` (`msgspec`), `litestar-mcp` (`TurnBudget`, `SpanManager`, `AgentStreamFrame`), and SQLSpec `0.69.0` `OracleLoaderService` stores.

## 1. Execution Flow

```text
CoffeeChatController (POST /api/chat/stream)
  -> AgentOrchestrationService.stream_conversation_turn() (Scope.REQUEST)
     1. Load session/history via OracleSessionStore + OracleEventStore; append user AgentEvent
     2. CacheService lookup (skipped when location context or multi-turn session context is active)
     3. VertexAIService.get_text_embedding(..., embedding_purpose="query")
     4. HybridRouteResolver.resolve_turn() -> single-query Oracle 26ai Hybrid RRF + MetricsService
     5. GroundedRouteService.dispatch() (PRODUCT_RAG, STORE_LOCATION, PRODUCT_AVAILABILITY, ORDER_STATUS)
        OR AgentRuntime.execute_turn() (GENERAL_CONVERSATION with CallContext + CoffeeToolContext)
  -> AgentStreamService.adapt() -> SSE frames (session, tool_call, tool_end, delta, ping, final)
```

## 2. Core Primitives (`src/app/domain/ai/runtime/` & `src/app/domain/ai/protocols/_runtime.py`)

- **Wire Types (`_types.py`)**: Immutable, GC-exempt `FrozenBaseStruct` models (`Content`, `Part`, `FunctionCall`, `FunctionResponse`, `AgentEvent`, `AgentLimits`, `Usage`) with `kw_only=True` and `thought_signature` preservation.
- **Call Context & Protocols (`_context.py`, `protocols/_runtime.py`)**: `CallContext` and `CoffeeToolContext` carry session state and request-scoped services into tool executions; `SessionStoreProtocol`, `EventStoreProtocol`, and `ModelClientProtocol` decouple persistence and model streaming.
- **Schema Translator (`_schema.py`)**: `translate_to_gemini_schema()` converts Python 3.12+ and `msgspec.Struct` annotations into lowercase OpenAPI JSON Schema objects accepted by `google-genai`.
- **Tool Registry & Parallel Dispatch (`_tools.py`)**: `declare()` inspects tool signatures, coerces LLM arguments via `msgspec.convert(..., strict=False)`, and `execute_parallel()` runs tool calls concurrently with `asyncio.gather()`.
- **Agent Specifications (`_spec.py`)**: `AgentSpec`, `GenerationConfig`, `SpecTree` (automatic `transfer_to_agent` specialist delegation injection), and `fence_context_block()` (`<<<BEGIN_SYSTEM_INSTRUCTION>>>` ... `<<<END_SYSTEM_INSTRUCTION>>>` prompt boundary fencing).
- **Model Client (`_model.py`)**: `GeminiModelClient` wraps `genai.Client` (`gemini-3.8-flash` on `location="global"`), suppresses `thought=True` text parts while preserving `thought_signature`, assigns `call_<uuid>` fallback IDs, retries transient HTTP 429 errors with exponential backoff, and tracks token `Usage`. It also powers the OpenAI-compatible `ApexAIController` gateway at `/api/apex/ai/v1/*`.
- **Re-Entrant Execution Loop (`_loop.py`)**: `AgentRuntime.execute_turn()` enforces `TurnBudget` limits (`TOOL_LIMIT_EXCEEDED` / `TURN_LIMIT_EXCEEDED`), instruments turns and tool calls via OpenTelemetry `SpanManager`, fences `ACTIVE_SESSION_CONTEXT` dynamic prompts, and resolves `SpecTree` transfers.
- **Oracle Persistence (`_store.py`)**: `OracleSessionStore` (`agent_session`) and `OracleEventStore` (`agent_event`) extend `OracleLoaderService` using named SQL in `src/app/db/sql/ai-runtime.sql`, reading CLOB payloads inline as `str` via SQLSpec `0.69.0` (`fetch_lobs=False`).
- **SSE Stream Adapter (`_stream.py`)**: `AgentStreamService.adapt()` and `to_agent_stream_frame()` (`AgentStreamFrame`) drain events asynchronously, emit 5-second `ping` keep-alives, deduplicate aggregated `tool_call`/`delta` events, and emit a terminal `final` telemetry frame.

## 3. LitestarMCP 0.15, LitestarA2A & Protocol Auth

- **MCP (`src/app/domain/ai/mcp/` & `src/app/server/mcp/_config.py`)**: Mounted at `POST /mcp`, combining route-annotated `mcp_tool=` handlers (`get_product`, `get_store_inventory`, `search_products`), `CoffeeSkillController` (`_skills.py`), `CoffeePromptController` (`_prompts.py`), and `.agents/skills` via `MCPSkillsConfig`.
- **A2A (`src/app/domain/ai/a2a/`)**: Mounted at `POST /a2a` with `CoffeeAgentExecutor` (`_executor.py`) and `GET /.well-known/agent-card.json` (`build_agent_card` in `_card.py`).
- **Authentication (`src/app/lib/security.py` & `src/app/domain/products/controllers/_apex_ai.py`)**: `/mcp` and `/a2a` enforce constant-time `secrets.compare_digest` checks (`X-API-Key` or `Authorization: Bearer`) when `MCP_API_KEY` is configured (`build_security_config`); `/api/apex/ai/v1/*` enforces constant-time Bearer checks via `ApexAIController._verify_bearer_auth()` when `APEX_GATEWAY_API_KEY` is configured.
