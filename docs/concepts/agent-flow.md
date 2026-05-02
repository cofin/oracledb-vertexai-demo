# Google ADK

A chat turn isn't one call — it's a small graph. Cymbal Coffee runs intent
classification and the conversational LLM in parallel from the same `START`
node, then converges them at a join. The agent itself decides whether to
fire a vector search via a closure-bound tool. The browser sees one SSE
stream regardless.

```{mermaid}
flowchart TD
    S{ADK START} --> A[LlmAgent coffee_turn]
    S --> I[FunctionNode intent]
    A -- tool call --> O[(Oracle 26ai<br/>vector search)]
    O -- matches --> A
    A --> J((JoinNode))
    I --> J
    J --> M[FunctionNode<br/>classify_and_respond]
    M --> R[Grounded answer]
```

## The graph

`ADKRunner.build_workflow` wires the diagram above into an actual ADK
`Workflow`:

```{literalinclude} ../../src/app/domain/chat/services/workflow.py
:language: python
:start-after: docs:start-workflow-fanout
:end-before: docs:end-workflow-fanout
:caption: src/app/domain/chat/services/workflow.py
```

Two edges leave `START` and both feed the same `JoinNode`. With
`max_concurrency=2`, the classifier and the LLM run on the same Python
event loop and Oracle/Vertex AI calls overlap with the classifier
round-trip. The classifier's latency disappears behind whatever the agent
is doing.

## Why parallel?

The intent classifier is a separate Gemini Flash-Lite call constrained to
a tiny enum (`PRODUCT_RAG`, `GENERAL_CONVERSATION`, `STORE_LOCATION`,
`ORDER_STATUS`). It isn't blocking the answer — it's labelling it for
telemetry and for the deterministic-shortcut path. The agent's own
reasoning is what decides whether to call the vector-search tool.

That separation is intentional:

- The classifier's job is *labelling*, not gating. You want it cheap and
  fast.
- The agent's job is *reasoning*, including reasoning about whether
  retrieval is worth it.
- The runner's job is *grounding*, not generation. For `PRODUCT_RAG` it
  takes a deterministic shortcut and formats the final answer directly
  from product rows.

## Closure-bound tools

ADK passes tools to the LLM as plain async Python callables. Each request
constructs a new closure that captures the request-scoped
`AgentToolsService`, which in turn holds the SQLSpec driver and the
product/cache/metrics/store services. That's how tool calls reach the same
Oracle session as the rest of the request.

A representative tool (the model reads the docstring to decide *when* to
call it):

```python
async def search_products_by_vector(
    query: str,
    limit: int = 5,
    similarity_threshold: float = 0.7,
) -> dict[str, Any]:
    """Search the Cymbal Coffee menu by vector similarity.

    Use for questions about the menu, catalog, drinks, recommendations,
    flavor preferences, availability, decaf substitutions, and idiomatic
    requests like "wake me up" or "what's good today".
    """
    return await tools_service.search_products_by_vector(
        query, limit, similarity_threshold,
    )
```

The phrasing matters. The tool docstring is the tool's prompt — drop
"recommendation" or "decaf" and the model under-routes obvious menu
questions.

## Streaming

For non-RAG turns, the runner streams the LLM's deltas as `ServerSentEvent`
chunks and follows them with a final event. For `PRODUCT_RAG` turns, no
deltas are emitted — the runner classifies, runs product search, formats
the grounded answer, and yields one final event. The browser never sees an
ungrounded draft that gets overwritten.

The event contract on the wire is the same either way:

| Field | Meaning |
| --- | --- |
| `answer` | The text the user sees |
| `intent_detected` | `PRODUCT_RAG` / `GENERAL_CONVERSATION` / `STORE_LOCATION` / `ORDER_STATUS` |
| `from_cache` | Response cache hit |
| `embedding_cache_hit` | Embedding cache hit during retrieval |
| `search_metrics` | `embedding_ms`, `oracle_ms`, `tool_ms`, `results_count` |
| `sql_phases` | Per-phase timings the chat UI shows as badges |
| `session_id` | The ADK session, separate from the Litestar browser session |

## Sessions

The Litestar browser session and the ADK conversation session are separate
stores. The chat controller bridges them by storing `adk_session_id` and
`adk_user_id` on the Litestar session at request time, then passing those
identifiers to the SQLSpec-backed `OracleAsyncADKStore`. ADK owns the
conversational state; Litestar owns the cookie.

## Where this is used

- **The walkthrough** follows one turn through this graph: see
  [the walkthrough](../tour.md).
- **RAG** explains what happens *inside* the tool call when the agent
  decides to fire it: see [RAG](rag.md).
- **The internals appendix** has the parallel-vs-sequential latency
  timeline that shows why the classifier feels free in production: see
  [for the curious](../reference/internals.md).
