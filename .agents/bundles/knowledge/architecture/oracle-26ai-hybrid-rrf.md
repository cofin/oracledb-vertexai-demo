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

Cymbal Coffee replaces multi-step LLM intent classification and separate vector queries with single-query Oracle AI Database 26ai Hybrid Reciprocal Rank Fusion (`hybrid-search-turn` and `hybrid-search-products` in `src/app/db/sql/hybrid.sql`, orchestrated by `HybridRouteResolver` in `src/app/domain/chat/services/_router.py` and `ProductService.search_hybrid()` in `src/app/domain/products/services/_products.py`).

## 1. Unified Route + Candidate Retrieval (`hybrid-search-turn`)

A single SQL round trip evaluates three indexed entity families simultaneously:
1. **`chat_route`**: Route exemplars (`PRODUCT_RAG`, `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, `ORDER_STATUS`, `GENERAL_CONVERSATION`) combining Oracle Text lexical rank and HNSW vector rank.
2. **`product`**: 130 specialty coffee products (`name`, `category`, `sku`, `description`, `embedding`) combining Oracle Text lexical rank and HNSW vector rank.
3. **`store`**: 17 store locations (`name`, `address`, `city`, `state`, `zip` indexed by `store_search_ds`) ranked via `STORE_HYBRID_CTX_IDX` Oracle Text lexical matching (`CONTAINS(s.address, :text_query, 3) > 0`).

Vector-indexed entity families (`chat_route` and `product`) compute:
- **Vector Rank ($r_{\text{vec}}$)**: `ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE) FETCH APPROX FIRST :limit ROWS ONLY` hitting the `INMEMORY NEIGHBOR GRAPH` (HNSW) index.
- **Lexical Rank ($r_{\text{lex}}$)**: `CONTAINS(..., :text_query, label) > 0` ordered by `SCORE(label) DESC` hitting the `CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE` (`SYNC (ON COMMIT)`) index.
- **Fused RRF Score ($k = 60$)**:
  $$\text{RRF}(d) = \frac{1}{60 + r_{\text{lex}}(d)} + \frac{1}{60 + r_{\text{vec}}(d)}$$

## 2. Injection-Safe Oracle Text Sanitization (`src/app/lib/text_search.py`)

User input is never interpolated into SQL or passed raw to `CONTAINS(...)`. `src/app/lib/text_search.py` centralizes token extraction and Oracle Text query construction:
1. `extract_search_tokens(text, max_terms=16)` extracts deduplicated lowercase alphanumeric/hyphen tokens (`len >= 2`) and strips `ORACLE_TEXT_RESERVED_WORDS` (`AND`, `OR`, `NOT`, `NEAR`, `ACCUM`, `EQUIV`, `WITHIN`, `ABOUT`, `FUZZY`, `SYN`, `BT`, `NT`, `PT`, `TR`, `TRSYN`, `SQE`, `MINUS`, `SDATA`, `MDDATA`, `STEM`, `SOUNDEX`, `WILD`, etc.) and conversational `ORACLE_TEXT_STOPWORDS`.
2. `build_oracle_text_query(text, max_terms=16)` wraps each sanitized token in literal braces `{token}` and joins tokens with `ACCUM` (for example, `"{decaf} ACCUM {espresso}"`).
3. `build_oracle_proximity_query(text, max_span=6, in_order=True, max_terms=8)` builds a `NEAR(({t1}, {t2}), span, TRUE) ACCUM ({t1} ACCUM {t2})` expression for phrase-boosted lexical recall.
4. When `build_oracle_text_query()` returns `None`, callers bind `:has_text_query = 0` (with placeholder `:text_query = "{coffee}"`) so lexical CTEs short-circuit cleanly.

## 3. Off-Menu Brand Detection (`hybrid-term-hits`)

Dense embeddings map off-menu brands (for example, *"Do you carry Folgers?"*) to high cosine similarity (~0.68) with dark roasts. To distinguish off-menu brands from valid taste descriptions without an extra LLM call:
1. `extract_candidate_terms(user_query)` in `src/app/domain/chat/services/_router.py` extracts quoted or capitalized product/brand tokens.
2. `hybrid-term-hits` executes a single `JSON_TABLE(:terms_json)` + `CONTAINS(p.description, '{' || jt.term || '}') > 0` query to count catalog hits per term.
3. When a specific brand noun has 0 catalog hits (`off_menu_terms`), `GroundedRouteService` (`src/app/domain/chat/services/_grounded.py`) deterministically reports that Cymbal Coffee does not carry that brand and offers the top RRF-ranked in-stock alternatives.

## 4. HNSW Index Access inside RRF CTEs & Storage Sizing

- **Subquery Isolation for `ROWNUM` Ranking**: In Oracle AI Database 26ai (`23.26.0.0.0`), placing `ROW_NUMBER() OVER (ORDER BY VECTOR_DISTANCE(..., COSINE))` directly inside the same query block as `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX FIRST :limit ROWS ONLY` prevents the Cost-Based Optimizer from selecting `VECTOR INDEX HNSW SCAN` and falls back to `TABLE ACCESS FULL`. Always isolate `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST :limit ROWS ONLY` inside an inner subquery (`*_vec_top`) and assign `ROWNUM AS vector_rank` in the outer CTE so the optimizer combines `VECTOR INDEX HNSW SCAN IN-FILTER` (`PRODUCT_EMBEDDING_IDX`) with `DOMAIN INDEX` (`PRODUCT_HYBRID_CTX_IDX`).
- **Validated Storage Calculator Formulas (`src/resources/vector-calculator.js`)**:
  - **HNSW (`INMEMORY NEIGHBOR GRAPH`)**: Per `DBMS_VECTOR.INDEX_VECTOR_MEMORY_ADVISOR`, requires `1.25x` raw vector bytes (`Math.round(raw_size * 1.25 + row_count * 640)`, where `raw_size` is `row_count * ceil(dimensions / 8)` for `BINARY` and `row_count * dimensions * dtype_bytes` otherwise) plus `640 B/row` hierarchical neighbor-graph link structures in the SGA Vector Pool (`VECTOR_MEMORY_SIZE`).
  - **IVF (`NEIGHBOR PARTITIONS`)**: Allocates `1.1x` raw vector bytes (`Math.round(raw_size * 1.1)`) on disk for inverted partition tables and caches `clamp(floor(sqrt(N)), 1, 65536)` partition centroids (`Math.round(partitions * max(ceil(raw_size / N), dimensions * 4) * 3)`) in the SGA Vector Pool.
  - **Oracle Text FTS (`CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE`)**: Allocates four internal segments (`DR$<index>$I` token postings BLOB, `$X` B-tree on `(TOKEN_TEXT, TOKEN_TYPE, TOKEN_FIRST, TOKEN_LAST, TOKEN_COUNT)`, `$K` DOCID-to-ROWID IOT, and `$R` ROWID-to-DOCID mapping table), sized via `max(576 KiB, round(row_count * (fts_doc_bytes * 0.42 + 36)))` (`42%` inverted-index ratio plus `36 B/row` mapping overhead, or `0` when `fts_doc_bytes <= 0`).
