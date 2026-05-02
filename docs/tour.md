# Walkthrough

Follow one chat message — *"I need something bold"* — from the moment a
user types it until Gemini's grounded reply renders in the browser.

The phrase isn't an obvious coffee question. The agent has to recognize
that "bold" is an idiom for a dark roast or strong espresso, then decide
to call the vector-search tool against the menu — that's the whole point
of the demo.

The path of one message:

1. The browser opens an SSE stream to `/api/chat/stream`.
2. Vertex AI embeds the question (with an Oracle-backed cache in front).
3. Oracle 26ai's HNSW index returns the closest products.
4. ADK 2.0 grounds the answer and streams it back.

```{mermaid}
flowchart LR
    B([Browser]) -->|POST /api/chat/stream| C[Litestar controller]
    C --> R[ADKRunner]
    R --> V[Vertex AI<br/>embedding]
    R --> O[(Oracle 26ai<br/>HNSW search)]
    R --> G[Gemini]
    G -->|SSE final| B
```

*The whole turn in one picture: SSE in, SSE out, with retrieval and
generation hidden inside the runner.*

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

When the runner classifies the turn as `PRODUCT_RAG`, or the agent decides
to call its vector-search tool, the question is sent to Vertex AI's
`gemini-embedding-001` model with `task_type="RETRIEVAL_QUERY"`. Document
embeddings (the products themselves) are produced separately with
`RETRIEVAL_DOCUMENT` so query and document vectors share the same metric
geometry. Repeat queries are short-circuited by the Oracle-backed embedding
cache.

```{mermaid}
flowchart TD
    Q["query: I need something bold"] --> CK{embedding_cache hit?}
    CK -- yes --> EV["list[float] · 3072 dims"]
    CK -- no --> V[Vertex AI embed_content]
    V --> EV
    EV --> NX[next stop]
```

`ProductService` is a SQLSpec async service. Its `embed_text` method is the
wrapper around Vertex AI's `gemini-embedding-001` call, with the
Oracle-backed embedding cache check in front of it.

```{literalinclude} ../src/app/domain/products/services/services.py
:language: python
:start-after: docs:start-vertex-embedding
:end-before: docs:end-vertex-embedding
:caption: src/app/domain/products/services/services.py
```

:::{agent-detail}
`task_type` is not cosmetic — Vertex returns embeddings tuned for the role
of the text. `RETRIEVAL_QUERY` for the user's question, `RETRIEVAL_DOCUMENT`
for the product fixture. Mixing them quietly degrades similarity scores.
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

## 4. ADK 2.0 grounds the answer and streams it back

`ADKRunner` wraps a Google ADK 2.0 `Workflow`. From the `START` node, two
branches fan out in parallel: a `FunctionNode` runs the Flash-Lite intent
classifier, and an `LlmAgent` produces the conversational reply with the
vector-search tool bound in its closure. Both branches converge in a
`JoinNode`, then a final `FunctionNode` packages the labelled, grounded
answer. The runner emits `ServerSentEvent` deltas for non-RAG turns and a
single grounded final event for menu turns.

```{mermaid}
flowchart TD
    S{ADK START} --> A[LlmAgent coffee_turn]
    S --> I[FunctionNode intent]
    A -- tool call --> O[(Oracle 26ai)]
    O -- matches --> A
    A --> J((JoinNode))
    I --> J
    J --> M[FunctionNode<br/>classify_and_respond]
    M --> R[Grounded answer]
```

`ADKRunner` builds a Google ADK 2.0 `Workflow` once per request. The fanout
below — two edges leaving `START` and rejoining at a `JoinNode` — is what
lets the classifier and the agent overlap on the same event loop.

```{literalinclude} ../src/app/domain/chat/services/workflow.py
:language: python
:start-after: docs:start-workflow-fanout
:end-before: docs:end-workflow-fanout
:caption: src/app/domain/chat/services/workflow.py
```

:::{agent-detail}
`max_concurrency=2` lets the classifier and the LLM run on the same start
node without one blocking the other. The classifier's result feeds telemetry
and the final-event payload; for `PRODUCT_RAG` turns the runner takes a
deterministic shortcut and skips speculative model deltas so the browser
never sees an ungrounded draft.
:::

## What's next

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} Concept primers
:link: concepts/vector-search
:link-type: doc

Three short pages on vectors in Oracle, RAG, and Google ADK.
:::

:::{grid-item-card} Reference
:link: reference/quickstart
:link-type: doc

Quickstart, the `coffee` CLI, autodoc on `ADKRunner` and the core services,
and a "for the curious" appendix.
:::

::::
