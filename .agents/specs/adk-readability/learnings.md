# Learnings: adk-readability (Ch6)

## PRODUCT_RAG relabel is load-bearing — fold, never delete

`stream_request` has two PRODUCT_RAG paths and only one is the deterministic
route:

- Direct route: `classify() == PRODUCT_RAG` -> `_deterministic_route_event` ->
  `_product_rag_event`, returns before the ADK fan-out (`Runner` never runs).
- Relabel-after-fanout: `classify()` returned `GENERAL_CONVERSATION`, but the
  model actually called the vector tool, so `_effective_intent` (which checks
  `search_metrics.vector_query` / `results_count` / the
  `vector-search-products` sql_key via `_product_lookup_ran`) relabels the turn
  to `PRODUCT_RAG`. The fan-out tail then re-grounds the answer/metrics from the
  recorded lookup via `_ground_product_rag_turn`.

The relabel re-ground is the ONLY PRODUCT_RAG handling on the fan-out path and
is reached exclusively via the relabel — it is not a duplicate of the direct
route. Keep it (now in `_general_conversation_event`). Two mocked unit parity
tests gate this: `test_product_rag_stream_does_not_emit_speculative_model_delta`
(direct) and `test_general_conversation_relabels_to_product_rag_after_tool_lookup`
(relabel).

## Folding `_adk_*` helpers: watch the grounding -> telemetry edge

`_adk_grounding.py` imports `_coerce_sql_phases` from the telemetry helpers, so a
flat fold of telemetry into `adk.py` would cycle (`adk` -> `_adk_grounding` ->
`adk`). Resolution: one `_adk_support.py` that holds both the history and
telemetry helpers and that BOTH `adk.py` and `_adk_grounding.py` import. Three
orbiting `_adk_*` modules -> two (`_adk_support`, `_adk_grounding`).

## One `_final_event` builder for the canonical 12-key final dict

Every chat route returns the same `{"type": "final", ...}` shape (13 keys incl.
`type`). A single keyword-only `_final_event(...)` with the four route fields
defaulting to empty lists + `_safe_location_context(location_context)`
reproduces all six former hand-written dicts byte-for-byte (verified key order +
values). `_default_route_fields` became dead after this and was deleted.

## Linearizing past PLR0914

Inlining the single-call privates raised `stream_request`'s local count above
the ruff PLR0914 threshold once the `# noqa` was removed. Extracting the
general-conversation fan-out into its own async-generator method
(`_general_conversation_event`) — the natural "third linear exit" — kept
`stream_request` short (cache short-circuit, deterministic route, delegate) and
both methods under 15 locals without a `noqa`.

## Cache is snake_case only

`_cached_response_event` previously read camelCase-or-snake_case for every cached
field. The cache is written only by this app (`_product_rag_event` and the
general-conversation tail) in snake_case, so the camelCase arm was dead. Read
snake_case only.
