# AI Runtime, MCP & A2A Review Checklist

## Runtime, Tool & Protocol Rules

1. **Models & Embeddings**:
   - Default chat model is `gemini-3.8-flash` (`location="global"`) and default embedding model is `gemini-embedding-2` (`3072` dimensions).
   - Always pass `embedding_purpose="query"` for user search queries and `embedding_purpose="document"` for product/route document embeddings.
   - Placeholder Vertex AI project IDs must raise `AIServiceUnconfigured` (mapped to HTTP 503), never an unhandled 500.
2. **Native Agent Runtime (`src/app/domain/ai/runtime/`)**:
   - `GeminiModelClient` must yield a non-partial aggregated `Event` (`partial=False`) at the end of each model stream so `AgentRuntime` persists the turn and preserves `thought_signature` and function call IDs.
   - Tool parameter JSON Schemas emitted by `declare()` in `src/app/domain/ai/runtime/_schema.py` must use lowercase JSON Schema types (`"object"`, `"string"`, `"integer"`, `"number"`, `"boolean"`, `"array"`).
3. **Coordinate Privacy**:
   - Browser latitude/longitude coordinates (`LocationContext`) are request-scoped opt-in inputs. They must never be persisted to `agent_session`, `agent_event`, `response_cache`, `search_metrics`, or structured logs.
4. **LitestarMCP 0.15 & LitestarA2A**:
   - `CoffeeSkillController` and `CoffeePromptController` must declare `opt = {"auth": public()}` so `litestar-security` route compilation succeeds.
   - When `MCP_API_KEY` is configured, `/mcp` and `/a2a` validate credentials using constant-time `hmac.compare_digest`.
