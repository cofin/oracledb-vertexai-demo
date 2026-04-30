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
