# RAG with Hybrid RRF & Lexical Term Hits

Gemini is good at writing fluid, persuasive sentences about coffee. It is
not, on its own, a source of truth for *this* coffee shop's menu. Cymbal
Coffee solves that with a single-query Oracle 26ai Hybrid RRF RAG path:
retrieve real menu rows by fusing BM25-style lexical ranking (`CONTAINS`/`SCORE`)
and HNSW vector similarity (`VECTOR_DISTANCE ... FETCH APPROX`), verify exact
catalog token hits via `hybrid-term-hits`, and format the answer deterministically
from those rows.

```{mermaid}
flowchart TD
    Q[user question] --> E[embed with gemini-embedding-2]
    E --> R[(Oracle 26ai Hybrid RRF<br/>hybrid-search-turn)]
    R --> T[(Oracle Text JSON_TABLE<br/>hybrid-term-hits)]
    T --> G[grounded composer<br/>GroundedRouteService.handle_product_rag]
    G --> A[row-rendered<br/>grounded answer]
```

## The three steps

**1. Fuse Lexical & Vector Retrieval (`hybrid-search-turn`).** The user question
is embedded once, and a single SQL query combines Oracle Text `CONTAINS`/`SCORE`
(over `MULTI_COLUMN_DATASTORE` indexing `name`, `description`, `category`, `sku`) with
HNSW `VECTOR_DISTANCE(..., COSINE) FETCH APPROX` via Reciprocal Rank Fusion
($k = 60$).

**2. Verify Off-Menu Tokens (`hybrid-term-hits`).** Content tokens from the
user's message are checked in one `JSON_TABLE(:terms_json)` + `CONTAINS` query
against the catalog. If a user asks *"Do you carry Folgers?"*, dense embeddings
match dark roasts at ~0.68 similarity, but `term_hits["folgers"] == 0` proves
`"Folgers"` is not on the menu—allowing the composer to explicitly pivot to
closest in-stock alternatives without a second LLM call.

**3. Render Grounded Answer (`GroundedRouteService.handle_product_rag`).** The final answer
is rendered directly from the returned Oracle product rows (names, prices,
descriptions) and yielded as a grounded SSE `final` event.

## Caches

Two caches sit on this path:

- **Embedding cache** — Oracle table keyed on `(text_hash, model)`. Repeat
  queries skip the Vertex AI call. Vectors are stored as `VECTOR(3072, FLOAT32)`.
- **Response cache** — keyed on version + model + persona + normalized query.
  A hit yields the cached final event without re-running retrieval or the LLM
  (automatically bypassed when browser geolocation coordinates are shared).

## Where this is used

- **The walkthrough** walks through one full RAG turn: see [the
  walkthrough](../tour.md).
- **Hybrid routing** explains how `hybrid-search-turn` and `AgentRuntime`
  fit together: see [Hybrid RRF Routing and Native AI Runtime](agent-flow.md).
