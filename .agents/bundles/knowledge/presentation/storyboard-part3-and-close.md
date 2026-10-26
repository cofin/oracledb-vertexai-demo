---
type: Guide
title: "Storyboard — Build Real Apps: Cymbal Coffee and Close (slides 26–34)"
description: Slide-by-slide content, code, takeaways, and speaker notes for the Build Real Apps Cymbal Coffee walkthrough and Close (slides 26–34)
tags:
  - presentation
  - storyboard
---

# Storyboard — Build Real Apps: Cymbal Coffee and Close (slides 26–34)

This section follows the architecture walkthrough in [`SLIDES.md`](../../../../SLIDES.md),
the baseline schema in `src/app/db/migrations/0001_cymball_coffee_products.sql`,
and the named SQL queries in `src/app/db/sql/`. Keep repository file paths strictly
in speaker notes and sources—never on public slide faces.

## Build Real Apps: Cymbal Coffee

### 26. Build Real Apps: Cymbal Coffee

- **Target:** `dba_s29` (section divider)
- **Title:** Build Real Apps: Cymbal Coffee
- **Subtitle:** Grounded conversational commerce on Oracle AI Database 26ai, Oracle APEX 26.1, and Vertex AI
- **Notes:** Everything up to this point helps you operate Oracle. The next six slides show Oracle AI Database 26ai doing intent routing, lexical matching, and approximate vector retrieval in SQL for a production-shaped web and APEX application (`SLIDES.md`), so prices and store inventory come straight from database rows.
  BRIDGE: First, let's look at the customer scenario the AI Barista has to solve.
- **Sources:** NorCal 35; Webinar 39; `SLIDES.md`

### 27. The Demo Scenario: Cymbal Coffee AI Barista

- **Target:** `dba_s38`
- **Title:** The Demo Scenario: Cymbal Coffee AI Barista
- **Subtitle:** Natural taste questions, off-menu brand checks, and store stock grounded in live SQL rows
- **Cards:**
  - **Idiom & Taste Discovery:** `"I need something bold"` matches dark roasts via `gemini-embedding-2` even when the customer never writes the word `"coffee"`.
  - **Exact Terms & Off-Menu Guard:** `CTXSYS.CONTEXT` matches SKUs, ZIP codes, and `"Do you carry Folgers?"`—`JSON_TABLE` + `CONTAINS` sees `0` catalog hits and recommends `Dark Roast House Blend (\$4.99)` without an extra LLM call.
  - **Grounded SQL vs Open-Ended Agent:** `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, and `ORDER_STATUS` answer directly from SQL rows without calling Gemini; `PRODUCT_RAG` uses deterministic off-menu replies or constrained ID selection over SQL candidates; `GENERAL_CONVERSATION` runs the tool-calling Gemini 3.8 Flash loop.
- **Notes:** Walk through how `GroundedRouteService` (`src/app/domain/chat/services/_grounded.py`) keeps prices and stock deterministic: `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, and static `ORDER_STATUS` format Oracle rows in Python without calling Gemini at all; `PRODUCT_RAG` replies deterministically when `hybrid-term-hits` detects an off-menu brand like Folgers (offering `Dark Roast House Blend` at `\$4.99` and `Signature Bold Blend` at `\$4.99` from `src/app/db/fixtures/product.json.gz`) or runs constrained structured ID selection over the SQL candidate rows with deterministic template fallback; and only open-ended `GENERAL_CONVERSATION` turns invoke `AgentRuntime` (`src/app/domain/ai/runtime/_loop.py`) via `AgentOrchestrationService` (`src/app/domain/ai/services/_agent.py`).
  BRIDGE: Let's look at how the application, Oracle 26ai, Oracle APEX 26.1, and Vertex AI fit together.
- **Sources:** `SLIDES.md` slides 0, 6, and appendix; `src/app/domain/chat/services/_grounded.py`, `src/app/domain/ai/services/_agent.py`, `src/app/db/fixtures/product.json.gz`

### 28. Cymbal Coffee Reference Architecture

- **Target:** `dba_s30` (bordered 2026 UI screenshot + architecture diagram)
- **Title:** Cymbal Coffee Reference Architecture
- **Subtitle:** Oracle 26ai handles hybrid retrieval and queues; Litestar and APEX 26.1 share one schema
- **Diagram boxes:**
  - **Browser & Operations UI:** Streaming SSE chat web app (`http://localhost:8000`) plus pre-bundled Oracle APEX 26.1.5 + ORDS 26.3 Operations Console (`https://localhost:8443/ords/apex`, App ID `100`, workspace `COFFEE`, schema `APP`).
  - **Litestar 2 Application Tier:** Async Python service on Cloud Run or Compute Engine using SQLSpec `0.69.0` (`fetch_lobs=False` inline `CLOB`/`BLOB` strings, session tracing, wire-level `sqlcommenter`), an isolated `FOR UPDATE SKIP LOCKED` queue pool (`min=1, max=4`), and short transactions committed before model calls.
  - **Oracle AI Database 26ai:** Autonomous AI Database Free (`adb-free:latest-26ai` on `:1522` mTLS) or Oracle Database@Google Cloud storing `product` (`130` rows), `store` (`17` rows), `store_product_inventory` (`1,700` rows), `chat_route` (`25` exemplars across `5` routes), `embedding_cache`, `response_cache`, `agent_session` / `agent_event`, and queue tables; browser coordinates stay request-scoped in memory only.
  - **Vertex AI:** `gemini-embedding-2` (`3,072` dimensions) and `Gemini 3.8 Flash`, called from Python via `google-genai` (`vertexai=True`) and from Oracle APEX 26.1 PL/SQL via `APEX_AI.GENERATE` (`COFFEE_VERTEX_AI` against Vertex AI `/endpoints/openapi` or the local OpenAI-compatible `/api/apex/ai/v1` gateway).
  - **Shared Agent Protocols (`POST /mcp` & `POST /a2a`):** Exposes catalog search, product details, store inventory, barista prompts, and the `/.well-known/agent-card.json` A2A skill over the same parameterized SQL services, optionally gated by `MCP_API_KEY`.
- **Source line:** `github.com/cofin/oracledb-vertexai-demo`
- **Notes:** Trace one turn from `SLIDES.md` slides 0, 3, 7, and 8: `OracleSessionStore` and `OracleEventStore` (`src/app/domain/ai/runtime/_store.py`) commit immediately before any Vertex AI call; SQLSpec `0.69.0` (`src/app/lib/settings/_database.py`) defaults `fetch_lobs=False` and isolates `OracledbAsyncQueueStore` on `DatabaseSettings.get_queue_config()` (`session_key="queue_db_session"`); and the APEX 26.1 console (`src/apex/cymbal-coffee-ops/`, backed by `ApexController` in `src/app/domain/products/controllers/_apex.py` and `ApexAIController` in `src/app/domain/products/controllers/_apex_ai.py`) shares the `APP` schema. Emphasize protocol reuse: the same parameterized SQL services (`ProductService`, `StoreService`, `OracleVectorSearchService`) back `AgentRuntime`'s five Gemini tools (`search_products`, `get_product_details`, `find_nearby_stores`, `check_product_availability`, `check_order_status` in `src/app/domain/ai/services/_tools.py`), `LitestarMCP` (`POST /mcp` in `src/app/server/mcp/_config.py` exposing `search_products`, `get_product`, `get_store_inventory`, `describe_barista_capabilities`, and barista prompts in `src/app/domain/ai/mcp/`), and `LitestarA2A` (`POST /a2a`, agent card `/.well-known/agent-card.json` in `src/app/domain/ai/a2a/`), optionally gated by `MCP_API_KEY`.
  BRIDGE: Let's walk through the four SQL building blocks, starting with Step 1: dense embeddings in the `product` table.
- **Sources:** `SLIDES.md` slides 0, 2, 3, 7, 8; `src/apex/README.md`, `src/app/lib/settings/_database.py`, `src/app/server/plugins.py`, `src/app/server/mcp/_config.py`, `src/app/domain/ai/services/_tools.py`, `src/app/domain/ai/mcp/`, `src/app/domain/ai/a2a/`

### 29. Step 1: Dense Embeddings in Oracle 26ai

- **Target:** `dba_s31` (`T_SCULPTURE`)
- **Title:** Step 1: Dense Embeddings in Oracle 26ai
- **Left card (`Native VECTOR + In-Memory`):**
  - `gemini-embedding-2` outputs 3,072 `FLOAT32` dimensions (`~12 KB` per row)
  - Stored in `VECTOR(3072, FLOAT32)` inside the same table as relational, `BOOLEAN`, and `JSON` columns
  - **Why `INMEMORY PRIORITY HIGH`:** keeps scalar filters (`in_stock`, `category`, `price`) in the In-Memory column store (`inmemory_size`) alongside HNSW (`vector_memory_size`)
  - `python-oracledb` binds a Python `list[float]` directly
- **Right code card (`sql`):**

  ```sql
  CREATE TABLE product (
      id          NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY PRIMARY KEY,
      name        VARCHAR2(255) NOT NULL,
      description VARCHAR2(4000),
      price       NUMBER(10, 2),
      category    VARCHAR2(100),
      sku         VARCHAR2(100) UNIQUE,
      in_stock    BOOLEAN DEFAULT TRUE,
      metadata    JSON,
      embedding   VECTOR(3072, FLOAT32)
  ) INMEMORY PRIORITY HIGH;
  -- Populates scalar filters (in_stock, category, price) into the
  -- In-Memory Column Store alongside HNSW (no-op if inmemory_size = 0)

  -- Bind Python list[float] directly via python-oracledb
  UPDATE product SET embedding = :embedding WHERE id = :id;
  ```

- **Notes:** Quote the exact column definitions from `src/app/db/migrations/0001_cymball_coffee_products.sql` (`lines 11-36`, where `in_stock` and `embedding` also carry `ANNOTATIONS` and `created_at` / `updated_at` track row timestamps) and `ProductService.update_embedding()` (`src/app/domain/products/services/_products.py`). Explain why `INMEMORY PRIORITY HIGH` is paired with HNSW: HNSW lives in `vector_memory_size`, while `INMEMORY PRIORITY HIGH` populates scalar filter columns into `inmemory_size` (and is a safe no-op when `inmemory_size = 0`).
  BRIDGE: Next, Step 2: sizing the vector pool and configuring the HNSW neighbor graph index.
- **Sources:** `src/app/db/migrations/0001_cymball_coffee_products.sql`, `src/app/domain/products/services/_products.py`

### 30. Step 2: HNSW Vector Index Configuration in 26ai

- **Target:** `dba_s32` (`T_CORAL`)
- **Title:** Step 2: HNSW Vector Index Configuration in 26ai
- **Left card (`Minimum Pool + HNSW Graph`):**
  - **Minimum Pool on Free:** `vector_memory_size = 512M` (`SCOPE = SPFILE`) is the minimum carve-out to enable HNSW inside 26ai Free's ~1.5 GB SGA cap (Autonomous AI Database Free manages it automatically)
  - **Graph Parameters:** `NEIGHBORS 40` (edges per node) and `EFCONSTRUCTION 500` (build search depth) at `95%` target accuracy
  - **Optimizer Rule:** Query with `ORDER BY VECTOR_DISTANCE(..., COSINE)` + `FETCH APPROX`
- **Right code card (`sql`):**

  ```sql
  -- 1. Minimum pool config on 26ai Free (~1.5 GB SGA cap)
  --    (Autonomous AI DB Free manages vector memory automatically)
  ALTER SYSTEM SET vector_memory_size = 512M SCOPE = SPFILE;

  -- 2. Verify active Vector Memory Pool allocation
  SELECT pool, alloc_bytes / 1048576 AS alloc_mb,
         used_bytes / 1048576 AS used_mb
  FROM v$vector_memory_pool;

  -- 3. Configure the in-memory HNSW neighbor graph index
  CREATE VECTOR INDEX product_embedding_idx ON product (embedding)
  ORGANIZATION INMEMORY NEIGHBOR GRAPH
  DISTANCE COSINE
  WITH TARGET ACCURACY 95
  PARAMETERS (
      TYPE           HNSW,
      NEIGHBORS      40,
      EFCONSTRUCTION 500
  );
  ```

- **Notes:** Contrast local sizing across both container flavors: `gvenzl/oracle-free:latest` (`ORACLE_CONTAINER_FLAVOR=free`) sets `vector_memory_size = 512M SCOPE = SPFILE` on init (`tools/oracle/on_init/00_configure_vector_memory.sql`) to avoid `ORA-51962`, whereas default `container-registry.oracle.com/database/adb-free:latest-26ai` manages the vector memory pool automatically when `product_embedding_idx` and `chat_route_embedding_idx` (`src/app/db/migrations/0001_cymball_coffee_products.sql`) are created.
  BRIDGE: Fast vector search still cannot distinguish user intent or exact SKUs on its own—that brings us to Step 3.
- **Sources:** `tools/oracle/on_init/00_configure_vector_memory.sql`, `src/app/db/migrations/0001_cymball_coffee_products.sql`

### 31. Step 3: Route Intent in SQL (No Extra LLM Call)

- **Target:** `dba_s34`
- **Title:** Step 3: Route Intent in SQL (No Extra LLM Call)
- **Subtitle:** Score 25 route exemplars across 5 route labels in the same Oracle 26ai turn
- **Left card (`Routing as an Indexed Lookup Table`):**
  - Earlier two-step pipelines spent `~300–450 ms` on a classifier LLM call before querying Oracle
  - `chat_route` stores `25` exemplars across `5` labels (`PRODUCT_RAG`, `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, `ORDER_STATUS`, `GENERAL_CONVERSATION`) with keywords (`CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE`, `SYNC (ON COMMIT)`) and `VECTOR(3072, FLOAT32)` HNSW embeddings
  - Sanitize raw user text into `{token} ACCUM ...` before `CONTAINS` to prevent `DRG-50901` operator errors
- **Right comparison table:**

  | Step | Two-step pipeline | Single hybrid SQL turn |
  | :--- | :--- | :--- |
  | Calls before composing reply | 1 embedding + 1 classifier LLM + 1–2 SQL | 1 embedding (cached) + 1 SQL |
  | Routing + retrieval (local example) | ~350–500 ms | ~15–25 ms in Oracle 26ai |
  | Exact SKUs, ZIPs, `"decaf"` | Weak in pure vector search | `CTXSYS.CONTEXT` (`CONTAINS` / `SCORE`) |
  | Off-menu brands (`"Folgers"`) | Extra LLM check | `JSON_TABLE` + `CONTAINS` in same turn |

- **Notes:** Turning intent classification into an indexed lookup table (`chat_route`, seeded from `src/app/db/fixtures/chat_route.json` and resolved by `HybridRouteResolver` in `src/app/domain/chat/services/_router.py`) eliminates an entire network LLM round-trip. Point out `build_oracle_text_query()` (`src/app/lib/text_search.py`), which strips Oracle Text operators and stopwords so `CONTAINS` never raises `DRG-50901`, and note that timings are local example timings rather than benchmarks (backup B15 holds the `PersonaManager` prompts from `src/app/domain/system/services/_personas.py`).
  BRIDGE: Now let's look at Step 4: the single Reciprocal Rank Fusion SQL query that joins lexical and HNSW rankings together.
- **Sources:** `SLIDES.md` slide 4; `src/app/domain/chat/services/_router.py`, `src/app/lib/text_search.py`, `src/app/db/fixtures/chat_route.json`

### 32. Step 4: It's All SQL — Hybrid RRF (k = 60)

- **Target:** `dba_s35`
- **Title:** Step 4: It's All SQL — Hybrid RRF (k = 60)
- **Subtitle:** Fuse Oracle Text `SCORE` and HNSW `VECTOR_DISTANCE` positions in one explainable query
- **Left card (`Why Reciprocal Rank Fusion Works`):**
  - Oracle Text `SCORE` (`1..100` inverse-frequency TF-IDF family, BM25-style ranking) and cosine similarity (`-1..1`) use incompatible scales
  - RRF sums `1 / (60 + rank)` across a `FULL OUTER JOIN` so rows strong in both lists beat a noisy `#1` in only one list (`1/63 + 1/63 = 0.0317` vs `1/61 = 0.0164`)
  - Isolating `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX` inside `prod_vec_top` and numbering with `ROWNUM` in `prod_vec` preserves `VECTOR INDEX HNSW SCAN` in `DBMS_XPLAN`
- **Right code card (`sql`):**

  ```sql
  WITH prod_lex AS (
      SELECT p.id, p.name, SCORE(2) AS lex_score,
             ROW_NUMBER() OVER (ORDER BY SCORE(2) DESC, p.id) AS lex_rank
      FROM product p
      WHERE :has_text_query = 1 AND CONTAINS(p.description, :text_query, 2) > 0
      FETCH FIRST :limit ROWS ONLY
  ),
  prod_vec_top AS (
      SELECT p.id, p.name,
             1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) AS vec_sim
      FROM product p
      WHERE p.embedding IS NOT NULL
      ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
      FETCH APPROX FIRST :limit ROWS ONLY
  ),
  prod_vec AS (
      SELECT pv.*, ROWNUM AS vec_rank FROM prod_vec_top pv
  )
  SELECT COALESCE(l.id, v.id) AS entity_id,
         (CASE WHEN l.lex_rank IS NOT NULL THEN 1.0 / (:rrf_k + l.lex_rank) ELSE 0 END) +
         (CASE WHEN v.vec_rank IS NOT NULL THEN 1.0 / (:rrf_k + v.vec_rank) ELSE 0 END) AS rrf_score
  FROM prod_lex l FULL OUTER JOIN prod_vec v ON l.id = v.id
  ORDER BY rrf_score DESC FETCH FIRST :limit ROWS ONLY;
  ```

- **Notes:** Quote the product leg of `hybrid-search-turn` (`src/app/db/sql/hybrid.sql`, `SLIDES.md` slide 5), which runs the exact same fusion pattern across `chat_route`, `product`, and `store` in one round trip. Highlight the Oracle 26ai (`23.26.0.0.0`) optimizer detail every DBA appreciates: keeping `ROW_NUMBER()` out of `prod_vec_top` prevents `TABLE ACCESS FULL` fallback and preserves `VECTOR INDEX HNSW SCAN IN-FILTER` alongside `DOMAIN INDEX` in `DBMS_XPLAN`.
  BRIDGE: Let's wrap up with three concrete places you can start on Monday morning.
- **Sources:** `src/app/db/sql/hybrid.sql`; `SLIDES.md` slide 5

## Close

### 33. Let's Recap: Where to Start on Monday

- **Target:** `dba_s28` (three full-width cards)
- **Title:** Let's Recap: Where to Start on Monday
- **Subtitle:** Pick one workflow to try on a development schema this week
- **Cards:**
  - **Connect Your Toolchain:** Wire Antigravity (`agy` CLI + IDE) to a read-only Oracle 26ai user with SQLcl MCP (`sql -mcp`) and a team `tools.yaml` in MCP Toolbox (`mcp-toolbox.dev`).
  - **Document & Guard Schemas:** Let `agy` review one regressed plan and draft Oracle 26ai `ANNOTATIONS` for one schema, ready for Knowledge Catalog MCP (`docs.cloud.google.com/knowledge-catalog/docs/use-remote-mcp`).
  - **Run the Reference App:** Spin up Cymbal Coffee—Litestar on `http://localhost:8000` plus bundled Oracle APEX 26.1 on `https://localhost:8443/ords/apex`—and inspect the `DBMS_XPLAN` for single-query Hybrid RRF (`github.com/cofin/oracledb-vertexai-demo`).
- **Notes:** Summarize the three Monday actions so every DBA leaves with a concrete starting point whether they focus on daily diagnostics, fleet schema governance, or building AI applications on Oracle 26ai (`src/app/db/sql/hybrid.sql` and `src/apex/cymbal-coffee-ops/` in the repository).
  BRIDGE: Thank you—grab the QR links on the closing slide and let's open the floor for questions.
- **Sources:** NorCal 55–56

### 34. Thank You

- **Target:** `dba_s41`
- **Title:** Thank You
- **Content:** Non-overlapping closing title, speaker contact block (`Cody Fincher · linkedin.com/in/cofin · github.com/cofin`), and closing QR codes (`github.com/cofin/oracledb-vertexai-demo`, `mcp-toolbox.dev`, `docs.cloud.google.com/knowledge-catalog/docs/use-remote-mcp`, plus the event survey QR when provided by the conference).
- **Notes:** Thank the audience and open for questions. No `BRIDGE:` line.
- **Sources:** NorCal 56
