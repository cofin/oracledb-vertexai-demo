# Walkthrough

Follow one chat message — *"I need something bold"* — from the moment a
user types it until the grounded reply renders in the browser.

<div class="soft-backdrop-wrapper">

```{image} screenshots/chat_snippet.png
:alt: Cymbal Coffee Chat Snippet
:align: center
```

</div>

The phrase isn't an obvious coffee question. The router has to recognize that
"bold" is an idiom for a dark roast or strong espresso, retrieve matching
products from the menu, and verify whether any off-menu brand was requested —
all in a single Oracle 26ai Hybrid RRF round trip.

The path of this message:

1. The browser opens an SSE stream to `/api/chat/stream`.
2. Vertex AI embeds the question with `gemini-embedding-2` (with an Oracle-backed `embedding_cache` in front).
3. Oracle 26ai executes `hybrid-search-turn`, fusing BM25-style `CONTAINS`/`SCORE` lexical ranking with HNSW `VECTOR_DISTANCE(..., COSINE) FETCH APPROX` across `chat_route`, `product`, and `store` via Reciprocal Rank Fusion ($k=60$).
4. `HybridRouteResolver` resolves the `PRODUCT_RAG` route and product candidates from that single query, checks `hybrid-term-hits` for off-menu nouns, and renders a grounded `final` SSE event.

```{mermaid}
flowchart LR
    B([Browser]) -->|POST /api/chat/stream| C[Litestar controller]
    C --> R[AgentOrchestrationService]
    R --> V[Vertex AI<br/>embedding]
    V --> O[(Oracle 26ai Hybrid RRF<br/>hybrid-search-turn)]
    O --> G[Grounded composer<br/>+ term_hits check]
    G -->|SSE final| B
```

*The whole product-RAG turn in one picture: SSE in, SSE out, with single-query
Hybrid RRF routing, retrieval, and grounded formatting inside the orchestrator.*

## 1. The browser opens an SSE stream

The chat form posts to `/api/chat/stream`. `CoffeeChatController` validates the
message, derives the `(user_id, session_id)` identity from the Litestar session,
and delegates the turn to `AgentOrchestrationService.stream_conversation_turn()`.
Each frame the orchestrator yields becomes one SSE block on the wire.

```{mermaid}
flowchart TD
    F[Chat form] -->|fetch POST| H[stream_chat_message]
    H --> I[validate message]
    H --> S[chat_session_identity]
    H --> R[AgentOrchestrationService.stream_conversation_turn]
    R -. session / delta / final / error .-> H
    H -->|ServerSentEvent| F
```

```{literalinclude} ../src/app/domain/chat/controllers/_chat.py
:language: python
:pyobject: CoffeeChatController.stream_chat_message
:caption: src/app/domain/chat/controllers/_chat.py
```

:::{tour-stop}
The chat controller is intentionally thin. Input validation, CSRF enforcement,
session bridging, and error sanitization happen here; orchestration and
grounding live in `AgentOrchestrationService` and `HybridRouteResolver`.
:::

## 2. Vertex AI embeds the question

The question is sent to Vertex AI's `gemini-embedding-2` model with a
query-purpose instruction prepended to the text. Document embeddings (products
and `chat_route` exemplars) are produced with a document-purpose instruction so
query and document vectors share compatible retrieval geometry. Repeat queries
are short-circuited by the Oracle-backed `embedding_cache`.

```{mermaid}
flowchart TD
    Q["query: I need something bold"] --> CK{embedding_cache hit?}
    CK -- yes --> EV["list[float] · 3072 dims"]
    CK -- no --> V[Vertex AI embed_content]
    V --> EV
    EV --> NX[next stop]
```

```{literalinclude} ../src/app/domain/products/services/_embedding.py
:language: python
:pyobject: VertexAIService.get_text_embedding
:caption: src/app/domain/products/services/_embedding.py
```

:::{agent-detail}
Query/document purpose is not cosmetic. The user question and catalog fixture
text are embedded with different instructions so Oracle compares vectors
generated for compatible retrieval roles.
:::

## 3. Oracle 26ai runs Hybrid RRF routing & retrieval

The 3072-dimension query vector and sanitized Oracle Text query are bound into
named SQL statements under `src/app/db/sql/`. For direct vector search,
Oracle's HNSW index (`INMEMORY NEIGHBOR GRAPH`) uses `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX`:

```{literalinclude} ../src/app/db/sql/products.sql
:language: sql
:start-after: docs:start-vector-search-sql
:end-before: docs:end-vector-search-sql
:caption: src/app/db/sql/products.sql
```

`ProductService.search_by_vector` and `ProductService.search_hybrid` map each
returned row directly into a typed `ProductMatch` `msgspec.Struct`:

```{literalinclude} ../src/app/domain/products/services/_products.py
:language: python
:pyobject: ProductService.search_by_vector
:caption: src/app/domain/products/services/_products.py
```

:::{oracle-internals}
See [Oracle 26ai vector search](concepts/vector-search.md) for the HNSW
index shape and the `vector_memory_size` knob.
:::

## 4. The orchestrator emits a grounded final event

`HybridRouteResolver.resolve_turn` fuses lexical (`CONTAINS`/`SCORE`) and
vector (`VECTOR_DISTANCE`) rankings across `chat_route`, `product`, and
`store` in one query (`hybrid-search-turn`), eliminating a separate LLM
intent-classification round trip:

```{literalinclude} ../src/app/domain/chat/services/_router.py
:language: python
:pyobject: HybridRouteResolver.resolve_turn
:caption: src/app/domain/chat/services/_router.py
```

For `PRODUCT_RAG`, `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, and `ORDER_STATUS`,
the orchestrator formats a deterministic grounded answer from the Oracle rows
and emits the `final` SSE frame. For `GENERAL_CONVERSATION`, execution streams
through the native `AgentRuntime` (`Gemini 3.8 Flash`) with closure-bound tools.

## What's next

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} Concept primers
:link: concepts/vector-search
:link-type: doc

Short pages on vectors in Oracle, Hybrid RRF RAG, native AI runtime routing, and store/map grounding.
:::

:::{grid-item-card} Reference
:link: reference/quickstart
:link-type: doc

Quickstart, the `coffee` CLI, autodoc on `AgentOrchestrationService` and core services,
and a "for the curious" appendix.
:::

::::
