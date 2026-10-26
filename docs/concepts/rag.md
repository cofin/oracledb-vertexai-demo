# RAG with Hybrid RRF & Lexical Term Hits

Gemini is good at writing fluid, persuasive sentences about coffee. It is
not, on its own, a source of truth for *this* coffee shop's menu. Cymbal
Coffee solves that with an Oracle 26ai Hybrid RRF RAG path: retrieve real menu
rows in one `hybrid-search-turn` query fusing BM25-style lexical ranking
(`CONTAINS`/`SCORE`) and HNSW vector similarity
(`VECTOR_DISTANCE ... FETCH APPROX`), run a conditional `hybrid-term-hits` check
when quoted or capitalized brand tokens appear, and render product names,
prices, and descriptions directly from the returned Oracle rows.

```{mermaid}
flowchart TD
    Q[user question] --> E[embed with gemini-embedding-2]
    E --> R[(Oracle 26ai Hybrid RRF<br/>hybrid-search-turn)]
    R --> T[(conditional JSON_TABLE check<br/>hybrid-term-hits)]
    T --> G[grounded composer<br/>GroundedRouteService.handle_product_rag]
    G --> A[row-rendered<br/>grounded answer]
```

## Grounded Retrieval Pipeline

**1. Fuse Lexical And Vector Retrieval (`hybrid-search-turn`).** The user
question is embedded once with `VertexAIService.get_text_embedding`
(`src/app/domain/products/services/_embedding.py`) and sanitized with
`build_oracle_text_query` (`src/app/lib/text_search.py`). A single SQL query
(`src/app/db/sql/hybrid.sql`) combines Oracle Text `CONTAINS`/`SCORE` (over a
`MULTI_COLUMN_DATASTORE` indexing `name`, `category`, `sku`, and `description`)
with HNSW `VECTOR_DISTANCE(..., COSINE) FETCH APPROX` via Reciprocal Rank Fusion
($k = 60$).

**2. Verify Off-Menu Tokens (`hybrid-term-hits`).** `extract_candidate_terms`
(`src/app/domain/chat/services/_router.py`) extracts quoted or capitalized
product and brand tokens from the user's message and, when any are present,
checks them in one `JSON_TABLE(:terms_json)` + `CONTAINS` query against the
catalog. If a user asks
*"Do you carry Folgers?"*, dense embeddings match dark roasts at ~0.68
similarity, whereas `term_hits["Folgers"] == 0` populates `off_menu_terms` and
allows `compose_off_menu_alternative`
(`src/app/domain/chat/services/_composers.py`) to pivot directly to the closest
in-stock alternatives without an LLM call.

**3. Render Grounded Answer (`GroundedRouteService.handle_product_rag`).** For
in-catalog requests (`src/app/domain/chat/services/_grounded.py`),
`gemini-3.8-flash` selects candidate product IDs and a one-sentence persona
explanation (`PersonaManager` in `src/app/domain/system/services/_personas.py`)
under a strict JSON schema, falling back deterministically to
`compose_product_rag_answer` on timeout, non-credential generation errors, or
guard rejection. Product names,
prices, and descriptions are always rendered from the returned Oracle `product`
rows and yielded as a grounded SSE `final` event.

## Caches

`CacheService` (`src/app/domain/system/services/_cache.py`, inheriting from
`OracleLoaderService`) manages the Oracle cache tables on this path:

- **Embedding cache (`embedding_cache`)** — Oracle table keyed on
  `(text_hash, model)`. Repeat queries skip the Vertex AI call. Vectors are
  stored as `VECTOR(3072, FLOAT32)`.
- **Response cache (`response_cache`)** — keyed on
  `chat:<sha256(version:model:persona:normalized_query)>`
  (`make_response_cache_key` in `src/app/domain/ai/services/_agent.py`). A hit yields the cached final event
  without re-running retrieval or the model, and is automatically bypassed when
  location context or prior multi-turn session history is present.

## Where this is used

- **The walkthrough** walks through one full RAG turn: see [the
  walkthrough](../tour.md).
- **Hybrid routing** explains how `hybrid-search-turn` and `AgentRuntime`
  fit together: see [Hybrid RRF Routing and Native AI Runtime](agent-flow.md).
