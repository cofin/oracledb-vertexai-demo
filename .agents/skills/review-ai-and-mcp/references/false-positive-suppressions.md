# AI Runtime & MCP False-Positive Suppressions

DO NOT FLAG any of the following deliberate AI runtime and protocol patterns:

## `FP-AI-01` — `gemini-3.8-flash` and `gemini-embedding-2` Model Identifiers

- **DO NOT FLAG** `gemini-3.8-flash` (`google/gemini-3.8-flash`) or `gemini-embedding-2` in `src/app/lib/settings/_ai.py`, `src/app/domain/products/services/_embedding.py`, `src/app/domain/products/controllers/_apex_ai.py`, `tools/oracle/apex_vertex.py`, or `src/app/domain/` as invalid or future model names.
- **Rationale**: `gemini-3.8-flash` (served on Vertex AI `global` endpoint) and `gemini-embedding-2` (`VECTOR(3072, FLOAT32)`) are the canonical models for this application.

## `FP-AI-02` — Custom `AgentRuntime` Loop Alongside `litestar-mcp` 0.15 Primitives

- **DO NOT FLAG** `src/app/domain/ai/runtime/_loop.py` (`AgentRuntime`) or `src/app/domain/ai/services/_agent.py` (`AgentOrchestrationService`) for not using `litestar_mcp.agent.AgentRuntime` directly.
- **Rationale**: The application adopts `litestar-mcp` 0.15's `TurnBudget`, `AgentStreamFrame`, `SkillController`, `PromptController`, and `SpanManager` while retaining its domain-specific `AgentRuntime` loop to capture per-tool `sql_phases` telemetry and Oracle `agent_session`/`agent_event` persistence.

## `FP-AI-03` — `opt = {"auth": public()}` Without `ClassVar` on `CoffeeSkillController` and `CoffeePromptController`

- **DO NOT FLAG** `opt = {"auth": public()}` on `CoffeeSkillController` (`src/app/domain/ai/mcp/_skills.py`) or `CoffeePromptController` (`src/app/domain/ai/mcp/_prompts.py`) for omitting `ClassVar`.
- **Rationale**: Upstream `litestar.Controller` annotates `opt` as an instance attribute (`Mapping[str, Any] | None`), so annotating `ClassVar` on subclasses triggers a mypy `misc` override error.

## `FP-AI-04` — Optional `APEX_GATEWAY_API_KEY` Bearer Auth and `opt={"exclude_from_csrf": True}` on `ApexAIController`

- **DO NOT FLAG** `ApexAIController` (`src/app/domain/products/controllers/_apex_ai.py`) for setting `opt={"exclude_from_csrf": True}` on `POST /api/apex/ai/v1/chat/completions` or permitting unauthenticated local container requests when `APEX_GATEWAY_API_KEY` is unset.
- **Rationale**: Oracle APEX 26.1 (`APEX_AI.GENERATE`) calls `/api/apex/ai/v1` server-to-server from PL/SQL without browser cookies or CSRF tokens. Local Docker setups (`host.docker.internal`) allow optional keyless access, while non-local deployments configure `APEX_GATEWAY_API_KEY` to enforce constant-time `secrets.compare_digest` Bearer validation.
