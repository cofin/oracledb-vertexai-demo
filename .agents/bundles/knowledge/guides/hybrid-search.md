---
type: Guide
title: Oracle 26ai Hybrid Search & RRF Routing Guide
description: Single-query Hybrid RRF combining Oracle Text MULTI_COLUMN_DATASTORE CONTAINS/SCORE with HNSW VECTOR_DISTANCE FETCH APPROX and JSON_TABLE term_hits
tags:
  - oracle-26ai
  - hybrid-search
  - rrf
  - bm25
  - vector-search
---

# Oracle 26ai Hybrid Search & RRF Routing Guide

This guide documents Cymbal Coffee's single-query **Hybrid Reciprocal Rank Fusion (RRF)** architecture (`src/app/db/sql/hybrid.sql` and `src/app/domain/chat/services/_router.py`), which replaces the two-step LLM intent-classifier + separate vector-search pipeline.

## 1. Why Single-Query Hybrid RRF?

Previously, every chat turn made an LLM intent-classification call (`Gemini Flash-Lite`) followed by a separate product or store SQL query (~350–500 ms combined). By indexing route exemplars (`chat_route`), products (`product`), and stores (`coffee_store`) with both **Oracle Text (`CTXSYS.CONTEXT`)** and **3072-dimension dense vectors (`VECTOR(3072, FLOAT32)`)**, a single SQL round trip (`hybrid-search-turn`, ~15–25 ms) simultaneously resolves:

1. **The turn route** (`PRODUCT_RAG`, `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, `ORDER_STATUS`, or `GENERAL_CONVERSATION`).
2. **Top-ranked product candidates** fused by lexical and semantic rank.
3. **Top-ranked store candidates** matching city, state, postal code, or address tokens.

## 2. Oracle Text `MULTI_COLUMN_DATASTORE` & `SYNC(ON COMMIT)`

In `src/app/db/migrations/0002_agent_runtime_and_hybrid_search.sql`, multi-column Oracle Text preferences index combined text attributes on `product`, `coffee_store`, and `chat_route`:

- `product_ hybrid_idx` on `product(search_text)` with `MULTI_COLUMN_DATASTORE` across `name, description, category` and `SYNC(ON COMMIT)`.
- `coffee_store_text_idx` on `coffee_store(search_text)` with `MULTI_COLUMN_DATASTORE` across `name, address_line1, city, state, postal_code` and `SYNC(ON COMMIT)`.
- `chat_route_text_idx` on `chat_route(search_text)` with `MULTI_COLUMN_DATASTORE` across `title, exemplar_text, keywords` and `SYNC(ON COMMIT)`.

> **Lexical Scoring Note:** Oracle Text `CONTAINS(..., :text_query, 1) > 0` paired with `SCORE(1)` computes an inverse-frequency TF-IDF relevance score (0–100), providing **BM25-style lexical ranking** over relational columns. Oracle AI Database 26ai also supports `VECTOR(..., SPARSE)` for client-generated BM25/SPLADE sparse vectors when external sparse encoders are used.

## 3. Injection-Safe Oracle Text Query Sanitization (`build_oracle_text_query`)

User input must never be passed raw to `CONTAINS(...)` because Oracle Text interprets words like `AND`, `OR`, `NOT`, `NEAR`, `SYN`, `FUZZY`, `ABOUT`, and punctuation (`{}`, `%`, `_`, `-`) as query operators.

`build_oracle_text_query(raw_text: str) -> str | None` in `src/app/domain/chat/services/_router.py`:
1. Extracts alphanumeric tokens (`[a-z0-9]+`).
2. Filters conversational stopwords and reserved Oracle Text keywords.
3. Wraps every token in literal braces `{token}` and joins up to 12 tokens with `ACCUM` (e.g., `"{decaf} ACCUM {espresso}"`).
4. Returns `None` when no indexable tokens remain; the SQL binds `:has_text_query = 0` and short-circuits `CONTAINS` cleanly.

## 4. HNSW `FETCH APPROX` + Reciprocal Rank Fusion ($k=60$)

Oracle 26ai HNSW (`INMEMORY NEIGHBOR GRAPH`) indexes are only used when the query orders directly by `VECTOR_DISTANCE(embedding, TO_VECTOR(:query_vector, 3072, FLOAT32), COSINE)` with `FETCH APPROX FIRST :vec_k ROWS ONLY`.

In `src/app/db/sql/hybrid.sql` (`hybrid-search-turn`), each entity family (`chat_route`, `product`, `coffee_store`) computes `vec_rank` and `lex_rank` in separate CTEs and joins them via `FULL OUTER JOIN`:

$$\text{RRF}(d) = \frac{1}{60 + r_{\text{lex}}(d)} + \frac{1}{60 + r_{\text{vec}}(d)}$$

## 5. Off-Menu Brand Detection (`hybrid-term-hits`)

Dense embeddings map off-menu coffee brands (e.g., *"Do you carry Folgers?"*) to high cosine similarity (~0.68) with dark roasts. To separate valid taste idioms (*"I need something bold"*) from off-menu brands without a second LLM call:

1. `extract_candidate_product_terms(message)` extracts candidate product/brand tokens from the user's query.
2. `hybrid-term-hits` checks each token's catalog hit count in a single `JSON_TABLE(:terms_json)` + `CONTAINS(p.name, t.term_query, 1) > 0` query.
3. When a specific product/brand noun has `term_hits[token] == 0`, `compose_product_rag_answer` (`src/app/domain/chat/services/_grounded.py`) deterministically states that Cymbal Coffee does not carry that item and recommends the top RRF-matched in-stock alternatives.
