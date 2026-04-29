# Flow: ADK 2.0 Runner (adk2-runner_20260429)

*Chapter 3 of [cymbal-coffee-reset_20260429](../cymbal-coffee-reset_20260429/prd.md)*
*Beads epic: `oracledb-vertexai-4d6.3` (blocked by Ch 2, blocks Ch 5)*

---

## Specification

### Objective

Rebuild the chat runner on **Google ADK 2.0b1** (`Workflow` / `BaseNode` graph orchestration) and eliminate the slow path from intent classification. The new runner replaces the exemplar-vector intent lookup with a **Gemini 2.5 Flash-Lite enum-classifier**, **dispatched in parallel** with the main agent's response generation via `asyncio.gather` inside a custom `@node`. Perceived intent latency drops from ~150–400ms (embedding + vector top-1) to ~0ms (hidden behind retrieval). The `request_container_var` workaround disappears in favor of **closure-bound tools** built per-request. The `intent_exemplar` table is retained as **offline ground-truth** + a comparison panel on the Ch 4 explore page, fed by a new `uv run app coffee classify-compare` CLI.

### Code Analysis Summary (verified 2026-04-29)

**Critical latent bug discovered during research:**

`request_container_var` (defined `src/py/app/lib/di.py:45`) is **never `.set()` anywhere in the codebase** — verified via `grep -rn "request_container_var.set\|request_container_var ="`. Every ADK tool invocation falls into the `else` branch of `_resolve_request_container` (`src/py/app/domain/chat/services/adk.py:104-131`) and **constructs a fresh Dishka `AsyncContainer` per call**. With up to 3 tools per chat turn this is 3 container builds + 3 fresh Oracle sessions per request. The Ch 3 rewrite erases the entire mechanism.

**Current runner shape (`src/py/app/domain/chat/services/adk.py:135-160`):**

- Constructor takes `SQLSpecSessionService` (sqlspec ADK extension — already correct).
- Builds one `LlmAgent(name="CoffeeAssistant", instruction=BASE_SYSTEM_INSTRUCTION, model=settings.vertex_ai.CHAT_MODEL, tools=ALL_TOOLS)` at construction time.
- Wraps it in `Runner(agent=agent, app_name="coffee-assistant", session_service=session_service)`.
- `process_request` composes persona overlay by **string-concatenating into the user turn** (`f"[System Context: {persona_instruction}]\n\nUser Query: {query}"`) — the persona never reaches `LlmAgent.instruction`.
- Returns `{"answer", "session_id", "response_time_ms"}`. The `intent_detected`, `search_metrics`, `from_cache`, `embedding_cache_hit` keys the controller expects (`controllers.py:94-97`) default to empty/false because the runner never emits them.

**Current intent classifier:**

- `IntentService.classify_intent(query)` (`adk.py:45-61`): `vertex_ai.get_text_embedding(query)` → `exemplar.search_similar_intents(embedding, limit=1)` → returns top-1 intent regardless of similarity threshold.
- Exposed as an ADK tool the LLM may call. `BASE_SYSTEM_INSTRUCTION` *insists* it run first, but compliance is at LLM discretion. **Hot-path latency: one embedding call + one Oracle vector top-1 query + one extra LLM round trip** (tool call → summary → final response).

**Persona system (`src/py/app/domain/system/services/services.py:35-129`):**

- `PersonaConfig` (msgspec): `name`, `description`, `language_style`, `focus_areas`, `example_responses`, `system_prompt_addon`, `temperature`, `complexity_level`.
- 4 personas: `novice`, `enthusiast` (default), `expert`, `barista`.
- `temperature` and `complexity_level` are **defined but never threaded into `LlmAgent`**.

**Credential guard (`controllers.py:77-83`):** brittle string match (`"API key" in str(exc) or "credentials" in str(exc).lower()`) on `ValueError`. Replace with typed exception `AIServiceUnconfigured`.

**ADK store wiring (`domain/chat/services/__init__.py:24-37`):** `OracleAsyncADKStore(config)` + `SQLSpecSessionService(store)` already provided as APP-singletons. Missing: `await store.ensure_tables()` at startup.

### ADK 2.0b1 contract (verified against adk.dev + PyPI 2026-04-21):

- Pin: `google-adk==2.0.0b1`. Backwards-compatible with 1.x `LlmAgent`.
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

1. `pyproject.toml` pins `google-adk==2.0.0b1` (Ch 1 sets the version; Ch 3 actually uses it).
2. New `src/py/app/domain/chat/services/workflow.py` defines an ADK 2.0 `Workflow` with one custom `@node` (`classify_and_respond`) that fans out **`intent_node`** (Gemini Flash-Lite enum classifier) and **`coffee_turn`** (the `LlmAgent` response) via `asyncio.gather`.
3. New `src/py/app/domain/chat/services/classifier.py` exposes `FlashLiteIntentClassifier` with `async classify(phrase: str) -> Intent` using `text/x.enum` structured output.
4. `ADKRunner.process_request` becomes:
   - Resolve services via Dishka at the controller layer; pass them in.
   - Build the per-request `LlmAgent` with **closure-bound tools** (no module-level functions, no `request_container_var`).
   - Construct the `Workflow` for this turn; invoke via `Runner.run_async`.
   - Return `{"answer", "session_id", "response_time_ms", "intent_detected", "search_metrics", "from_cache", "embedding_cache_hit"}` with all keys populated.
5. Persona overlay flows into `LlmAgent(instruction=composed_prompt, generate_content_config=GenerateContentConfig(temperature=persona.temperature))` — `temperature` is finally honored.
6. `request_container_var` and `_resolve_request_container` are deleted; module-level tool functions (`search_products_by_vector`, `get_product_details`, `classify_intent`) are deleted.
7. `before_agent_callback` on the `LlmAgent` runs the credential guard — returns `types.Content(parts=[Part(text="...")])` with the 503 message text when the Vertex client can't be initialized; controller maps the response to HTTP 503 via a typed `AIServiceUnconfigured` exception path.
8. App startup hook (`src/py/app/server/asgi.py`) calls `await store.ensure_tables()` so the demo boots without `uv run app db upgrade` for ADK session DDL.
9. `BASE_SYSTEM_INSTRUCTION` (in `domain/system/services/services.py`) is rewritten to **drop the "ALWAYS call classify_intent first" prose** — the workflow enforces it now.
10. New CLI `uv run app coffee classify-compare` runs both classifiers (legacy vector + new Flash-Lite) on every `intent_exemplar` row, emits a JSON confusion matrix to `dist/classify-compare.json`, and prints a per-intent precision/recall summary. **Ch 4 reads this JSON for the comparison chart.**
11. New integration test `tests/integration/test_chat_workflow.py` asserts (a) `intent_detected` is one of the enum values, (b) `answer` is non-empty, (c) `response_time_ms < 4000` (95th pct expectation; widen if needed).
12. New unit test `tests/unit/test_classifier_compare.py` mocks the genai client and verifies the CLI emits well-formed confusion-matrix JSON.

### Acceptance Criteria

- `grep -rn "request_container_var" src/py/app/` returns **zero** hits.
- `grep -rn "_resolve_request_container" src/py/app/` returns **zero** hits.
- `python -c "from app.domain.chat.services.workflow import make_workflow; print(make_workflow.__doc__)"` runs without ImportError.
- `uv run app coffee classify-compare --limit 50` exits 0, writes `<repo-root>/dist/classify-compare.json` with 50 rows shaped `{phrase, gold, legacy, new}`. Precision/recall numbers are logged to Beads notes for human review (no hard numeric gate — bootstrap labels are not academic ground truth).
- Manual `POST /api/chat` returns response within 4 seconds; response includes populated `intent_detected`, `search_metrics`, `from_cache`, `embedding_cache_hit`.
- App boot logs include `ADKStore.ensure_tables() OK` (or equivalent).
- `make lint && make test` green; `pytest src/py/tests/integration/test_chat_workflow.py -v` passes.
- A repro of the *old* slow-path is impossible — searching for the `else: container = make_litestar_container()` branch in `adk.py` yields no match.

### Risks / Known Gotchas

- **ADK 2.0b1 is beta.** Pin exactly. API churn risk: isolate every `from google.adk` import inside `domain/chat/services/workflow.py` and `adk.py` so a future `2.0.0b2` only touches those two files.
- **`session.state` is JSON-persisted via `SQLSpecSessionService`.** Do NOT stash Dishka containers, drivers, or any non-serializable object there. Use closure-bound tools.
- **`text/x.enum` requires `gemini-2.5-flash-lite` or newer.** Pin `settings.vertex_ai.INTENT_MODEL = "gemini-2.5-flash-lite"`.
- **Per-turn `LlmAgent` construction is cheap** (Pydantic init only). The expensive call is the model invocation. Don't micro-optimize agent caching.
- **`worker_container_var` (used by SAQ in `lib/di.py:74`) must remain.** Only delete `request_container_var`, not the worker variant.
- **`store.ensure_tables()` adds 30–100ms to first boot** issuing idempotent `CREATE TABLE IF NOT EXISTS`. Acceptable for a reference demo.
- **Confusion-matrix comparison uses `intent_exemplar.intent` as gold** — this is bootstrap data, not human-labeled. Document this in `classify-compare` output: agreement, not academic accuracy.

---

## Implementation Plan

### Phase 0: API surface verification (`oracledb-vertexai-4d6.3.0`)

- [ ] **0.1** After Ch 1 has bumped `google-adk==2.0.0b1`, run a smoke import: `uv run python -c "from google.adk import Workflow, Runner, Context; from google.adk.workflow import node, BaseNode; print('ADK 2.0 surface OK')"`. **If any import fails, halt and re-research the actual 2.0b1 module layout** — do not proceed to Phase 1+ guessing names. Update the snippets in Phases 2–4 to match the verified surface.
- [ ] **0.2** Same smoke for `Runner` accepting a workflow root: build a trivial `Workflow(name="t", edges=[("START", noop)])` and call `Runner(agent=workflow, app_name="t", session_service=mock).run_async(...)`. Confirm `agent=` is the right kwarg (vs `workflow=` or `root=`); record the correct kwarg in Beads notes and update Phase 4.1c accordingly.
- [ ] **0.3** Confirm `gemini-2.5-flash-lite` accepts `response_mime_type="text/x.enum"` with `response_schema={"type": "STRING", "enum": [...]}` via a one-shot `client.aio.models.generate_content(...)` call against a real Vertex/AI Studio key. Record sample output (`response.text`) in Beads notes.

### Phase 1: ADK store + startup hooks (`oracledb-vertexai-4d6.3.1`)

- [ ] **1.1** `src/py/app/config.py`: extend `OracleAsyncConfig` with `extension_config={"adk": {"session_table": "adk_sessions", "events_table": "adk_events", "memory_table": "adk_memory_entries"}}`.
- [ ] **1.2** `src/py/app/server/asgi.py` (or `core.py`): add a Litestar `on_startup` hook that resolves `OracleAsyncADKStore` from the container and calls `await store.ensure_tables()`. Log success/failure at INFO.
- [ ] **1.3** Inspect `src/py/app/db/migrations/` for any `*adk*.sql` file. If present (`ls src/py/app/db/migrations/*adk* 2>/dev/null`): delete it — `ensure_tables()` at startup is now the canonical bootstrap. If absent: no-op; document in Beads notes that the bootstrap is purely runtime.

### Phase 2: Flash-Lite enum classifier (`oracledb-vertexai-4d6.3.2`)

- [ ] **2.1** Create `src/py/app/domain/chat/services/classifier.py`:
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
- [ ] **2.2** Add `INTENT_MODEL: str = "gemini-2.5-flash-lite"` to `settings.vertex_ai`.
- [ ] **2.3** Wire `FlashLiteIntentClassifier` into the APP-scoped `provide_intent_classifier` slot **already reserved** by Ch 2 in `IntegrationsProvider` (`src/py/app/ioc.py`). The provider depends on `genai.Client` from the same provider; signature: `def provide_intent_classifier(self, client: genai.Client) -> FlashLiteIntentClassifier: return FlashLiteIntentClassifier(client, model=settings.vertex_ai.INTENT_MODEL)`.
- [ ] **2.4** Unit test `tests/unit/test_classifier.py` — mock `client.aio.models.generate_content` to return `MagicMock(text="PRODUCT_RAG")`; assert classifier returns the enum.

### Phase 3: Workflow + parallel fan-out (`oracledb-vertexai-4d6.3.3`)

- [ ] **3.1** Create `src/py/app/domain/chat/services/workflow.py`:
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
- [ ] **3.2** Unit test `tests/unit/test_workflow_factory.py` — mock classifier + agent, run the workflow, assert dict shape.

### Phase 4: ADKRunner rewrite (`oracledb-vertexai-4d6.3.4`)

- [ ] **4.1a** Replace the constructor in `src/py/app/domain/chat/services/adk.py:ADKRunner.__init__`: `def __init__(self, session_service: SQLSpecSessionService, classifier: FlashLiteIntentClassifier, persona_manager: PersonaManager)`. Store all three on `self._...`. Delete any old construction-time `LlmAgent` / `Runner` setup (now per-request).
- [ ] **4.1b** Add a private helper `_make_tool_factories(tools_service: AgentToolsService) -> list[Callable]` that returns closure-bound `search_products_by_vector` and `get_product_details` async functions. No module-level tool functions remain.
- [ ] **4.1c** Add a private helper `_build_workflow(self, instruction: str, temperature: float, tools: list[Callable]) -> Workflow`:
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
  Pin the `Runner` kwarg name (`agent=` vs `workflow=` vs `root=`) to whichever Phase 0.2 verified.
- [ ] **4.1d** Rewrite `process_request(query, user_id, session_id, persona, tools_service)` to: resolve persona+temperature, build tools via 4.1b, build workflow via 4.1c, instantiate `Runner(agent=workflow, app_name="coffee-assistant", session_service=self._session_service)`, call `run_async(user_id, session.id, new_message=Content(role="user", parts=[Part(text=query)]))`, aggregate events, and return the populated `ChatResult` dict (all 7 keys).
- [ ] **4.2** Add `credential_guard_callback(callback_context: CallbackContext) -> Optional[types.Content]` as a **defense-in-depth** that returns the 503-text `Content` when invoked with an unconfigured client — short-circuits the agent. **The primary path is controller pre-flight:** wrap the `runner.process_request` call in `controllers.py` with a try that catches `genai.errors.ClientError`/`ValueError` from `genai.Client(...)` resolution and raises `AIServiceUnconfigured`. The callback is the safety net if pre-flight slips through.
- [ ] **4.3** Define `class AIServiceUnconfigured(Exception)` in `src/py/app/domain/chat/exceptions.py`. Update `controllers.py:77-83` to catch this typed exception and return `HTTPException(status_code=503, detail="AI service is not configured. Set GOOGLE_API_KEY or VERTEX_AI_API_KEY in your .env file.")`. Delete the string-match block.
- [ ] **4.4** Update `IntegrationsProvider.provide_adk_runner` (Ch 2 created the slot): now depends on `(session_service, classifier, persona_manager)` — no code change here if Ch 2 already wired it; sanity-check.

### Phase 5: Cleanup of pre-2.0 workarounds (`oracledb-vertexai-4d6.3.5`)

- [ ] **5.1** Delete `request_container_var` from `src/py/app/lib/di.py` (keep `worker_container_var`).
- [ ] **5.2** Delete `_resolve_request_container` from `src/py/app/domain/chat/services/adk.py`.
- [ ] **5.3** Delete module-level `search_products_by_vector`, `get_product_details`, `classify_intent` functions from `adk.py`.
- [ ] **5.4** Delete `ALL_TOOLS` constant from `adk.py`.
- [ ] **5.5** Delete `IntentService` class from `adk.py` — no longer used at request time. (`ExemplarService` remains for Ch 4 / classify-compare.)
- [ ] **5.6** `grep -rn "from app.lib.di import" src/py/app/` — confirm only `worker_container_var` references remain.
- [ ] **5.7** Update `BASE_SYSTEM_INSTRUCTION` in `domain/system/services/services.py`: drop the "MANDATORY WORKFLOW: ALWAYS call classify_intent first" block. Keep persona+tone scaffolding only.

### Phase 6: classify-compare CLI (`oracledb-vertexai-4d6.3.6`)

- [ ] **6.1** Add `coffee classify-compare` subcommand in `src/py/app/cli/commands.py`. **Output path contract:** default `--output` is `dist/classify-compare.json` resolved from repo root (`Path.cwd() / "dist" / "classify-compare.json"`); ensure `dist/` is created if missing. Ch 4 reads from this exact path.
  ```python
  @coffee_demo_group.command(name="classify-compare")
  @click.option("--limit", default=0)
  @click.option("--output", type=click.Path(), default="dist/classify-compare.json")
  def classify_compare(limit: int, output: str) -> None:
      from sqlspec.utils.sync_tools import run_
      async def _run():
          # resolve driver, exemplar service, classifier, vertex_ai service
          # for each row in intent_exemplar (limited): legacy_pred = vector top-1; new_pred = classifier.classify(phrase)
          # write JSON [{phrase, gold, legacy, new}, ...]
          # compute & print confusion matrix
      run_(_run)
  ```
- [ ] **6.2** Helper `_render_matrix(rows: list[dict]) -> None` prints a 2-column matrix per intent with precision/recall.
- [ ] **6.3** Unit test `tests/unit/test_classify_compare.py`: monkeypatch the classifier + DB rows, invoke the click command in-process, assert JSON output shape and matrix print.

### Phase 7: Integration test + verification (`oracledb-vertexai-4d6.3.7`)

- [ ] **7.1** `tests/integration/test_chat_workflow.py`:
  - Fixture: real Oracle (already present), mock `genai.Client` to return deterministic responses.
  - Call `ADKRunner.process_request("What's a good dark roast?", ..., persona="enthusiast", tools_service=AgentToolsService(...))`.
  - Assert response dict contains `intent_detected == "PRODUCT_RAG"`, `answer` non-empty, `search_metrics["products_found"] >= 1`.
- [ ] **7.2** Capture latency snapshot: log `response_time_ms` per test run. Assert < 4000 (sanity bound, mocked LLM should be < 100).
- [ ] **7.3** Manual smoke checklist (document outcomes in Beads notes):
  - `uv run app run` boots without exceptions.
  - Browser: `/` loads chat (Ch 4 page; Ch 3 acceptance is a curl test).
  - `curl -X POST localhost:5006/api/chat -H "Content-Type: application/json" -d '{"message":"Tell me about Cymbal Espresso","persona":"enthusiast"}'` returns JSON with all 7 keys populated.
  - `uv run app coffee classify-compare --limit 100` produces a confusion matrix.
- [ ] **7.4** Append to `.agents/patterns.md`: ADK 2.0 workflow pattern (closure-bound tools, parallel fan-out via `asyncio.gather`, `before_agent_callback` credential guard, `text/x.enum` classifier).

---

## Out of Scope (defer to other chapters)

- Frontend explore-page comparison chart for `classify-compare` output — Ch 4.
- HITL pause/resume via `RequestInput` — future flow.
- `SQLSpecMemoryService` / `SQLSpecArtifactService` adoption — future flow (Ch 3 only wires sessions).
- Streaming chat (PRD says "not yet canonical").
- Multi-turn agent graphs (sequential workflow only for now).
- Renaming `worker_container_var` to standardize naming — separate cleanup flow.
