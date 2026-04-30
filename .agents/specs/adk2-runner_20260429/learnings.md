# Learnings: adk2-runner_20260429

> Notes captured during implementation. Synced from Beads task notes via `/flow:sync`.

_No implementation notes yet — chapter not started._

## Pre-implementation findings (planning phase, 2026-04-29)

- **Latent bug:** `request_container_var` is **never `.set()` anywhere in the codebase**. Every chat tool invocation today builds a brand-new Dishka container from scratch. Verified via `grep -rn "request_container_var.set\|request_container_var ="`. Ch 3's switch to closure-bound tools fixes this incidentally.
- ADK 2.0b1 is **backwards-compatible with 1.x `LlmAgent`** — we don't have to rewrite tools, only the runner. `Workflow(edges=[("START", node)])` accepts a single entry node and `Runner` accepts the workflow root.
- **Parallel fan-out idiom:** `asyncio.gather(ctx.run_node(node_a, ...), ctx.run_node(node_b, ...))` inside a custom `@node` is preferred over `ParallelAgent` when branches return heterogeneous shapes (intent label vs full agent answer).
- **`text/x.enum` mode** requires Gemini 2.5 Flash-Lite or newer; the response is a plain enum-value string in `response.text`, not a JSON-parsed Enum instance.
- `before_agent_callback` returning a non-`None` `types.Content` short-circuits the agent **before** any LLM call. Right place for the 503 credential guard.
- The persona system already has `temperature` and `complexity_level` fields that go nowhere — `LlmAgent(generate_content_config=GenerateContentConfig(temperature=...))` finally honors them post-rewrite.
- `intent_exemplar` retains value as **offline ground truth** for the new live classifier; the new `classify-eval` CLI outputs JSON that Ch 4 charts as a comparison panel.

## Phase 2 (2026-04-30)

### `4d6.3.3` Flash-Lite intent classifier — implementation [e48d80e]

- **Spec misnumbering caught at claim time:** spec.md heading says `oracledb-vertexai-4d6.3.2` for Phase 2, but Beads has the classifier task at `4d6.3.3` (`4d6.3.2` was the `ext_adk_0001` no-op). Beads is source of truth; spec heading kept as-is per "preserve spec content" sync rule.
- **`provide_intent_classifier` slot was NOT pre-reserved by Ch 2.** Spec line 150 asserted otherwise — wrong. Added from scratch as a new `@provide(scope=APP)` method on `IntegrationsProvider`, depending only on `google.genai.Client`. No conflict with `provide_adk_runner` (Phase 4 will rewire that to depend on the classifier).
- **`INTENT_MODEL` is a separate setting from `CHAT_MODEL`** because Flash-Lite is purpose-fit for cheap single-call classification while `CHAT_MODEL` (`gemini-3-flash-latest`) handles tool-calling RAG. Override via `VERTEX_AI_INTENT_MODEL` env var.
- **Test surface follows `test_adk2_surface_pin.py:80-87` exactly** — same `response_mime_type="text/x.enum"`, same `response_schema={"type": "STRING", "enum": INTENT_VALUES}` shape captured from `generate_content` kwargs.
- **No defensive fallback for unknown enum text:** classifier raises `ValueError` if Gemini ever returns a non-enum string. Per the no-backwards-compat-shims rule + because Phase 4 controllers will wrap the runner call in `AIServiceUnconfigured` translation. Pinned by `test_classifier_raises_on_unknown_label`.
- **Live `text/x.enum` smoke still deferred** (Phase 0.3) — needs `GOOGLE_API_KEY` or `VERTEX_AI_API_KEY` in env.

## Phase 3 (2026-04-30)

### `4d6.3.4` Coffee workflow with parallel fan-out — implementation [a5f6da6]

- **`@node` decorator does not expose `parameter_binding=`.** Verified — its kwargs are `name, rerun_on_resume, retry_config, timeout, parallel_worker, auth_config`. Default is `'state'`, but Phase 4 invokes nodes as `ctx.run_node(node, user_query)` — that pattern needs `parameter_binding='node_input'`. **Resolution:** dropped the `@node(name=...)` wrapper from spec lines 163-188 and constructed `FunctionNode(func=..., name=..., parameter_binding='node_input')` directly in `workflow.py`. Spec example needs a sync touch-up.
- **`from __future__ import annotations` interacts with `FunctionNode` introspection.** `FunctionNode` builds an `input_schema` from the wrapped function's signature via runtime type-hint resolution. Forward-only annotations (e.g. `Context` only inside `TYPE_CHECKING`) cause `NameError` during `FunctionNode(func=...)` construction. Imported `Context` at runtime; left `LlmAgent` and `FlashLiteIntentClassifier` in `TYPE_CHECKING` since they only annotate the public factory signatures, not the inner `func`.
- **`Workflow.edges` accepts the literal `("START", node)` tuple form.** Confirmed via Pydantic field introspection — the discriminated union allows `Literal['START']` as the source endpoint. No need to import a `START` constant.
- **`FunctionNode._func` is the canonical handle** for direct unit-test invocation without a real `Context`. Pattern in `test_workflow_factory.py`: `await intent._func(ctx=MagicMock(), user_query="...")` — bypasses `_bind_parameters` and event normalization, exercises only the closure body.
- **`asyncio.gather` ordering is preserved** in the fan-out's return mapping: `intent_label, answer = await asyncio.gather(intent, coffee)` — `intent_label` is always the first awaitable's result. The dict assembly relies on positional order; pinned by `test_classify_and_respond_func_runs_intent_and_coffee_in_parallel`.

## Phase 4 (2026-04-30)

### `4d6.3.5` ADKRunner rewrite with closure-bound tools — implementation [d35d3e4]

- **Spec slot mismatch (round 2):** Phase 4 in the spec is labeled `oracledb-vertexai-4d6.3.4` but in Beads it's `4d6.3.5` (Beads `4d6.3.4` is the Phase 3 workflow factory that just shipped). Beads is source of truth; spec heading kept as-is.
- **`PersonaManager` is class-only with `@classmethod get_system_prompt`.** The spec line 4.1a wants the runner to receive a `persona_manager` param. Resolved by adding `PersonaManager.get_temperature(persona_key) -> float` as a classmethod (so MagicMock-friendly during tests + clean instance access in production), then APP-scoping `PersonaManager()` in `IntegrationsProvider.provide_persona_manager`. The runner calls `self._persona_manager.get_system_prompt(...)` and `self._persona_manager.get_temperature(...)` — both classmethods work on instances.
- **Closure metric capture pattern:** `_make_tool_factories(tools_service, metric_state)` takes a mutable dict the closure mutates on each tool call. `process_request` reads `metric_state["embedding_cache_hit"]` after the workflow finishes. Cleaner than session-state-stuffing for non-serializable runtime state.
- **Intent extraction via `session.state`:** the workflow's `classify_and_respond` node returns `{"answer": ..., "intent": ...}`; `Runner.run_async` persists this into `session.state` via `SQLSpecSessionService`. After the event loop completes, `process_request` reads `session.state["intent"]` directly (defaults to `GENERAL_CONVERSATION` when state is empty/missing). This avoids needing to introspect ADK event payloads.
- **`from __future__ import annotations` is safe in `adk.py`** because Dishka resolves `AgentToolsService` constructor types via `get_type_hints` (which honors deferred annotations) — but only because the runtime imports of `ProductService`/`StoreService`/`VertexAIService`/`MetricsService` remain at module top-level. Moving them to `TYPE_CHECKING` would break Dishka resolution. Pinned by `test_domain_service_provider_request_scoped` continuing to pass.
- **Credential error mapping pattern:** `genai.errors.ClientError` extends `APIError` extends `Exception` (NOT `ValueError`); credential ValueErrors raised inside `genai.Client(...)` initialization extend `ValueError` directly. The runner catches both with `except (genai_errors.ClientError, ValueError)` and re-raises as `AIServiceUnconfigured` only when `_is_credential_error(exc)` matches (`isinstance ClientError` OR substring "api key"/"credentials"). Pinned by `test_process_request_raises_ai_service_unconfigured_on_credential_error`.
- **`credential_guard_callback` is defense-in-depth, not the primary path.** It checks `settings.vertex_ai.PROJECT_ID or settings.vertex_ai.API_KEY`; returns `types.Content(role="model", parts=[Part(text="...")])` to short-circuit the agent if config is missing. The primary path is the controller catching `AIServiceUnconfigured` and returning HTTP 503 — the callback only fires if pre-flight slips through.
- **Pre-existing API test failures (`test_chat_partial.py`) are infrastructure-side**, not regressions: they require a running Oracle, which the conftest hardcodes to `localhost:1521` rather than spinning one via `pytest_databases.docker.oracle`. Same 3 tests fail on the pre-Phase-4 tree. Out of scope for Phase 4.

## Phase 5 (2026-04-30)

### `4d6.3.6` Delete pre-2.0 workarounds — implementation [59c760d]

- **Scope expanded by user direction.** Audit found that `request_container_var` was one of *four* dead families in `app.lib.di`: (1) `request_container_var` + its only consumer `job_inject` (zero `@job_inject` callers), (2) `worker_container_var` + `worker_scope` (zero `worker_scope()` callers), (3) `with_websocket_request` + `get_from_connection` (zero callers), (4) `WebSocketScope` + `provide_websocket_scope` (zero callers). User confirmed deletion of all four after planned-spec audit cross-checked against PRD scope.
- **Spec line 91 `worker_container_var` "must remain" overruled by PRD scope.** `prune-and-document_20260429/spec.md:241` lists "SAQ/background workers, streaming chat" as out-of-scope. With SAQ ruled out and zero callers, preserving worker plumbing is dead-code-keeping, not forward compatibility. The cautious "keep the worker variant" guidance in the adk2-runner spec was written before the prune-and-document PRD locked scope.
- **No SSE / WebSocket in the chat path.** `pages/chat.html.j2:40-42` is plain `hx-post="/api/chat"` → `hx-target="#messages"` → `hx-swap="beforeend"`. The `ADKRunner.process_request` collects all `runner.run_async` events into one string before returning a single `HTMXTemplate(partials/_chat_response.html.j2)` swap. "Live" feel comes from polling (`hx-trigger="every 10s"` on metrics summary in `pages/explore.html.j2:72`) and OOB swaps for flash/metrics badges.
- **`async_inject` simplification.** Dropped the `worker_container_var.set()` / `request_container_var.set()` ContextVar shuffle. New body opens a single Dishka REQUEST scope on the made container, resolves type-hint kwargs, runs `func`, closes the container. `Scope` re-export removed from `lib/di.py` since cli/utils.py now imports it directly from `dishka` (matching ioc.py's pattern).
- **Live `lib/di.py` surface frozen by architectural test.** `test_di_module.py` parametrizes `DEAD_NAMES` (8 names) across `hasattr` + `__all__` + `cli/utils.py` source-grep checks; `test_di_module_exports_live_surface` pins the surviving 7-name `__all__`. Anyone re-introducing the deleted helpers fails the suite.
- **Stale spec text retained per "PRESERVE SPEC CONTENT" sync rule.** Spec line 217 still says "(keep `worker_container_var`)" and line 245 still references "Renaming `worker_container_var`" — both moot now. The sync-discipline rule is to flip markers and append learnings, not rewrite requirements; the drift is documented here instead.
- **Net delta: -268 / +68 lines** across `lib/di.py`, `cli/utils.py`, plus 56 lines of new test. `lib/di.py` shrank from 275 lines (10 helpers, 4 ContextVars, 1 dataclass) to 32 lines (1 ContextVar, 1 dataclass, 5 re-exports).
