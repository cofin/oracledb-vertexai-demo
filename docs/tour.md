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
"bold" is an idiom for a dark roast or strong espresso, then use the
vector-search route against the menu — that's the whole point of the demo.

The path of this message:

1. The browser opens an SSE stream to `/api/chat/stream`.
2. Flash-Lite classifies it as `PRODUCT_RAG`.
3. Vertex AI embeds the question (with an Oracle-backed cache in front).
4. Oracle 26ai's HNSW index returns the closest products.
5. The runner formats one grounded final SSE event.

```{mermaid}
flowchart LR
    B([Browser]) -->|POST /api/chat/stream| C[Litestar controller]
    C --> R[ADKRunner]
    R --> I[Flash-Lite<br/>intent]
    I --> V[Vertex AI<br/>embedding]
    V --> O[(Oracle 26ai<br/>HNSW search)]
    O --> F[Grounded formatter]
    F -->|SSE final| B
```

*The whole product-RAG turn in one picture: SSE in, SSE out, with routing,
retrieval, and answer formatting inside the runner.*

## 1. The browser opens an SSE stream

The chat form posts to `/api/chat/stream`. The controller validates the
message, derives the ADK session identity from the Litestar session, and
hands control to `ADKRunner.stream_request()`. Each event the runner yields
becomes one SSE block on the wire.

```{mermaid}
flowchart TD
    F[Chat form] -->|fetch POST| H[stream_chat_message]
    H --> I[validate message]
    H --> S[adk_session_identity]
    H --> R[ADKRunner.stream_request]
    R -. delta / final / error .-> H
    H -->|ServerSentEvent| F
```

The chat routes live on a Litestar controller. `stream_chat_message` is the
SSE endpoint the form posts to — it validates input, bridges the Litestar
session to an ADK session, then delegates the streaming work to `ADKRunner`.

```{literalinclude} ../src/app/domain/chat/controllers/_chat.py
:language: python
:start-after: docs:start-stream-handler
:end-before: docs:end-stream-handler
:caption: src/app/domain/chat/controllers/_chat.py
```

:::{tour-stop}
The chat controller is intentionally thin. Validation, session bridging, and
error sanitization happen here; everything else is delegated to `ADKRunner`
and the Dishka-injected `AgentToolsService`.
:::

## 2. Vertex AI embeds the question

When the runner classifies the turn as `PRODUCT_RAG`, the question is sent
to Vertex AI's `gemini-embedding-2` model with a query-purpose instruction
prepended to the text. The general-conversation fallback can call the same
vector-search tool, but this menu turn uses the deterministic route. Document
embeddings (the products themselves) are produced separately with a
document-purpose instruction so query and document vectors share the same
metric geometry. Repeat queries are short-circuited by the Oracle-backed
embedding cache.

```{mermaid}
flowchart TD
    Q["query: I need something bold"] --> CK{embedding_cache hit?}
    CK -- yes --> EV["list[float] · 3072 dims"]
    CK -- no --> V[Vertex AI embed_content]
    V --> EV
    EV --> NX[next stop]
```

`ProductService` is a SQLSpec async service. Its `embed_text` method is the
wrapper around Vertex AI's `gemini-embedding-2` call, with the Oracle-backed
embedding cache check in front of it. Gemini Embedding 2 does not use the old
embedding `task_type` API parameter; this app encodes query-vs-document intent
in the text sent to the embedding model.

```{literalinclude} ../src/app/domain/products/services/services.py
:language: python
:start-after: docs:start-vertex-embedding
:end-before: docs:end-vertex-embedding
:caption: src/app/domain/products/services/services.py
```

:::{agent-detail}
Query/document purpose is not cosmetic. The user question and product fixture
text are embedded with different instructions so Oracle compares vectors
generated for compatible retrieval roles.
:::

## 3. Oracle 26ai finds matching products

The 3072-dimension query vector is bound straight into a named SQL query.
Oracle's HNSW index over `product.embedding` returns the top matches in a
single round trip; `1 - VECTOR_DISTANCE(..., COSINE)` is reshaped into a
similarity score so a higher number means "more like the query."

```{mermaid}
flowchart LR
    QV["list[float] · 3072"] --> P[ProductService.search_by_vector]
    P --> S[(named SQL<br/>vector-search-products)]
    S --> X[(Oracle HNSW index<br/>NEIGHBOR GRAPH)]
    X --> M["list[ProductMatch]<br/>id · name · price · score"]
```

Every query lives as a named SQL file under `src/app/db/sql/`; SQLSpec loads
them by key. Here is the vector search the product service runs:

```{literalinclude} ../src/app/db/sql/products.sql
:language: sql
:start-after: docs:start-vector-search-sql
:end-before: docs:end-vector-search-sql
:caption: src/app/db/sql/products.sql
```

The matching `ProductService` method calls that named SQL and lets SQLSpec
map each row straight into a `ProductMatch` msgspec struct.

```{literalinclude} ../src/app/domain/products/services/services.py
:language: python
:start-after: docs:start-search-by-vector
:end-before: docs:end-search-by-vector
:caption: src/app/domain/products/services/services.py
```

:::{oracle-internals}
See [Oracle 26ai vector search](concepts/vector-search.md) for the HNSW
index shape and the `vector_memory_size` knob.
:::

## 4. The runner emits a grounded final event

For `PRODUCT_RAG`, the runner does not stream speculative model deltas. It
formats the returned product rows into one grounded `final` event. Store
location and product availability turns follow the same deterministic shape:
classify first, query named SQL through request-scoped services, then emit a
single grounded event with optional map actions.

```{mermaid}
flowchart TD
    I{intent} -->|PRODUCT_RAG| P[Product RAG]
    I -->|STORE_LOCATION| S[Store lookup]
    I -->|PRODUCT_AVAILABILITY| A[Inventory lookup]
    P --> O[(Oracle 26ai)]
    S --> O
    A --> O
    O --> R[Grounded final event]
```

For `GENERAL_CONVERSATION`, the runner falls through to the Google ADK 2.0
workflow. That path uses an `LlmAgent` with the same closure-bound tools and a
parallel `FunctionNode` classifier before the workflow output is packaged.

```{literalinclude} ../src/app/domain/chat/services/workflow.py
:language: python
:start-after: docs:start-workflow-fanout
:end-before: docs:end-workflow-fanout
:caption: src/app/domain/chat/services/workflow.py
```

:::{agent-detail}
The ADK workflow is still useful for general conversation and model-driven
fallbacks, but grounded product, store, availability, and unsupported order
routes are handled before the workflow is built. That is why menu turns never
show an ungrounded draft that later gets overwritten.
:::

## What's next

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} Concept primers
:link: concepts/vector-search
:link-type: doc

Short pages on vectors in Oracle, RAG, Google ADK, and store/map grounding.
:::

:::{grid-item-card} Reference
:link: reference/quickstart
:link-type: doc

Quickstart, the `coffee` CLI, autodoc on `ADKRunner` and the core services,
and a "for the curious" appendix.
:::

::::
