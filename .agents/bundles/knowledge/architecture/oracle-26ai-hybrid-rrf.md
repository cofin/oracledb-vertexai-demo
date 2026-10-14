---
type: Guide
title: Oracle 26ai Hybrid RRF Search
description: Single-query Hybrid Reciprocal Rank Fusion combining Oracle Text MULTI_COLUMN_DATASTORE CONTAINS/SCORE with HNSW VECTOR_DISTANCE FETCH APPROX and JSON_TABLE term_hits
tags:
  - oracle-26ai
  - hybrid-search
  - rrf
  - vector-search
---

# Oracle 26ai Hybrid RRF Search

Cymbal Coffee replaces multi-step LLM intent classification + separate vector queries with a single Oracle AI Database 26ai Hybrid Reciprocal Rank Fusion query (`hybrid-search-turn` in `src/app/db/sql/hybrid.sql`, orchestrated by `HybridRouteResolver` in `src/app/domain/chat/services/_router.py`).

## 1. Unified Route + Candidate Retrieval (`hybrid-search-turn`)

A single SQL round trip evaluates three indexed entity families simultaneously:
1. **`chat_route`**: Route exemplars (`PRODUCT_RAG`, `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, `ORDER_STATUS`, `GENERAL_CONVERSATION`).
2. **`product`**: 130 specialty coffee products (`name`, `category`, `sku`, `description`, `embedding`).
3. **`store`**: 17 store locations (`name`, `address`, `city`, `state`, `zip`, `latitude`, `longitude`).

Each entity family computes:
- **Vector Rank ($r_{\text{vec}}$)**: `ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE) FETCH APPROX FIRST :vec_k ROWS ONLY` hitting the `INMEMORY NEIGHBOR GRAPH` (HNSW) index.
- **Lexical Rank ($r_{\text{lex}}$)**: `CONTAINS(..., :text_query, 1) > 0` ordered by `SCORE(1) DESC` hitting the `CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE` (`SYNC (ON COMMIT)`) index.
- **Fused RRF Score ($k = 60$)**:
  $$\text{RRF}(d) = \frac{1}{60 + r_{\text{lex}}(d)} + \frac{1}{60 + r_{\text{vec}}(d)}$$

## 2. Injection-Safe Oracle Text Sanitization (`build_oracle_text_query`)

User input is never interpolated into SQL or passed raw to `CONTAINS(...)`:
1. `build_oracle_text_query(raw_text)` extracts alphanumeric tokens (`[a-z0-9]+`).
2. Strips conversational stopwords and reserved Oracle Text operators (`AND`, `OR`, `NOT`, `NEAR`, `ACCUM`, `EQUIV`, `WITHIN`, `ABOUT`, `FUZZY`, `SYN`, `BT`, `NT`, `PT`, `TR`, `TRSYN`, `SQE`, `MINUS`).
3. Wraps each token in literal braces `{token}` and joins up to 16 tokens (`_MAX_QUERY_TOKENS = 16`) with `ACCUM` (e.g. `"{decaf} ACCUM {espresso}"`).
4. When no indexable tokens exist, binds `:has_text_query = 0` so the lexical CTE short-circuits cleanly.

## 3. Off-Menu Brand Detection (`hybrid-term-hits`)

Dense embeddings map off-menu brands (e.g. *"Do you carry Folgers?"*) to high cosine similarity (~0.68) with dark roasts. To distinguish off-menu brands from valid taste descriptions without an extra LLM call:
1. `extract_candidate_terms(message)` extracts candidate product/brand tokens.
2. `hybrid-term-hits` executes a single `JSON_TABLE(:terms_json)` + `CONTAINS(p.description, '{' || jt.term || '}') > 0` query to count catalog hits per term.
3. When a specific brand noun has 0 catalog hits, `GroundedRouteService` deterministically reports that Cymbal Coffee does not carry that brand and offers the top RRF-ranked in-stock alternatives.
