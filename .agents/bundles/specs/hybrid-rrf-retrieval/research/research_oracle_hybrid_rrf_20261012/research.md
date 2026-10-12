---
type: Research
research_id: research_oracle_hybrid_rrf_20261012
title: Oracle AI Database 26ai Hybrid Search, Oracle Text Lexical Scoring, and Single-Query RRF Routing
description: Primary-source verification of Oracle 26ai Text scoring vs BM25, DBMS_HYBRID_VECTOR vs pure-SQL RRF, and single-query route + retrieval fusion on Oracle Free 23.26.0
scope: database
status: stable
state: promoted
promoted_to: hybrid-rrf-retrieval
confidence: high
created_at: 2026-10-12T17:35:00Z
updated_at: 2026-10-12T17:35:00Z
tags:
  - research
  - oracle
  - vector-search
  - hybrid-search
  - rrf
  - bm25
---

# Oracle AI Database 26ai Hybrid Search, Oracle Text Lexical Scoring, and Single-Query RRF Routing

## Executive Summary

1. **Oracle Text `CONTAINS` / `SCORE` Algorithm**: In Oracle AI Database 26ai (`23.26.0.0.0`), standard `CTXSYS.CONTEXT` indexes and `DBMS_HYBRID_VECTOR.SEARCH` score lexical matches using **Salton's inverse-frequency TF-IDF formula** normalized to `0..100` (via `DEFINESCORE(..., DISCRETE | FLOAT)`), **not** a native `BM25` keyword inside `CTXSYS.CONTEXT`. Oracle 26ai's native in-database support for external BM25 encoders is **Sparse Vectors** (`VECTOR(dim, format, SPARSE)`), where a client BM25/SPLADE model emits sparse token-index/weight vectors queried via `VECTOR_DISTANCE` (`INNER_PRODUCT`).
2. **Why `DBMS_HYBRID_VECTOR.SEARCH` Is Not Used Here**:
   - `CREATE HYBRID VECTOR INDEX` requires an in-database `VECTORIZER` preference (`DBMS_VECTOR.CREATE_PREFERENCE`), whereas Cymbal Coffee computes 3,072-dimension `gemini-embedding-2` embeddings client-side in Python via `google-genai` with an in-DB `embedding_cache`.
   - `DBMS_HYBRID_VECTOR.SEARCH` operates on a single base table per call and returns a CLOB JSON document rather than typed relational rows, preventing a single query from fusing `product`, `coffee_store`, and `chat_route` exemplars in one round trip.
3. **Recommended Architecture — Pure-SQL Hybrid RRF + Per-Term Lexical Hit Counts**:
   - Combine `CTXSYS.CONTEXT` (`MULTI_COLUMN_DATASTORE` across `name`, `category`, `origin`, `roast_level`, `flavor_profile`, `description` for products and `name`, `city`, `state`, `address_line1`, `postal_code`, `neighborhood`, `notes` for stores) with `VECTOR_DISTANCE(..., COSINE) FETCH APPROX FIRST :k ROWS ONLY` in a single CTE-based SQL query (`hybrid-search-turn`).
   - Fuse lexical rank ($r_{\text{lex}}$) and semantic vector rank ($r_{\text{vec}}$) using Reciprocal Rank Fusion ($k = 60$):
     $$\text{RRF}(d) = \frac{w_{\text{lex}}}{60 + r_{\text{lex}}(d)} + \frac{w_{\text{vec}}}{60 + r_{\text{vec}}(d)}$$
   - Include `chat_route` exemplars in the same SQL statement so route resolution (`PRODUCT_RAG`, `PRODUCT_AVAILABILITY`, `STORE_LOCATION`, `ORDER_STATUS`, `GENERAL_CONVERSATION`), top products, and top stores are returned in **one database round trip**, eliminating `FlashLiteIntentClassifier`.
   - Compute per-term lexical hit counts via `JSON_TABLE(:terms_json, '$[*]' COLUMNS (term VARCHAR2(128) PATH '$'))` against `CONTAINS(p.name, t.term) > 0 OR CONTAINS(p.description, t.term) > 0` so off-menu brand requests (`"Folgers"`, `"Starbucks"`) are detected deterministically (`hits = 0`) without hardcoded brand blocklists.

## 1. Decision Matrix: `DBMS_HYBRID_VECTOR.SEARCH` vs Pure-SQL RRF

| Criterion | `DBMS_HYBRID_VECTOR.SEARCH` | Pure-SQL RRF (`CONTAINS` + `VECTOR_DISTANCE`) |
| --- | --- | --- |
| Works with client-side Vertex AI `gemini-embedding-2` (3072-dim `list[float]` bind) | Awkward — requires in-DB `VECTORIZER` preference even when passing `search_vector` | **Native** — binds `:query_vector` directly to `TO_VECTOR(:query_vector, 3072, FLOAT32)` |
| Combines route exemplars + products + stores in 1 round trip | No — single base table per index | **Yes** — multi-CTE `UNION ALL` in a single statement |
| Multi-column lexical search (`name`, `category`, `origin`, `roast_level`, `flavor_profile`, `description`) | Single column unless manually concatenated | **Yes** — `CTXSYS.MULTI_COLUMN_DATASTORE` with `SECTION GROUP` |
| Exposes per-term lexical hit counts (`Folgers` -> 0 hits) | No | **Yes** — `JSON_TABLE(:terms_json)` + `CONTAINS` |
| SQLSpec typed mapping (`schema_type=MsgspecStruct`) | Returns nested CLOB JSON requiring manual unpack | **Yes** — flat relational columns mapped directly by SQLSpec |
| Verified on `gvenzl/oracle-free:latest` (`23.26.0.0.0`) + SQLSpec 0.65 | Requires DB credential setup | **Verified passing** end-to-end |

## 2. Verified `CTX_DDL` `MULTI_COLUMN_DATASTORE` DDL

```sql
BEGIN
    BEGIN
        CTX_DDL.DROP_PREFERENCE('product_search_ds');
    EXCEPTION
        WHEN OTHERS THEN NULL;
    END;
    CTX_DDL.CREATE_PREFERENCE('product_search_ds', 'MULTI_COLUMN_DATASTORE');
    CTX_DDL.SET_ATTRIBUTE(
        'product_search_ds',
        'COLUMNS',
        'name, category, origin, roast_level, flavor_profile, description'
    );
END;
/

CREATE INDEX product_hybrid_ctx_idx ON product(description)
    INDEXTYPE IS CTXSYS.CONTEXT
    PARAMETERS ('DATASTORE product_search_ds SYNC (ON COMMIT)');
```

## 3. Verified `build_oracle_text_query` Sanitizer

Oracle Text `CONTAINS` throws `DRG-50901: text query parser syntax error` if raw user punctuation (`?`, `-`, `&`, `|`, `~`, `*`, `%`, `()`, `{}`) or reserved operators (`AND`, `OR`, `NOT`, `NEAR`, `ACCUM`, `ABOUT`, `SYN`, `BT`, `NT`, `PT`, `RT`, `SQE`, `TR`, `TRSYN`, `WITHIN`, `FUZZY`, `STEM`, `SOUNDEX`) are passed unescaped. Wrapping each tokenized alphanumeric/hyphen term in `{term}` braces and joining with `ACCUM` (Oracle Text's weighted sum-of-terms operator, with higher weight on phrase/title tokens):

- Escapes all reserved words and punctuation safely.
- Ranks documents matching more query terms higher (`SCORE(1)` in `0..100`).
- Returns `None` when no searchable tokens exist so the SQL query short-circuits the `CONTAINS` branch via `:has_text_query = 1`.
