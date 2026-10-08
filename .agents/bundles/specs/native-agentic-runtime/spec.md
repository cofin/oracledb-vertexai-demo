---
type: Spec
id: native-agentic-runtime
title: Generic Domain AI Runtime, Gemini 3.8 Flash, A2A Protocol & MCP Integration
description: Architecture specification for establishing a generic domain/ai/ layer with a native google-genai + msgspec agentic runtime, Gemini 3.8 Flash, A2A 1.0 agent protocol support, and advanced LitestarMCP integration while decommissioning Google ADK.
state: closed
parent_prd: null
tags:
  - spec
  - domain-ai
  - agent-runtime
  - gemini-3.8-flash
  - a2a-protocol
  - mcp
  - msgspec
  - sqlspec
  - oracle-26ai
  - litestar
---

# Architecture Specification: Generic Domain AI Runtime, Gemini 3.8 Flash, A2A & MCP

*Spec ID: `native-agentic-runtime`*
*Status: Closed / Implemented*
*Author: Agentic AI Engineering*
*Target Stack: Litestar 2.24+, litestar-security 0.6.0+, msgspec 0.19+, google-genai 2.28+, litestar-mcp 0.14+ (with A2A), OpenTelemetry (litestar[opentelemetry]), SQLSpec 0.65+, Oracle 26ai*

---

## 1. Executive Summary & North Star

This specification outlines the evolution of the application's AI capabilities into a **generic, first-class domain: `src/app/domain/ai/`**.

Instead of coupling the AI runtime and execution strictly to the chat domain (`domain/chat`), `domain/ai` provides the foundational intelligence platform for:
1. **Multi-Turn Conversational Agent**: Consumed cleanly by `app.domain.chat` and HTMX web views.
2. **Agent-to-Agent (A2A 1.0) Protocol**: Standard JSON-RPC and streaming agent communication (`POST /a2a` and `GET /.well-known/agent-card.json`) backed by `LitestarA2A` and `a2a-sdk`.
3. **Model Context Protocol (MCP)**: First-class tool exposure, resource catalog, and `MCPSkillsConfig` skills over `POST /mcp` backed by `LitestarMCP`.
4. **First-Party Gemini 3.8 Flash Acceleration**: Low-latency, high-throughput model execution (`gemini-3.8-flash`) with native thinking token handling and robust parallel tool dispatch.
5. **Native Oracle 26ai Persistence**: Session and event logging directly using SQLSpec named queries and Oracle ACID transactions, fully decommissioning `google-adk`.
6. **Declarative Security & Browser Hardening (`litestar-security` 0.6.0)**: Modern application security baseline using `SecurityPlugin` with hardened response headers (`SecurityHeadersConfig.hardened()`), declarative `PublicController` / `SecureController` base classes replacing deprecated `exclude_from_auth` attributes, unified session/CSRF derivation, and automated auth delegation for machine-only endpoints (`/mcp`, `/a2a`).
7. **End-to-End Observability & Tracing (OpenTelemetry)**: Full ASGI request/response instrumentation and distributed tracing enabled by default via `OpenTelemetryPlugin(config=OpenTelemetryConfig(exclude=[...]))` and configured via `OpenTelemetrySettings`, with static asset and health check path exclusions.

---

## 2. Deep-Module Domain Boundaries

```text
src/app/domain/
├── ai/                              <-- GENERIC AI SUBSYSTEM
│   ├── runtime/                     # Core dynamic agentic runtime
│   │   ├── _types.py                # msgspec.Struct wire contracts (Content, Part, FunctionCall, Event)
│   │   ├── _schema.py               # msgspec JSON schema -> Gemini schema converter
│   │   ├── _tools.py                # Tool, ToolDeclaration, declare(), execute_parallel()
│   │   ├── _context.py              # CallContext & RunContextRegistry for Dishka DI binding
│   │   ├── _model.py                # GeminiModelClient (google-genai client, gemini-3.8-flash, streaming)
│   │   ├── _spec.py                 # AgentSpec, SpecTree, and context fencing (<<<BEGIN_SYSTEM_INSTRUCTION>>>)
│   │   ├── _store.py                # OracleSessionStore and OracleEventStore using SQLSpec
│   │   ├── _loop.py                 # AgentRuntime re-entrant loop with turn/step limits
│   │   └── _stream.py               # Terminal-aware SSE StreamService (pings, delta, previews)
│   ├── services/
│   │   ├── classifier.py            # FlashLiteIntentClassifier (gemini-3.8-flash, structured enum)
│   │   └── agent_service.py         # AgentOrchestrationService coordinating turns and sessions
│   ├── a2a/
│   │   ├── card.py                  # AgentCard declaration for A2A discovery
│   │   └── executor.py              # CoffeeAgentExecutor(AgentExecutor) bridging A2A requests to AgentRuntime
│   └── mcp/
│       └── tools.py                 # MCP tool registry and decorators
│
├── chat/                            <-- PURE CONSUMER OF AI DOMAIN
│   ├── controllers/
│   │   └── _chat.py                 # Litestar HTTP/SSE endpoints (/api/chat, /api/chat/stream)
│   ├── schemas/
│   └── session.py                   # User session derivation & cookies
│
├── products/                        <-- DOMAIN CAPABILITIES & MCP TOOLS
│   ├── controllers/
│   │   └── _products.py             # HTTP routes with mcp_tool="search_products", etc.
│   └── services/                    # ProductService, StoreService
│
└── web/                             <-- UI CONSUMER
    ├── controllers/_pages.py        # HTMX chat page and partials
    └── templates/
```

### Boundary Guarantees

1. **`domain.ai` has zero dependencies on `domain.chat`**: All core AI types, tools, model clients, A2A executors, and execution loops reside in `domain.ai`.
2. **`domain.chat` is a lightweight adapter**: Handles browser cookies, Litestar session derivation, and HTTP SSE dispatching by invoking `AgentOrchestrationService` and `AgentStreamService`.
3. **Tools resolve request-scoped services via `CallContext`**: `Scope.APP` tool definitions receive a `CallContext` containing request-scoped Dishka services (`ProductService`, `StoreService`, `CacheService`, `MetricsService`). Short-lived database transactions are acquired only inside tool calls and persistence steps, never held across LLM awaits.
4. **Multi-Protocol Serving**: The same tools and agent capabilities are addressable via:
   - Browser SSE (`/api/chat/stream`)
   - Agent-to-Agent protocol (`/a2a` and `/.well-known/agent-card.json`)
   - Model Context Protocol (`/mcp` and CLI stdio bridge)

---

## 3. Detailed Component Specifications

### 3.1 Model Client & Gemini 3.8 Flash (`app.domain.ai.runtime._model`)

- Uses `google.genai.Client(vertexai=True)` directly with `gemini-3.8-flash`.
- Employs `client.aio.models.generate_content_stream` for interactive streaming.
- Strips `part.thought` and reasoning tokens from client-visible text deltas while preserving signatures for conversational continuity.
- Encapsulates exponential backoff retry on HTTP 429 (`ResourceExhausted`).

### 3.2 Wire Contracts & Schemas (`app.domain.ai.runtime._types` & `_schema`)

- Frozen `msgspec.Struct` types: `FunctionCall`, `FunctionResponse`, `Part`, `Content`, `Usage`, `AgentEvent`, `AgentLimits`.
- `translate_to_gemini_schema()` converts Python type annotations (via `msgspec.json.schema`) to the Gemini `FunctionDeclaration` schema subset (`type`, `properties`, `required`, `items`, `enum`, `description`).

### 3.3 Dynamic Tool Execution & DI Binding (`app.domain.ai.runtime._tools` & `_context`)

- `declare(fn)`: Function decorator converting async coroutines into typed `Tool` instances.
- `execute_parallel(calls, tools, ctx)`: Executes concurrent tool calls via `asyncio.gather()`. Catches domain exceptions and returns structured `{"error": {"code": "...", "message": "..."}}` so the model can self-correct without crashing the stream.
- `CallContext`: Holds session ID, invocation ID, turn number, and the active Dishka request container for resolving domain services.

### 3.4 Oracle Persistence (`app.domain.ai.runtime._store`)

- Backed by SQLSpec named queries in `db/sql/ai-runtime.sql`.
- Stores sessions and events in Oracle 26ai tables with native `JSON` columns.
- Uses monotonic sequence numbers per session for deterministic replay and history reconstruction.

### 3.5 Execution Loop & Terminal-Aware Streaming (`_loop.py` & `_stream.py`)

- `AgentRuntime`: Enforces per-turn budgets (`max_tool_calls_per_turn`, `max_model_calls_per_turn`), manages dynamic prompt fencing (`<<<BEGIN_SYSTEM_INSTRUCTION>>>`), and orchestrates multi-step re-entrant execution.
- `AgentStreamService.adapt()`: Adapts runtime events to SSE format, emitting an initial `session` frame, real-time `delta` text, deduplicated `tool_call` and `tool_end` markers (bounded to 240 chars preview), idle `ping` frames (every 5.0s), and a guaranteed terminal `complete` or `error` frame.

### 3.6 A2A 1.0 Agent Protocol Integration (`app.domain.ai.a2a`)

- Utilizes `litestar-mcp[a2a]` with `a2a-sdk`.
- `card.py`: Defines the `AgentCard` advertising Cymbal Coffee capabilities, skills (`coffee_recommendation`, `store_inventory`, `store_location`), and `AgentInterface(url="http://localhost:8000/a2a", protocol_binding="JSONRPC", protocol_version="1.0")`.
- `executor.py`: Implements `CoffeeAgentExecutor(AgentExecutor)`. Inside `execute(context, event_queue)`, opens a fresh `Scope.REQUEST` container from Dishka and delegates execution to `AgentOrchestrationService`.
- Configures `LitestarA2A` plugin in `src/app/server/plugins.py`:
  - `A2AConfig(path="/a2a", agent_card_path="/.well-known/agent-card.json")`.

### 3.7 Model Context Protocol (MCP) Integration (`app.domain.ai.mcp`)

- Configures `LitestarMCP` plugin in `src/app/server/plugins.py`:
  - `MCPConfig(name="Cymbal Coffee MCP", skills=MCPSkillsConfig(paths=[Path("skills"), Path(".agents/skills")], directory_read=True), route_opt={"auth": public()})`
- Annotates coffee and store endpoints in `src/app/domain/products/controllers/` with `mcp_tool="name"`:
  - `search_products`
  - `get_store_inventory`
  - `check_product_availability`
  - `find_nearby_stores`
- Enables CLI execution via `litestar mcp bridge` and `litestar mcp stdio`.

### 3.8 Declarative Security & Hardening (`litestar-security` 0.6.0)

- Registers `SecurityPlugin(config=SecurityConfig(headers=SecurityHeadersConfig.hardened(), exclude=[r"^/static", r"^/favicon\.ico"]))` in `src/app/server/plugins.py`.
- Controllers subclass `PublicController` from `litestar_security` for public endpoints (`PageController`, `CoffeeChatController`, `ProductController`, `StoreController`, `VectorSearchController`, `SystemController`, `MetricsController`), eliminating deprecated `exclude_from_auth=True` parameters.
- Replaces manual `session_config.middleware` and `csrf_config` in `src/app/server/core.py` with unified security plugin lifecycle management.
- Delegates MCP and A2A machine endpoint authentication directly to `litestar-security` via `route_opt={"auth": public()}` (or API keys) on `MCPConfig` and `opt={"auth": public()}` on `A2AConfig` / `/.well-known/agent-card.json`.

### 3.9 Observability, OpenTelemetry & Database Telemetry

- **ASGI Tracing**: Employs first-party `litestar[opentelemetry]` (`opentelemetry-instrumentation-asgi`, `opentelemetry-sdk`, `opentelemetry-util-http`). Configures `OpenTelemetrySettings` in `src/app/lib/settings.py` (`ENABLED=True`, `SERVICE_NAME="cymbal-coffee"`, exclusions for `^/static`, `^/favicon\.ico`, `^/health`). Registers `OpenTelemetryPlugin` in `src/app/server/plugins.py` and mounts into `app_config.plugins` in `src/app/server/core.py`.
- **Database Spans & SQL Telemetry**: Configures SQLSpec runtime telemetry in `src/app/lib/settings.py` (`DatabaseSettings`) using `ObservabilityConfig`, `TelemetryConfig(enable_spans=self.ENABLE_TELEMETRY)`, and `LoggingConfig(include_trace_context=True, include_sql_hash=True)`. Database statements automatically create child spans linked to the active ASGI request trace context.
- **SQL Echo Toggle**: Exposes `DATABASE_ECHO` / `DATABASE_ECHO_SQL` (defaulting to False) mapped to `ObservabilityConfig(print_sql=self.ECHO)`, enabling statement observer logging to `sqlspec.sql` and attaching sanitized SQL queries directly to trace spans when active.

---

## 4. Work Breakdown Structure (Vertical Slices)

| Task ID | Worksheet Path | Scope & Deliverable | Verification Strategy |
| :--- | :--- | :--- | :--- |
| **task-1** | `tasks/01_ai_runtime_primitives.md` | Core runtime types, schemas, `declare()` tool runner, `execute_parallel()`, and `CallContext` in `app.domain.ai.runtime`. (Completed & Closed) | `behavior_tdd` |
| **task-2** | `tasks/02_ai_runtime_model_and_store.md` | `GeminiModelClient` (Gemini 3.8 Flash), prompt spec fencing, and Oracle SQLSpec session/event store in `app.domain.ai.runtime`. (Completed & Closed) | `behavior_tdd` |
| **task-3** | `tasks/03_ai_runtime_loop_and_stream.md` | `AgentRuntime` execution loop, `AgentStreamService` terminal-aware SSE adapter, and `AgentOrchestrationService`. (Completed & Closed) | `behavior_tdd` |
| **task-4** | `tasks/04_mcp_and_skills_integration.md` | `LitestarMCP` plugin mount with `litestar-security` auth delegation (`route_opt={"auth": public()}`), route-level tool decorators, and `MCPSkillsConfig`. (Completed & Closed) | `behavior_tdd` |
| **task-5** | `tasks/05_a2a_agent_protocol.md` | `litestar-mcp[a2a]` dependency, `AgentCard` declaration, `CoffeeAgentExecutor`, and `LitestarA2A` plugin mount at `/a2a` with public discovery. (Completed & Closed) | `behavior_tdd` |
| **task-6** | `tasks/06_chat_migration_and_adk_decommission.md` | Chat controller migration to `domain.ai`, `SecurityPlugin` + `OpenTelemetryPlugin` wiring in `plugins.py`/`core.py`, `PublicController` adoption, Dishka DI wiring in `ioc.py`, ADK decommission, and test suite validation. (Completed & Closed) | `integration_acceptance` |

---

## 5. CI Pipeline & PyApp Packaging Alignment

To keep the application release process aligned with modern standards (such as `litestar-queues` and `litestar-build`):

1. **Two-Phase PyApp Packaging**:
   - `build-wheel`: Produces a self-contained wheel embedding the compiled Vite frontend (`app/domain/web/public`) via `uv build --wheel --clear`.
   - `tools/bundler.py build`: Downloads stripped standalone Python runtimes (Python 3.13.13+), embeds the wheel, and compiles the single-file PyApp binary using `cargo zigbuild --release --target <arch>-unknown-linux-gnu.2.17` with static `bzip2` and `lzma` (`BZIP2_SYS_STATIC=1`, `LZMA_API_STATIC=1`).
2. **GitHub Actions Hardening (aligned with `litestar-queues`)**:
   - Explicit `persist-credentials: false` on checkouts to eliminate ambient token permissions.
   - Pinned action SHA commits with human-readable version tags.
   - Concurrency group `test-${{ github.head_ref || github.ref }}` with `cancel-in-progress: true`.
   - Dedicated parallel verification jobs: `validate` (`uvx prek run`), `mypy`, `pyright`, and `test` matrix across Python versions.
   - `mkdir -p app/domain/web/public` placeholder trick preventing type checkers or Hatchling from failing in pure Python test jobs.

---

## 6. Verification & Acceptance Criteria

- [x] All 6 task worksheets created with decision-complete technical specs and exact test commands.
- [x] Application source code remains untouched during planning phase.
- [x] Every task mapped to a single verification strategy with initial and final evidence.
- [x] PyApp packaging and CI configurations support the new generic `domain/ai` layout.
- [x] Full `make lint` and `uv run pytest src/tests/unit` verification passes cleanly at every step (356 unit tests + 14 integration tests passing).
