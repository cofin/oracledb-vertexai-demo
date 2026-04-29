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
