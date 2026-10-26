# AI Runtime, MCP, A2A & APEX AI Gateway Review Checklist

## Runtime, Tool, Gateway & Protocol Rules

1. **Models & Embeddings (`src/app/domain/products/services/_embedding.py`, `src/app/lib/settings/_ai.py`)**:
   - Default chat model is `gemini-3.8-flash` (`location="global"`) and default embedding model is `gemini-embedding-2` (`3072` dimensions) implemented in `VertexAIService` (`src/app/domain/products/services/_embedding.py`).
   - Always pass `embedding_purpose="query"` for user search queries and `embedding_purpose="document"` for product and route document embeddings.
   - Placeholder or missing Vertex AI project IDs and credentials must raise `AIServiceUnconfigured` (mapped to HTTP 503), never an unhandled 500.
2. **Native Agent Runtime, Protocols & Services**:
   - Runtime protocols live in `src/app/domain/ai/protocols/_runtime.py` (`SessionStoreProtocol`, `EventStoreProtocol`, `ModelClientProtocol`, `CoffeeToolContext`), while agent orchestration, session history extraction, and grounded tool declarations live in `src/app/domain/ai/services/_agent.py` (`AgentOrchestrationService`), `src/app/domain/ai/services/_history.py`, and `src/app/domain/ai/services/_tools.py`.
   - `GeminiModelClient.generate_stream()` (`src/app/domain/ai/runtime/_model.py`) must extract `thought_signature` bytes and `FunctionCall` IDs on each streamed `partial=True` chunk `AgentEvent`, while `AgentRuntime` (`src/app/domain/ai/runtime/_loop.py`) aggregates `accumulated_parts` and yields a non-partial `AgentEvent` (`partial=False`, `actions={"aggregated": True}`) at the end of each model stream so `AgentOrchestrationService` (`src/app/domain/ai/services/_agent.py`) persists the turn and preserves `thought_signature` and function call IDs across tool turns.
   - Tool parameter JSON Schemas emitted by `declare()` (`src/app/domain/ai/runtime/_tools.py`) via `translate_to_gemini_schema()` (`src/app/domain/ai/runtime/_schema.py`) must use lowercase JSON Schema types (`"object"`, `"string"`, `"integer"`, `"number"`, `"boolean"`, `"array"`).
3. **Coordinate Privacy**:
   - Browser `latitude`, `longitude`, and `accuracy` inputs (`CoffeeChatForm` in `src/app/domain/chat/schemas/_forms.py`, normalized into a request-scoped `location_context` dict by `location_context_from_form()` in `src/app/domain/chat/controllers/_helpers.py`, plus `radius_miles` search inputs) are opt-in and request-scoped. Raw coordinates must never be persisted to `agent_session`, `agent_event`, `response_cache`, `search_metric`, or structured logs.
4. **LitestarMCP 0.15 & LitestarA2A (`src/app/domain/ai/mcp/`, `src/app/domain/ai/a2a/`)**:
   - `CoffeeSkillController` (`src/app/domain/ai/mcp/_skills.py`) and `CoffeePromptController` (`src/app/domain/ai/mcp/_prompts.py`) must declare `opt = {"auth": public()}` so `litestar-security` route compilation succeeds.
   - A2A 1.0 discovery and task execution live in `src/app/domain/ai/a2a/_card.py` (`build_agent_card`) and `src/app/domain/ai/a2a/_executor.py` (`CoffeeAgentExecutor`, `build_a2a_call_context`, `resolve_a2a_user_id`).
   - When `MCP_API_KEY` is configured, `/mcp` and `/a2a` validate credentials via `_ApiKeyVerifier` (`src/app/lib/security.py`) using constant-time `secrets.compare_digest`.
5. **APEX 26.1 Generative AI Gateway & Provisioning (`src/app/domain/products/controllers/_apex_ai.py`, `tools/oracle/apex_vertex.py`)**:
   - `ApexAIController` (`src/app/domain/products/controllers/_apex_ai.py`) exposes OpenAI-compatible `GET /api/apex/ai/v1/models` and `POST /api/apex/ai/v1/chat/completions` (JSON and SSE `data: [DONE]` modes) backed by `GeminiModelClient`, enforcing constant-time `secrets.compare_digest` Bearer validation whenever `APEX_GATEWAY_API_KEY` is configured and translating credential or service unavailability into HTTP 503 (`AIServiceUnconfigured`).
   - `ApexVertexConfigurator` (`tools/oracle/apex_vertex.py`) provisions `DBMS_NETWORK_ACL_ADMIN` host ACEs, `VERTEX_AI_CRED`, and `COFFEE_VERTEX_AI` (`APEX_AI.GENERATE`) using bound PL/SQL parameters and scrubs bearer tokens and passwords via `_redact_secrets` before raising `ApexVertexError`.
