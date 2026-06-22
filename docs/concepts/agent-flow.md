# Chat Routing and Google ADK

A chat turn starts with routing, not with a model draft. `ADKRunner` checks the
response cache, asks the Flash-Lite classifier for one intent label, and handles
the grounded routes directly from request-scoped services. Only
`GENERAL_CONVERSATION` falls through to the Google ADK 2.0 workflow.

```{mermaid}
flowchart TD
    Q[user message] --> C{response cache}
    C -->|hit| H[final event]
    C -->|miss| I{Flash-Lite intent}
    I -->|PRODUCT_RAG| P[product vector search]
    P --> PV[structured selection<br/>and validation]
    I -->|STORE_LOCATION| S[store lookup]
    I -->|PRODUCT_AVAILABILITY| A[inventory lookup]
    I -->|ORDER_STATUS| U[unsupported order response]
    I -->|GENERAL_CONVERSATION| W[ADK workflow]
    PV --> F[grounded final event]
    S --> F
    A --> F
    U --> F
    W --> F
```

## Grounded Routes

The classifier returns one enum value:

- `PRODUCT_RAG` for menu, recommendation, roast, price, caffeine, and product
  questions.
- `STORE_LOCATION` for store, address, hours, nearest-cafe, and directions
  questions.
- `PRODUCT_AVAILABILITY` for store-level pickup or stock questions.
- `ORDER_STATUS` for order tracking, which this demo explicitly does not
  implement.
- `GENERAL_CONVERSATION` for greetings and small talk.

The first three labels are grounded routes. They query Oracle through
`AgentToolsService`, shape rows into `store_results`, `inventory_results`,
`map_actions`, metrics, and SQL phases, then emit one `final` event. Product
RAG may use Gemini structured output to select among returned product ids, but
the final product answer is rendered from Oracle rows. `ORDER_STATUS` returns a
clear unsupported message instead of asking the model to invent order data.

## ADK Fallback

General conversation uses a Google ADK `Workflow`. The workflow still fans out
from `START`: one branch runs an `LlmAgent`, and the other runs the same
Flash-Lite classifier as a `FunctionNode` for workflow output labelling.

```{literalinclude} ../../src/app/domain/chat/services/workflow.py
:language: python
:start-after: docs:start-workflow-fanout
:end-before: docs:end-workflow-fanout
:caption: src/app/domain/chat/services/workflow.py
```

The ADK path has the same closure-bound tools as the deterministic path. If
the model calls the product vector-search tool during a general turn, the
runner treats the response as product-grounded and sends it through the same
selector, validator, and row-renderer used by directly-routed Product RAG.

## Closure-Bound Tools

ADK tools are plain async Python callables. Each request builds new closures
that capture the request-scoped `AgentToolsService`, which in turn holds the
SQLSpec driver and the product, store, cache, metrics, and Vertex AI services.
That is how tool calls use the same Oracle session as the rest of the request.

A representative tool:

```python
async def search_products_by_vector(
    query: str,
    limit: int = 5,
    similarity_threshold: float = 0.7,
) -> dict[str, Any]:
    """Search the Cymbal Coffee menu with vector RAG.

    Use for menu, catalog, recommendation, flavor, roast, price, caffeine,
    availability, dietary substitution, and idiomatic preference requests.
    """
    result = await tools_service.search_products_by_vector(
        query, limit, similarity_threshold,
    )
    _record_product_search_result(metric_state, result, query)
    return result
```

The docstring is part of the model contract in the ADK fallback path. The
deterministic route calls the same service method directly.

## Streaming Contract

Grounded routes emit one `final` event. General conversation can emit `delta`
events from ADK before its final event. The final payload uses the same fields
either way:

| Field | Meaning |
| --- | --- |
| `answer` | The text the user sees |
| `intent_detected` | `PRODUCT_RAG` / `GENERAL_CONVERSATION` / `STORE_LOCATION` / `PRODUCT_AVAILABILITY` / `ORDER_STATUS` |
| `from_cache` | Response cache hit |
| `embedding_cache_hit` | Embedding cache hit during retrieval |
| `search_metrics` | `embedding_ms`, `oracle_ms`, `tool_ms`, `results_count`, route-specific fields |
| `sql_phases` | Per-phase timings the chat UI shows as badges |
| `store_results` | Store rows for location turns |
| `inventory_results` | Store-product rows for availability turns |
| `map_actions` | No-key Google Maps actions derived from store rows |
| `location_context` | Request-safe location facts, never raw browser coordinates |
| `session_id` | The ADK session, separate from the Litestar browser session |

## Sessions

The Litestar browser session and the ADK conversation session are separate
stores. The chat controller bridges them by storing `adk_session_id` and
`adk_user_id` on the Litestar session at request time, then passing those
identifiers to the SQLSpec-backed `OracleAsyncADKStore`. ADK owns the
session-backed display history and fallback workflow state; Litestar owns the
browser cookie.

## Where This Is Used

- **The walkthrough** follows one product-RAG turn through this router: see
  [the walkthrough](../tour.md).
- **RAG** explains what happens inside the product vector-search route: see
  [RAG](rag.md).
- **Maps** covers store lookup, availability rows, location opt-in, and Google
  Maps links: see [Cymbal Coffee Maps](../maps.md).
