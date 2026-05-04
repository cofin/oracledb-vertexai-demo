# RAG

Gemini is good at writing fluid, persuasive sentences about coffee. It is
not, on its own, a source of truth for *this* coffee shop's menu. Cymbal
Coffee solves that with a stricter RAG path: retrieve real menu rows from
Oracle, format the answer from those rows, and refuse to invent products that
aren't on the list.

```{mermaid}
flowchart TD
    Q[user question] --> E[embed]
    E --> R[(Oracle 26ai<br/>vector match)]
    R --> G[grounding context<br/>list&lt;ProductMatch&gt;]
    G --> M[Gemini]
    M --> A[grounded answer]
```

## The three steps

**Retrieve.** The user question is embedded once, then the
`vector-search-products` SQL returns up to *k* `ProductMatch` rows above a
similarity threshold. See [Vector search in Oracle
26ai](vector-search.md) for the HNSW shape and the embedding contract.

**Ground.** The returned rows are formatted into a structured grounding
context — name, description, price, in-stock flag, similarity score —
*not* free-form prose. The deterministic route formats the final answer from
that context; the ADK fallback exposes the same list as tool output.

**Generate.** For `PRODUCT_RAG` turns, the runner takes a deterministic
shortcut: it formats the final answer directly from the returned products
and yields a single grounded SSE final event. The model never gets to draft
a speculative reply that the browser would have to overwrite.

For `GENERAL_CONVERSATION` turns there's nothing to retrieve — the agent
streams Gemini's reply normally.

## Why intent-routed grounding, not prompt-stuffing

The naive RAG pattern bakes retrieved rows into the prompt and lets the
model decide what to do with them. Cymbal Coffee inverts that: a small,
fast classifier reads the user's turn first and routes product, store, and
availability questions to deterministic handlers. For `PRODUCT_RAG`, the
handler runs the vector search itself and formats the answer from the returned
rows — the LLM never gets to draft a speculative reply. That has three
consequences:

1. Retrieval is gated by intent, not by the LLM's tool reasoning, so
   grounded turns can't silently degrade into ungrounded prose;
2. The classifier's labels (`PRODUCT_RAG`, `STORE_LOCATION`,
   `PRODUCT_AVAILABILITY`, `GENERAL_CONVERSATION`) are the routing
   contract, so changing retrieval behavior is a code change, not prompt
   tweaking;
3. `search_products_by_vector` is *also* registered as a tool on the
   fallback `GENERAL_CONVERSATION` agent for cases the classifier missed
   — and even then, if that fallback path performs a product lookup, the
   runner re-grounds the final answer from the real vector-search rows.

## Caches

Two caches sit on this path:

- **Embedding cache** — Oracle table keyed on `(text, model)`. Repeat
  queries (or product re-embeddings) skip the Vertex AI call. Vectors are
  stored as `VECTOR(3072, FLOAT32)` so the cache uses the same vector
  memory pool as the product index.
- **Response cache** — keyed on model + persona + normalized query. A hit
  yields the exact final event without re-running retrieval or the LLM.

The chat result payload reports both — `embedding_cache_hit` and
`from_cache` — so it's visible in the UI which path served the answer.

## Failure modes the demo surfaces

- **The fallback model skips the tool**: the runner's grounding fallback
  re-runs product search and formats the answer from the returned rows rather
  than trusting the model's tool-less draft.
- **The fallback model emits a tool-schema artifact instead of an answer**:
  same fallback. Better an honest grounded answer than a confused one.
- **No products match**: the threshold filters out weak matches; the
  agent says it doesn't have one and offers to substitute. It does not
  invent a product.

## Where this is used

- **The walkthrough** walks through one full RAG turn: see [the
  walkthrough](../tour.md).
- **Chat routing** explains how the classifier, deterministic routes, and ADK
  fallback fit together: see [Chat routing and Google ADK](agent-flow.md).
