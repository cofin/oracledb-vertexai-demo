# Flow: ADK 2.0 Runner (adk2-runner_20260429)

*Chapter 3 of [cymbal-coffee-reset_20260429](../cymbal-coffee-reset_20260429/prd.md)*
*Beads epic: `oracledb-vertexai-4d6.3` (blocked by Ch 2, blocks Ch 5)*

---

## Specification

### Objective

Rebuild the chat runner on **Google ADK 2.0** (`Workflow` / `BaseNode` graph orchestration; floor pin `google-adk>=2.0.0b1`) and eliminate the slow path from intent classification. The runner classifies intent with a **Gemini 2.5 Flash-Lite enum-classifier** **dispatched in parallel** with the main agent's response generation via `asyncio.gather` inside a custom `@node`. Perceived intent latency drops from ~150–400ms (embedding + vector top-1) to ~0ms (hidden behind retrieval). The `request_container_var` workaround disappears in favor of **closure-bound tools** built per-request.

**Pre-Ch3 cleanup (landed):** `IntentService`, `ExemplarService`, `ExemplarController`, `IntentExemplar` schema, `--include-exemplars` CLI flags, and the legacy `BASE_SYSTEM_INSTRUCTION` "ALWAYS call classify_intent first" prose are deleted. The `intent_exemplar` table and `intent_exemplar.json.gz` fixture are retained as data-only artifacts; their removal is queued as a follow-up once the new classifier replaces them.

### Code Analysis Summary (verified 2026-04-29)

**Critical latent bug discovered during research:**

`request_container_var` (defined `src/app/lib/di.py`) is **never `.set()` anywhere in the codebase** — verified via `grep -rn "request_container_var.set\|request_container_var =" src/app`. Every ADK tool invocation falls into the `else` branch of `_resolve_request_container` (`src/app/domain/chat/services/adk.py`) and **constructs a fresh Dishka `AsyncContainer` per call**. With up to 3 tools per chat turn this is 3 container builds + 3 fresh Oracle sessions per request. The Ch 3 rewrite erases the entire mechanism.

**Current runner shape (`src/app/domain/chat/services/adk.py`):**

- Constructor takes `SQLSpecSessionService` (sqlspec ADK extension — already correct).
- Builds one `LlmAgent(name="CoffeeAssistant", instruction=BASE_SYSTEM_INSTRUCTION, model=settings.vertex_ai.CHAT_MODEL, tools=ALL_TOOLS)` at construction time.
- Wraps it in `Runner(agent=agent, app_name="coffee-assistant", session_service=session_service)`.
- `process_request` composes persona overlay by **string-concatenating into the user turn** (`f"[System Context: {persona_instruction}]\n\nUser Query: {query}"`) — the persona never reaches `LlmAgent.instruction`.
- Returns `{"answer", "session_id", "response_time_ms"}`. The `intent_detected`, `search_metrics`, `from_cache`, `embedding_cache_hit` keys the controller expects (`controllers.py:94-97`) default to empty/false because the runner never emits them.

**Intent classifier (post-cleanup):** the legacy exemplar-vector lookup is gone — `IntentService` and `ExemplarService` are deleted. Until Ch 3 lands the Flash-Lite classifier the runner has no intent step; the LLM responds directly using `search_products_by_vector` / `get_product_details`.

**Persona system (`src/app/domain/system/services/services.py`):**

- `PersonaConfig` (msgspec): `name`, `description`, `language_style`, `focus_areas`, `example_responses`, `system_prompt_addon`, `temperature`, `complexity_level`.
- 4 personas: `novice`, `enthusiast` (default), `expert`, `barista`.
- `temperature` and `complexity_level` are **defined but never threaded into `LlmAgent`**.

**Credential guard (`src/app/domain/chat/controllers/_chat.py`):** brittle string match (`"API key" in str(exc) or "credentials" in str(exc).lower()`) on `ValueError`. Replace with typed exception `AIServiceUnconfigured`.

**ADK store wiring (`src/app/ioc.py`):** `OracleAsyncADKStore(config)` + `SQLSpecSessionService(store)` already provided as APP-singletons. Missing: `await store.ensure_tables()` at startup.

### ADK 2.0 contract (verified against adk.dev + PyPI 2026-04-21):

- Pin: `google-adk>=2.0.0b1` (floor only — bump as betas/RCs ship). Backwards-compatible with 1.x `LlmAgent`.
- Imports:
  ```python
  from google.adk import Context, Runner, Workflow
  from google.adk.workflow import BaseNode, FunctionNode, node
  from google.adk.agents import LlmAgent
  from google.adk.agents.callback_context import CallbackContext
  from google.genai import types
  ```
- `Workflow(name=..., edges=[("START", entry_node)])` is the root container; `Runner` accepts a workflow root the same way it accepts an agent.
- Tools may declare a final `tool_context: ToolContext` parameter; runtime supplies it. `tool_context.state` is the same dict as `session.state`. **Closure-bound tools** are simpler than state-stuffing for our case.
- `before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]` — returning `Content` short-circuits the agent (perfect for the credential guard).
- Parallel fan-out: `await asyncio.gather(ctx.run_node(node_a, ...), ctx.run_node(node_b, ...))` inside a `@node` is the canonical pattern when branches have heterogeneous return shapes.
- Structured output via Flash-Lite: `client.aio.models.generate_content(model="gemini-2.5-flash-lite", contents=phrase, config=types.GenerateContentConfig(response_mime_type="text/x.enum", response_schema={"type": "STRING", "enum": INTENT_VALUES}, system_instruction="..."))` returns the enum label as `response.text`.

### Requirements

1. `pyproject.toml` pin remains floor-only at `google-adk>=2.0.0b1`.
2. New `src/app/domain/chat/services/workflow.py` defines an ADK 2.0 `Workflow` with one custom `@node` (`classify_and_respond`) that fans out **`intent_node`** (Gemini Flash-Lite enum classifier) and **`coffee_turn`** (the `LlmAgent` response) via `asyncio.gather`.
3. New `src/app/domain/chat/services/classifier.py` exposes `FlashLiteIntentClassifier` with `async classify(phrase: str) -> IntentLabel` using `text/x.enum` structured output.
4. `ADKRunner.process_request` becomes:
   - Resolve services via Dishka at the controller layer; pass them in.
   - Build the per-request `LlmAgent` with **closure-bound tools** (no module-level functions, no `request_container_var`).
   - Construct the `Workflow` for this turn; invoke via `Runner.run_async`.
   - Return `{"answer", "session_id", "response_time_ms", "intent_detected", "search_metrics", "from_cache", "embedding_cache_hit"}` with all keys populated.
5. Persona overlay flows into `LlmAgent(instruction=composed_prompt, generate_content_config=GenerateContentConfig(temperature=persona.temperature))` — `temperature` is finally honored.
6. `request_container_var`, `_resolve_request_container`, and the module-level `search_products_by_vector` / `get_product_details` tool functions are deleted; tools become per-request closures.
7. `before_agent_callback` on the `LlmAgent` runs the credential guard — returns `types.Content(parts=[Part(text="...")])` with the 503 message text when the Vertex client can't be initialized; controller maps the response to HTTP 503 via a typed `AIServiceUnconfigured` exception path.
8. App startup hook (`src/app/server/asgi.py`) calls `await store.ensure_tables()` so the demo boots without a separate ADK-session DDL step. Main product migrations still run through `uv run python manage.py database upgrade`.
9. New integration test `src/tests/integration/test_chat_workflow.py` asserts (a) `intent_detected` is one of the enum values, (b) `answer` is non-empty, (c) `response_time_ms < 4000` (95th pct expectation; widen if needed).

### Acceptance Criteria

- `grep -rn "request_container_var" src/app/` returns **zero** hits.
- `grep -rn "_resolve_request_container" src/app/` returns **zero** hits.
- `python -c "from app.domain.chat.services.workflow import make_workflow; print(make_workflow.__doc__)"` runs without ImportError.
- Manual `POST /api/chat` returns response within 4 seconds; response includes populated `intent_detected`, `search_metrics`, `from_cache`, `embedding_cache_hit`.
- App boot logs include `ADKStore.ensure_tables() OK` (or equivalent).
- `make lint && make test` green; `uv run pytest src/tests/integration/test_chat_workflow.py -v` passes.
- A repro of the *old* slow-path is impossible — searching for the `else: container = make_litestar_container()` branch in `adk.py` yields no match.

### Risks / Known Gotchas

- **ADK 2.0b1 is beta.** Pin exactly. API churn risk: isolate every `from google.adk` import inside `domain/chat/services/workflow.py` and `adk.py` so a future `2.0.0b2` only touches those two files.
- **`session.state` is JSON-persisted via `SQLSpecSessionService`.** Do NOT stash Dishka containers, drivers, or any non-serializable object there. Use closure-bound tools.
- **`text/x.enum` requires `gemini-2.5-flash-lite` or newer.** Pin `settings.vertex_ai.INTENT_MODEL = "gemini-2.5-flash-lite"`.
- **Per-turn `LlmAgent` construction is cheap** (Pydantic init only). The expensive call is the model invocation. Don't micro-optimize agent caching.
- **`worker_container_var` (used by SAQ in `lib/di.py:74`) must remain.** Only delete `request_container_var`, not the worker variant.
- **`store.ensure_tables()` adds 30–100ms to first boot** issuing idempotent `CREATE TABLE IF NOT EXISTS`. Acceptable for a reference demo.
---

### Follow-ups (not blocking Ch 3)

- **`intent_exemplar` table + `intent_exemplar.json.gz` fixture removal.** The runtime classifier no longer reads this data. Schedule deletion (DDL drop + migration entry + fixture file removal + `COFFEE_SHOP_TABLES` trim + integration-test bootstrap trim) once Ch 3 has shipped and there are no consumers.

---

## Implementation Plan

### Phase 0: API surface verification (`oracledb-vertexai-4d6.3.0`)

- [x] **0.1** ~~After Ch 1 has bumped `google-adk==2.0.0b1`, run a smoke import~~ **VERIFIED 2026-04-30**: All assumed imports resolve cleanly against installed `google-adk==2.0.0b1` — `Context`/`Runner`/`Workflow` from `google.adk`, `BaseNode`/`FunctionNode`/`node` from `google.adk.workflow`, `LlmAgent` from `google.adk.agents`, `CallbackContext` from `google.adk.agents.callback_context`. `@node` decoration produces a `FunctionNode` (a `BaseNode`). Pinned in `src/tests/unit/test_adk2_surface_pin.py`.
- [x] **0.2** ~~Same smoke for `Runner` accepting a workflow root~~ **VERIFIED 2026-04-30**: `Runner.__init__` exposes both `agent: Optional[BaseAgent] = None` and `node: Any = None` as separate kwargs. `Workflow` is a `BaseNode` subclass (not a `BaseAgent`), so the workflow root MUST be passed as `Runner(node=workflow, ...)`, **NOT** `agent=workflow`. Phase 4.1c + 4.1d updated. Pinned in `src/tests/unit/test_adk2_surface_pin.py`.
- [x] **0.3** ~~Confirm `gemini-2.5-flash-lite` accepts `response_mime_type="text/x.enum"`~~ **PARTIAL 2026-04-30**: SDK-level shape verified — `types.GenerateContentConfig(response_mime_type="text/x.enum", response_schema={"type": "STRING", "enum": [...]})` constructs cleanly with `google-genai` (pinned in `test_adk2_surface_pin.py::test_genai_types_for_classifier`). Live API smoke deferred — no `GOOGLE_API_KEY`/`VERTEX_AI_API_KEY` available in this environment. Smoke once creds are available with: `client.aio.models.generate_content(model="gemini-2.5-flash-lite", contents="Where's the nearest Cymbal?", config=GenerateContentConfig(response_mime_type="text/x.enum", response_schema={"type": "STRING", "enum": ["PRODUCT_RAG","STORE_LOCATION","ORDER_STATUS","GENERAL_CONVERSATION"]}))` and assert `response.text` is one of the enum values.

### Phase 1: ADK store + startup hooks (`oracledb-vertexai-4d6.3.1`)

**Closed as no-op 2026-04-30**: bootstrap topology was misread in the original spec. ADK tables are created by sqlspec's auto-injected extension migration (`ext_adk_0001`, surfaced by `coffee upgrade`) when `extension_config["adk"]` is set and `"adk"` is in `migration_config["include_extensions"]`. Both already present in `src/app/lib/settings.py:140-156`. There is no project-owned `*adk*.sql` to delete; sqlspec materializes the migration at runtime from the configured store DDL. Migration remains the single bootstrap path — no startup `ensure_tables()` hook needed.

- [x] **1.1** ~~Extend `extension_config["adk"]`~~ Already present (`session_table`, `events_table`).
- [x] **1.2** ~~Add `ensure_tables()` startup hook~~ Skipped — redundant with extension migration; would be a second bootstrap mechanism for a demo app that already runs `coffee upgrade`.
- [x] **1.3** ~~Delete redundant adk migration~~ No project file to delete; the auto-injected `ext_adk_0001` is the canonical migration.

### Phase 2: Flash-Lite enum classifier (`oracledb-vertexai-4d6.3.2`)

- [x] **2.1** Create `src/app/domain/chat/services/classifier.py`: [e48d80e]
  ```python
  from google import genai
  from google.genai import types

  class IntentLabel(str, Enum):
      PRODUCT_RAG = "PRODUCT_RAG"
      GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
      STORE_LOCATION = "STORE_LOCATION"
      ORDER_STATUS = "ORDER_STATUS"

  INTENT_VALUES = [m.value for m in IntentLabel]

  class FlashLiteIntentClassifier:
      def __init__(self, client: genai.Client, model: str = "gemini-2.5-flash-lite") -> None:
          self._client = client
          self._model = model

      async def classify(self, phrase: str) -> IntentLabel:
          response = await self._client.aio.models.generate_content(
              model=self._model,
              contents=phrase,
              config=types.GenerateContentConfig(
                  response_mime_type="text/x.enum",
                  response_schema={"type": "STRING", "enum": INTENT_VALUES},
                  system_instruction="Classify the user's coffee-related intent. Return exactly one label.",
              ),
          )
          return IntentLabel(response.text)
  ```
- [x] **2.2** Add `INTENT_MODEL: str = "gemini-2.5-flash-lite"` to `settings.vertex_ai`. [e48d80e]
- [x] **2.3** Wire `FlashLiteIntentClassifier` into the APP-scoped `provide_intent_classifier` slot **already reserved** by Ch 2 in `IntegrationsProvider` (`src/app/ioc.py`). The provider depends on `genai.Client` from the same provider; signature: `def provide_intent_classifier(self, client: genai.Client) -> FlashLiteIntentClassifier: return FlashLiteIntentClassifier(client, model=settings.vertex_ai.INTENT_MODEL)`. [e48d80e]
- [x] **2.4** Unit test `src/tests/unit/test_classifier.py` — mock `client.aio.models.generate_content` to return `MagicMock(text="PRODUCT_RAG")`; assert classifier returns the enum. [e48d80e]

### Phase 3: Workflow + parallel fan-out (`oracledb-vertexai-4d6.3.3`)

- [x] **3.1** Create `src/app/domain/chat/services/workflow.py`: [a5f6da6]
  ```python
  import asyncio
  from google.adk import Context, Workflow
  from google.adk.workflow import node
  from google.adk.agents import LlmAgent
  from google.genai import types

  def make_intent_node(classifier: FlashLiteIntentClassifier):
      @node(name="intent")
      async def intent_node(ctx: Context, user_query: str) -> str:
          return (await classifier.classify(user_query)).value
      return intent_node

  def make_coffee_node(agent: LlmAgent):
      @node(name="coffee_turn")
      async def coffee_turn(ctx: Context, user_query: str) -> str:
          return await ctx.run_node(agent, user_query)
      return coffee_turn

  def make_workflow(classifier, agent) -> Workflow:
      intent = make_intent_node(classifier)
      coffee = make_coffee_node(agent)

      @node(name="classify_and_respond")
      async def classify_and_respond(ctx: Context, user_query: str) -> dict:
          intent_label, answer = await asyncio.gather(
              ctx.run_node(intent, user_query),
              ctx.run_node(coffee, user_query),
          )
          return {"answer": answer, "intent": intent_label}

      return Workflow(name="coffee_workflow", edges=[("START", classify_and_respond)])
  ```
- [x] **3.2** Unit test `src/tests/unit/test_workflow_factory.py` — mock classifier + agent, run the workflow, assert dict shape. [a5f6da6]

### Phase 4: ADKRunner rewrite (`oracledb-vertexai-4d6.3.4`)

- [x] **4.1a** Replace the constructor in `src/app/domain/chat/services/adk.py:ADKRunner.__init__`: `def __init__(self, session_service: SQLSpecSessionService, classifier: FlashLiteIntentClassifier, persona_manager: PersonaManager)`. Store all three on `self._...`. Delete any old construction-time `LlmAgent` / `Runner` setup (now per-request). [d35d3e4]
- [x] **4.1b** Add a private helper `_make_tool_factories(tools_service: AgentToolsService) -> list[Callable]` that returns closure-bound `search_products_by_vector` and `get_product_details` async functions. No module-level tool functions remain. [d35d3e4]
- [x] **4.1c** Add a private helper `_build_workflow(self, instruction: str, temperature: float, tools: list[Callable]) -> Workflow`: [d35d3e4]
  ```python
  agent = LlmAgent(
      name="CoffeeAssistant",
      model=settings.vertex_ai.CHAT_MODEL,
      instruction=instruction,
      tools=tools,
      generate_content_config=GenerateContentConfig(temperature=temperature),
      before_agent_callback=credential_guard_callback,
  )
  return make_workflow(self._classifier, agent)
  ```
  Confirmed by Phase 0.2: `Runner` accepts a `Workflow` root as `node=workflow`, **not** `agent=workflow` (`Workflow` extends `BaseNode`, not `BaseAgent`).
- [x] **4.1d** Rewrite `process_request(query, user_id, session_id, persona, tools_service)` to: resolve persona+temperature, build tools via 4.1b, build workflow via 4.1c, instantiate `Runner(node=workflow, app_name="coffee-assistant", session_service=self._session_service)`, call `run_async(user_id, session.id, new_message=Content(role="user", parts=[Part(text=query)]))`, aggregate events, and return the populated `ChatResult` dict (all 7 keys). [d35d3e4]
- [x] **4.2** Add `credential_guard_callback(callback_context: CallbackContext) -> Optional[types.Content]` as a **defense-in-depth** that returns the 503-text `Content` when invoked with an unconfigured client — short-circuits the agent. **The primary path is controller pre-flight:** wrap the `runner.process_request` call in `controllers.py` with a try that catches `genai.errors.ClientError`/`ValueError` from `genai.Client(...)` resolution and raises `AIServiceUnconfigured`. The callback is the safety net if pre-flight slips through. [d35d3e4]
- [x] **4.3** Define `class AIServiceUnconfigured(Exception)` in `src/app/domain/chat/exceptions.py`. Update `src/app/domain/chat/controllers/_chat.py` to catch this typed exception and return `HTTPException(status_code=503, detail="AI service is not configured. Set GOOGLE_API_KEY or VERTEX_AI_API_KEY in your .env file.")`. Delete the string-match block. [d35d3e4]
- [x] **4.4** Update `IntegrationsProvider.provide_adk_runner` (Ch 2 created the slot): now depends on `(session_service, classifier, persona_manager)` — no code change here if Ch 2 already wired it; sanity-check. [d35d3e4]

### Phase 5: Cleanup of pre-2.0 workarounds (`oracledb-vertexai-4d6.3.5`)

> Sub-tasks 5.5 and 5.7 already landed in the pre-Ch3 cleanup commit. The remainder happens once Phase 4 switches to closure-bound tools.

- [ ] **5.1** Delete `request_container_var` from `src/app/lib/di.py` (keep `worker_container_var`).
- [ ] **5.2** Delete `_resolve_request_container` from `src/app/domain/chat/services/adk.py`.
- [ ] **5.3** Delete module-level `search_products_by_vector`, `get_product_details` from `adk.py`.
- [ ] **5.4** Delete `ALL_TOOLS` constant from `adk.py`.
- [x] **5.5** ~~`IntentService`, `ExemplarService`, `ExemplarController`, `IntentExemplar` schema, `vector-search-exemplars` / `list-exemplars` named queries deleted.~~
- [ ] **5.6** `grep -rn "from app.lib.di import" src/app/` — confirm only `worker_container_var` references remain.
- [x] **5.7** ~~`BASE_SYSTEM_INSTRUCTION` stripped of the classify-first workflow.~~

### Phase 6: Integration test + verification (`oracledb-vertexai-4d6.3.7`)

- [ ] **6.1** `src/tests/integration/test_chat_workflow.py`:
  - Fixture: real Oracle (already present), mock `genai.Client` to return deterministic responses.
  - Call `ADKRunner.process_request("What's a good dark roast?", ..., persona="enthusiast", tools_service=AgentToolsService(...))`.
  - Assert response dict contains `intent_detected == "PRODUCT_RAG"`, `answer` non-empty, `search_metrics["products_found"] >= 1`.
- [ ] **6.2** Capture latency snapshot: log `response_time_ms` per test run. Assert < 4000 (sanity bound, mocked LLM should be < 100).
- [ ] **6.3** Manual smoke checklist (document outcomes in Beads notes):
  - `uv run coffee run` boots without exceptions.
  - `curl -X POST localhost:5006/api/chat -H "Content-Type: application/json" -d '{"message":"Tell me about Cymbal Espresso","persona":"enthusiast"}'` returns JSON with all 7 keys populated.
- [ ] **6.4** Append to `.agents/patterns.md`: ADK 2.0 workflow pattern (closure-bound tools, parallel fan-out via `asyncio.gather`, `before_agent_callback` credential guard, `text/x.enum` classifier).

---

## Out of Scope (defer to other chapters)

- HITL pause/resume via `RequestInput` — future flow.
- `SQLSpecMemoryService` / `SQLSpecArtifactService` adoption — future flow (Ch 3 only wires sessions).
- Streaming chat (PRD says "not yet canonical").
- Multi-turn agent graphs (sequential workflow only for now).
- Renaming `worker_container_var` to standardize naming — separate cleanup flow.
