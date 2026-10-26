# Hybrid RRF Routing and Native AI Runtime

A chat turn starts with a single Oracle 26ai Hybrid RRF query, not with an LLM
intent-classification draft. `AgentOrchestrationService`
(`src/app/domain/ai/services/_agent.py`) checks the response cache
(`CacheService` in `src/app/domain/system/services/_cache.py`), embeds the user
message once with `gemini-embedding-2` (`VertexAIService` in
`src/app/domain/products/services/_embedding.py`), and runs `hybrid-search-turn`
(`HybridRouteResolver.resolve_turn` in `src/app/domain/chat/services/_router.py`)
to fuse BM25-style lexical ranking (`CONTAINS`/`SCORE`) with HNSW vector
similarity (`FETCH APPROX`) across `chat_route`, `product`, and `store`.
Deterministic grounded routes render through `GroundedRouteService`
(`src/app/domain/chat/services/_grounded.py`); `GENERAL_CONVERSATION` and
ambiguous turns enter the native `AgentRuntime` loop (`gemini-3.8-flash`).

```{mermaid}
flowchart TD
    Q[user message] --> C{response cache}
    C -->|hit| H[final event]
    C -->|miss| R{HybridRouteResolver<br/>hybrid-search-turn + conditional hybrid-term-hits}
    R -->|PRODUCT_RAG| P[GroundedRouteService<br/>off-menu guard + grounded selection]
    R -->|STORE_LOCATION| S[store distance / city lookup]
    R -->|PRODUCT_AVAILABILITY| A[store_product_inventory lookup]
    R -->|ORDER_STATUS| U[unsupported order response]
    R -->|GENERAL_CONVERSATION| W[Native AgentRuntime<br/>gemini-3.8-flash + grounded tools]
    P --> F[grounded final event]
    S --> F
    A --> F
    U --> F
    W --> F
```

## Grounded Routes

`HybridRouteResolver.resolve_turn` resolves a route label alongside top-ranked
product and store candidates in one `hybrid-search-turn` query (plus a
conditional `hybrid-term-hits` lexical check when quoted or capitalized brand
tokens appear in the prompt):

- `PRODUCT_RAG` for menu, recommendation, roast, price, caffeine, and product
  questions (with off-menu brand pivoting when `hybrid-term-hits` reports zero
  catalog matches).
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

## Native `AgentRuntime` And `CallContext`-Bound Tools

Open-ended turns run through `AgentRuntime.execute_turn()`
(`src/app/domain/ai/runtime/_loop.py`) backed by `GeminiModelClient`
(`src/app/domain/ai/runtime/_model.py`, implementing `ModelClientProtocol` in
`src/app/domain/ai/protocols/_runtime.py` over `google-genai`). `get_coffee_spec_tree()` declares the grounded barista toolset
via `build_coffee_tools` (`src/app/domain/ai/services/_tools.py`):

- `search_products` — single-query Oracle 26ai Hybrid RRF product search
- `get_product_details` — exact product lookup by ID or name
- `find_nearby_stores` — Haversine nearest-store or city/ZIP lookup with keyless Google Maps URLs
- `check_product_availability` — store-level inventory join over `store_product_inventory`
- `check_order_status` — explicit unsupported order-status response

On each turn, `AgentOrchestrationService` passes a request-scoped `CallContext`
(`src/app/domain/ai/runtime/_context.py`) carrying a `CoffeeToolContext`
(`ProductService`, `StoreService`, `VertexAIService`, `MetricsService`, and
`HybridTurnContext`). Each tool records executed named SQL queries
(`sql_phases`), `search_metrics`, `store_results`, `inventory_results`, and
`map_actions` into `ctx.state` (`src/app/domain/chat/services/_telemetry.py`)
for the frontend telemetry badge drawer.

## Streaming Contract

Cached and grounded routes yield normalized `session`, `delta`, and `final` SSE
frames from `AgentOrchestrationService`, while `AgentRuntime` turns stream
through `AgentStreamService.adapt()` (`src/app/domain/ai/runtime/_stream.py`).
Both paths conclude with a single `final` SSE frame carrying the complete turn
payload:

| Field | Meaning |
| --- | --- |
| `type` | Literal frame discriminator (`"final"`) |
| `answer` | The text the user sees |
| `response_time_ms` | End-to-end turn wall-clock duration in milliseconds |
| `intent_detected` | `PRODUCT_RAG` / `GENERAL_CONVERSATION` / `STORE_LOCATION` / `PRODUCT_AVAILABILITY` / `ORDER_STATUS` |
| `from_cache` | Response cache hit |
| `embedding_cache_hit` | Embedding cache hit during retrieval |
| `search_metrics` | `vector_query`, `total_ms`, `embedding_ms`, `oracle_ms`, `ai_ms`, `results_count`, `products_found`, `similarity_scores`, `avg_similarity`, `rrf_scores`, and `lexical_hits` (plus optional `grounded_answer_mode`, `grounded_answer_ms`, `product_query`, and `AgentRuntime` token counters) |
| `sql_phases` | Per-phase SQL timings and row counts rendered as badges in the chat UI |
| `store_results` | Store rows for location turns |
| `inventory_results` | Store-product rows for availability turns |
| `map_actions` | No-key Google Maps actions derived from store rows |
| `location_context` | Request-safe location facts, never raw browser coordinates |
| `session_id` | The Oracle `agent_session` identifier bridged from the Litestar browser session |

## Sessions

The Litestar browser session (`app_session`) and the AI conversation session are
separate stores. `CoffeeChatController` bridges them at request time via
`chat_session_identity(request)` (`src/app/domain/chat/_session.py`), persisting
conversation metadata in `agent_session` (`OracleSessionStore`) and
monotonically sequenced turn events in `agent_event` (`OracleEventStore` in
`src/app/domain/ai/runtime/_store.py`). Both stores inherit from
`OracleLoaderService` (`src/app/lib/service.py`) and benefit from SQLSpec
`0.69.0`'s default `fetch_lobs=False` behavior, which returns `CLOB` columns
under 1 GB directly as inline `str` values without locator round-trips.

## Where This Is Used

- **The walkthrough** follows one product-RAG turn through this router: see
  [the walkthrough](../tour.md).
- **RAG** explains how `hybrid-search-turn` and `hybrid-term-hits` ground
  product answers: see [RAG](rag.md).
- **Maps** covers store lookup, availability rows, location opt-in, and Google
  Maps links: see [Cymbal Coffee Maps](../maps.md).
