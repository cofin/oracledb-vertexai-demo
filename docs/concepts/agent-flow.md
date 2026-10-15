# Hybrid RRF Routing and Native AI Runtime

A chat turn starts with a single Oracle 26ai Hybrid RRF query, not with an LLM
intent-classification draft. `AgentOrchestrationService` checks the response
cache, embeds the user message once with `gemini-embedding-2`, and runs
`hybrid-search-turn` (`HybridRouteResolver.resolve_turn`) to fuse BM25-style
lexical ranking (`CONTAINS`/`SCORE`) with HNSW vector similarity (`FETCH APPROX`)
across `chat_route`, `product`, and `store`. Grounded routes render
directly from the returned rows; only `GENERAL_CONVERSATION` enters the native
`AgentRuntime` loop (`Gemini 3.8 Flash`).

```{mermaid}
flowchart TD
    Q[user message] --> C{response cache}
    C -->|hit| H[final event]
    C -->|miss| R{Hybrid RRF<br/>hybrid-search-turn}
    R -->|PRODUCT_RAG| P[grounded product composer<br/>+ hybrid-term-hits off-menu guard]
    R -->|STORE_LOCATION| S[store distance / city lookup]
    R -->|PRODUCT_AVAILABILITY| A[store_product_inventory lookup]
    R -->|ORDER_STATUS| U[unsupported order response]
    R -->|GENERAL_CONVERSATION| W[Native AgentRuntime<br/>Gemini 3.8 Flash + 5 tools]
    P --> F[grounded final event]
    S --> F
    A --> F
    U --> F
    W --> F
```

## Grounded Routes

`HybridRouteResolver.resolve_turn` resolves one of five route labels alongside
top-ranked product and store candidates in a single Oracle round trip:

- `PRODUCT_RAG` for menu, recommendation, roast, price, caffeine, and product
  questions (including off-menu brand detection via `hybrid-term-hits`).
- `STORE_LOCATION` for store, address, hours, nearest-cafe, and directions
  questions.
- `PRODUCT_AVAILABILITY` for store-level pickup or stock questions.
- `ORDER_STATUS` for order tracking, which this demo explicitly reports as
  unsupported.
- `GENERAL_CONVERSATION` for greetings and open-ended conversation.

```{literalinclude} ../../src/app/domain/chat/services/_router.py
:language: python
:pyobject: HybridRouteResolver.resolve_turn
:caption: src/app/domain/chat/services/_router.py
```

## Native `AgentRuntime` & Closure-Bound Tools

Open-ended turns run through `AgentRuntime.execute_turn()` (`src/app/domain/ai/runtime/_loop.py`)
backed by `GeminiModelClient` (`google-genai`). Each turn binds five request-scoped
tool closures (`build_coffee_tools` in `src/app/domain/ai/services/_tools.py`):

- `search_products` — single-query Oracle 26ai Hybrid RRF product search
- `get_product_details` — exact product lookup by ID or name
- `find_nearby_stores` — Haversine nearest-store or city/ZIP lookup with Google Maps URLs
- `check_product_availability` — store-level inventory join over `store_product_inventory`
- `check_order_status` — explicit unsupported order-status response

Each closure captures the active request's Dishka services and `TurnTelemetryState`,
recording executed named SQL queries (`sql_phases`) for the frontend telemetry badge drawer.

## Streaming Contract

Grounded routes and `AgentRuntime` turns both stream through `AgentStreamService`
and conclude with a single `final` SSE frame carrying the complete `ChatResponse`
contract:

| Field | Meaning |
| --- | --- |
| `answer` | The text the user sees |
| `intent_detected` | `PRODUCT_RAG` / `GENERAL_CONVERSATION` / `STORE_LOCATION` / `PRODUCT_AVAILABILITY` / `ORDER_STATUS` |
| `from_cache` | Response cache hit |
| `embedding_cache_hit` | Embedding cache hit during retrieval |
| `search_metrics` | `embedding_ms`, `oracle_ms`, `ai_ms`, `search_ms`, `results_count`, and similarity scores |
| `sql_phases` | Per-phase SQL timings and row counts rendered as badges in the chat UI |
| `store_results` | Store rows for location turns |
| `inventory_results` | Store-product rows for availability turns |
| `map_actions` | No-key Google Maps actions derived from store rows |
| `location_context` | Request-safe location facts, never raw browser coordinates |
| `session_id` | The Oracle `agent_session` identifier bridged from the Litestar browser session |

## Sessions

The Litestar browser session and the AI conversation session are separate
stores. `CoffeeChatController` bridges them at request time via
`chat_session_identity(request)`, persisting conversation metadata in
`agent_session` (`OracleSessionStore`) and monotonically sequenced turn events
in `agent_event` (`OracleEventStore`).

## Where This Is Used

- **The walkthrough** follows one product-RAG turn through this router: see
  [the walkthrough](../tour.md).
- **RAG** explains how `hybrid-search-turn` and `hybrid-term-hits` ground
  product answers: see [RAG](rag.md).
- **Maps** covers store lookup, availability rows, location opt-in, and Google
  Maps links: see [Cymbal Coffee Maps](../maps.md).
