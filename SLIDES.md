# How the Cymbal Coffee Demo Works

> Architecture notes for Oracle DBAs: how a chat request moves from the browser
> through Oracle 26ai (`CTXSYS.CONTEXT` text indexes + `VECTOR(3072, FLOAT32)`
> HNSW indexes) and Vertex AI (`gemini-embedding-2` and `Gemini 3.8 Flash`).
> Code paths below are relative to the repository root.
>
> **Presentation guide:** For the full 34-slide "Oracle in the Age of Gemini"
> deck storyboard, speaker guide, and verified facts, see
> [`.agents/bundles/knowledge/presentation/index.md`](.agents/bundles/knowledge/presentation/index.md).
> The sections below correspond to **Build Real Apps: Cymbal Coffee (Slides 26–32)**.

---

## Slide 0 — Request flow for one chat turn (Deck Slide 28)

```text
Browser ──POST /api/chat/stream (SSE)──► CoffeeChatController
                                              │ validate input, read opt-in lat/lng
                                              │ map cookie → (user_id, session_id)
                                              ▼
                              AgentOrchestrationService.stream_conversation_turn
       ┌──────────────────────────────────────┼────────────────────────────────────────┐
       ▼                                      ▼                                        ▼
  Response-cache lookup         One hybrid SQL query in Oracle 26ai           Session tables
  (skipped if lat/lng set)      `hybrid-search-turn` + `hybrid-term-hits`     (`agent_session`,
       │ hit → return cached     1 embedding + 1 SQL call (~15–25 ms)          `agent_event`)
       │                         combines Oracle Text SCORE + vector distance
       └──────────────────────► Picks route + top products/stores + term hits
                                              │
        ┌──────────────┬───────────────┬──────┴─────────┬──────────────────────┐
        ▼              ▼               ▼                ▼                      ▼
   PRODUCT_RAG   STORE_LOCATION  PRODUCT_AVAIL    ORDER_STATUS         GENERAL_CONVERSATION
   (SQL rows →    (SQL rows →     (SQL rows →      (static notice:      (Gemini 3.8 Flash
    Python text)   Python text)    Python text)     not implemented)     + 5 parameterized
        │              │               │                │                SQL tool functions)
        └──────────────┴───────────────┴────────────────┴──────────────────────┘
                                              ▼
                     Server-Sent Events (`session`, `tool_call`, `tool_end`,
                     `delta`, `ping`, `final` with SQL execution timings)
```

---

## Slide 1 — What a vector is, in Oracle terms (Deck Slides 22, 24, 29–30)

**Before looking at the app code, here is how the AI pieces map to Oracle 26ai:**

- **Embeddings (`VECTOR(3072, FLOAT32)`):** An embedding model (`gemini-embedding-2`) takes a string—like a product description or a customer's question—and returns an array of 3,072 32-bit floats (`~12 KB` per row). Texts about similar topics produce arrays that point in a similar direction, which Oracle compares using `VECTOR_DISTANCE(col, :query_vec, COSINE)`.
- **Vector indexes (`INMEMORY NEIGHBOR GRAPH`):** Scanning `VECTOR_DISTANCE` across a table is a full scan. Oracle 26ai's HNSW vector index is an in-memory graph stored in the SGA's Vector Pool (managed automatically on Autonomous AI Database Free, or sized via `vector_memory_size` on Oracle Database Free).
- **Getting the optimizer to use the index:** Just as a B-tree index requires a matching predicate, Oracle only uses an HNSW vector index when the query orders by `VECTOR_DISTANCE(...)` and includes `FETCH APPROX FIRST :k ROWS ONLY`. Without `FETCH APPROX`, Oracle performs an exact full table scan.
- **Why we still use Oracle Text (`CTXSYS.CONTEXT`):** Vector distance measures broad topic similarity, not exact words. It is great for *"something bright and citrusy for a morning pour-over,"* but poor at exact strings like SKU codes (`"ESP-ROM-001"`), ZIP codes (`"75201"`), neighborhood names (`"Arts District"`), or brand names. Oracle Text (`CONTAINS` / `SCORE`) already handles exact words well, so we run both in the same SQL statement.

---

## Slide 2 — One HTTP endpoint, streamed back as Server-Sent Events (Deck Slide 28)

**`POST /api/chat/stream` (`src/app/domain/chat/controllers/_chat.py`)**

- The browser opens one HTTP POST to the Litestar app (`http://localhost:8000`) and reads a stream of JSON frames (`src/app/domain/ai/runtime/_stream.py`):
  - `session` — returns the `session_id`
  - `tool_call` / `tool_end` — emitted when the model runs a database lookup function
  - `delta` — chunks of response text as they arrive
  - `ping` — 5-second keep-alive so load balancers do not drop idle connections
  - `final` — the finished turn payload (`type: "final"`), including `sql_phases` (every named SQL query that ran, its bind summary, row count, and elapsed milliseconds)
- Whether a request is answered from the response cache, formatted directly from SQL rows, or handled by the LLM, the browser receives the same `final` event structure.

---

## Slide 3 — Storing conversation history without holding transactions open (Deck Slide 28)

**`OracleSessionStore` and `OracleEventStore` (`src/app/domain/ai/runtime/_store.py`, `src/app/db/sql/ai-runtime.sql`)**

- The web framework gives each browser an anonymous cookie session. The chat controller maps that cookie to `session_id` and `user_id = f"web:{session_id}"`.
- Conversation history is stored in two regular Oracle tables (`src/app/db/migrations/0001_cymball_coffee_products.sql`):
  - `agent_session` — session metadata and JSON state (`CLOB CHECK (state IS JSON)`)
  - `agent_event` — ordered turn history (`UNIQUE (session_id, seq)`, `ON DELETE CASCADE`) recording user messages, model replies, and tool calls/results
- **Transaction boundary:** LLM calls over the network take hundreds of milliseconds to several seconds. You never want a database session holding an open transaction or row locks while waiting on an external API. Each `OracleLoaderService` store method borrows a connection from the pool (`provide_app_session()`), runs its `MERGE` or `INSERT`, commits immediately (`await driver.commit()`), and returns the connection to the pool before any model call begins.

---

## Slide 4 — Replacing a separate LLM router call with one SQL query (Deck Slide 31)

**`HybridRouteResolver` (`src/app/domain/chat/services/_router.py`)**

Earlier versions of this app made two sequential trips before answering a question:

1. Call a smaller LLM (`Flash-Lite`) to classify the user's question into one of 5 route labels (`~300–450 ms` network round trip).
2. Run a separate vector search or store lookup in Oracle.

We replaced that first LLM call by putting 25 route exemplars across our 5 route labels into a small lookup table (`chat_route`, with text keywords and a 3,072-float embedding per exemplar) and querying `chat_route`, `product`, and `store` together in a single SQL statement (`hybrid-search-turn`):

| Step | Previous two-step pipeline | Single hybrid SQL query |
|---|---|---|
| **Calls before composing answer** | 1 embedding call + 1 LLM classifier call + 1–2 SQL queries | 1 embedding call (cached in `embedding_cache`) + 1 SQL query |
| **Routing + retrieval time** | ~350–500 ms (dominated by the extra LLM network call) | ~15–25 ms inside Oracle 26ai (example local timings) |
| **Exact terms** (`"ESP-ROM-001"`, `"75201"`, `"Arts District"`) | Handled poorly by vector search alone | Matched by `CTXSYS.CONTEXT` (`MULTI_COLUMN_DATASTORE`) via `CONTAINS` / `SCORE` |
| **Descriptive questions** (`"low-acid dark roast"`) | Matched by `VECTOR_DISTANCE` | Matched by HNSW `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX` |
| **Off-menu brand check** (`"Do you sell Folgers?"`) | Needed another LLM call to detect the off-menu brand | Checked in the same database turn with `CONTAINS` over `JSON_TABLE` (`hybrid-term-hits`) |

> **A note on Oracle Text scoring:** Oracle Text `CONTAINS(...)` / `SCORE(...)` computes an inverse-frequency TF-IDF score (`0–100`) over `CTXSYS.CONTEXT` indexes. It serves the same role here that BM25 plays in search engines: rewarding exact, rare word matches across `name`, `description`, `category`, `sku`, and store `city`/`state`/`zip`.

---

## Slide 5 — How the hybrid RRF query works (Deck Slide 32)

**`hybrid-search-turn` (`src/app/db/sql/hybrid.sql`)**

Oracle Text `SCORE(...)` returns an integer from `1` to `100`, while `1 - VECTOR_DISTANCE(..., COSINE)` returns a float from `-1.0` to `1.0`. Because those two scales are not directly comparable, you cannot just add the raw scores together without one dominating the other.

Instead, we rank each list with `ROW_NUMBER()` and combine the **positions** using Reciprocal Rank Fusion (RRF):

$$\text{RRF}(d) = \frac{1}{60 + r_{\text{lex}}(d)} + \frac{1}{60 + r_{\text{vec}}(d)}$$

- **Why the `60` is there:** Without a constant offset, rank #1 (`1/1 = 1.0`) is worth ten times rank #10 (`1/10 = 0.1`), so a single noisy #1 match in one list beats a row that ranked #3 in *both* lists (`1/3 + 1/3 = 0.67`). Adding `60` flattens the curve so a product that scores well in both text and vector search (`1/63 + 1/63 = 0.0317`) beats a product that only ranked #1 in one list (`1/61 + 0 = 0.0164`).

```sql
WITH prod_lex AS (
    SELECT p.id, p.name, p.description, p.category, p.price,
           CASE WHEN p.in_stock THEN 1 ELSE 0 END AS in_stock,
           SCORE(2) AS lexical_score,
           ROW_NUMBER() OVER (ORDER BY SCORE(2) DESC, p.id) AS lexical_rank
    FROM product p
    WHERE :has_text_query = 1
      AND CONTAINS(p.description, :text_query, 2) > 0
    FETCH FIRST :limit ROWS ONLY
),
prod_vec_top AS (
    SELECT p.id, p.name, p.description, p.category, p.price,
           CASE WHEN p.in_stock THEN 1 ELSE 0 END AS in_stock,
           1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) AS vector_similarity
    FROM product p
    WHERE p.embedding IS NOT NULL
    ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
    FETCH APPROX FIRST :limit ROWS ONLY
),
prod_vec AS (
    SELECT pv.id, pv.name, pv.description, pv.category, pv.price,
           pv.in_stock, pv.vector_similarity,
           ROWNUM AS vector_rank
    FROM prod_vec_top pv
)
SELECT COALESCE(l.id, v.id) AS entity_id,
       (CASE WHEN l.lexical_rank IS NOT NULL THEN 1.0 / (:rrf_k + l.lexical_rank) ELSE 0 END) +
       (CASE WHEN v.vector_rank IS NOT NULL THEN 1.0 / (:rrf_k + v.vector_rank) ELSE 0 END) AS rrf_score
FROM prod_lex l
FULL OUTER JOIN prod_vec v ON l.id = v.id
ORDER BY rrf_score DESC
FETCH FIRST :limit ROWS ONLY;
```

- **Why `prod_vec_top` is isolated in its own subquery:** In Oracle AI Database 26ai (`23.26.0.0.0`), putting `ROW_NUMBER() OVER (ORDER BY VECTOR_DISTANCE(...))` inside the same query block as `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST :limit ROWS ONLY` causes the Cost-Based Optimizer to fall back to `TABLE ACCESS FULL`. Isolating the approximate vector top-K inside `prod_vec_top` and numbering rows with `ROWNUM AS vector_rank` in `prod_vec` preserves `VECTOR INDEX HNSW SCAN IN-FILTER` (`PRODUCT_EMBEDDING_IDX`) alongside `DOMAIN INDEX` (`PRODUCT_HYBRID_CTX_IDX`).

- **Escaping user input for `CONTAINS`:** Oracle Text has its own query grammar (`AND`, `OR`, `NOT`, `NEAR`, `FUZZY`, `SYN`, `%`). Passing raw user input to `CONTAINS` can raise `DRG-50901` syntax errors. `build_oracle_text_query()` (`src/app/lib/text_search.py`) strips punctuation and reserved words, wraps each token in literal braces `{token}`, and joins them with `ACCUM` (e.g., `{decaf} ACCUM {espresso}`).

---

## Slide 6 — Grounded SQL answers vs. open-ended LLM turns (Deck Slides 27–28)

**Why product prices and store inventory cannot be hallucinated**

When `hybrid-search-turn` comes back, 4 of the 5 routes are handled deterministically by `GroundedRouteService` (`src/app/domain/chat/services/_grounded.py`):

| Route | How the reply is built | Calls Gemini? |
|---|---|---|
| `PRODUCT_RAG` | Python formats the top RRF product rows (with constrained ID selection or deterministic off-menu fallback) | Constrained ID selector only (0 for off-menu) |
| `STORE_LOCATION` | Python formats `store` rows, Haversine distance, and Google Maps links | No |
| `PRODUCT_AVAILABILITY` | Python formats `store_product_inventory` join rows (`quantity_available`, `stock_status`) | No |
| `ORDER_STATUS` | Returns a static message that order tracking is not part of the demo | No |
| `GENERAL_CONVERSATION` | Runs `AgentRuntime` (`Gemini 3.8 Flash`) with 5 parameterized SQL tool functions | **Yes** |

When a question is open-ended (`GENERAL_CONVERSATION`), it runs `AgentRuntime` (`src/app/domain/ai/runtime/_loop.py`). The model cannot write arbitrary SQL; it can only ask the application to invoke 5 predefined Python functions (`src/app/domain/ai/services/_tools.py`):

- `search_products` — runs `hybrid-search-products`
- `get_product_details` — runs `get-product` filtered by `id = :id` or `name = :name`
- `find_nearby_stores` — runs `list-stores` (with Haversine distance ranking) or `find-stores-by-location`
- `check_product_availability` — runs `find-product-availability-by-query` (while `GroundedRouteService` uses `find-stores-with-product-inventory` when a candidate product ID is already matched)
- `check_order_status` — returns the unsupported-feature notice

Each function uses standard `:bind` parameters on the request's database connection and appends its execution time and row count to `sql_phases` so the UI can show the exact SQL that ran.

---

## Slide 7 — Background jobs, pool isolation, APEX 26.1, and MCP / A2A endpoints (Deck Slide 28)

**How the rest of the service connects to Oracle 26ai**

- **Database-backed job queue (`litestar-queues`):**
  - Instead of adding Redis or an external broker, background jobs (`products.embed_missing` for `coffee bulk-embed` and `system.cache_cleanup` every 15 minutes) use a table in Oracle 26ai polled with `FOR UPDATE SKIP LOCKED`.
  - **Driver and pool detail worth knowing (`get_queue_config()` in `src/app/lib/settings/_database.py`):** SQLSpec `0.69.0` configures `driver_features={"enable_session_tracing": True}`, wire-level `sqlcommenter` trace context, `wallet_zip` mTLS wallet extraction, and `python-oracledb`'s default `fetch_lobs=False` mode so `CLOB` and `BLOB` columns under 1 GB arrive inline as plain Python `str` and `bytes` values without extra LOB locator round-trips. Giving `litestar-queues` its own `OracleAsyncConfig` (`min=1, max=4`, `session_key="queue_db_session"`) isolates background queue polling and `OracledbAsyncQueueStore`'s in-place config mutations from the primary application pool.
- **Oracle APEX 26.1 + Vertex AI (`src/apex/cymbal-coffee-ops/`):**
  - Inside the persistent Autonomous AI Database Free 26ai container (`container-registry.oracle.com/database/adb-free:latest-26ai`, pre-bundled Oracle APEX 26.1.5 + ORDS 26.3 on `https://localhost:8443/ords/apex`, workspace `COFFEE`, schema `APP`), the source-controlled APEX 26.1 app (`compatibilityMode: 26.1`, App ID `100`) queries the same `APP` tables and invokes Gemini from PL/SQL (`APEX_AI.GENERATE` via `COFFEE_VERTEX_AI`).
  - `COFFEE_VERTEX_AI` connects directly to Vertex AI's OpenAI-compatible endpoint (`https://aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/endpoints/openapi`, `model="google/gemini-3.8-flash"`, with `DBMS_NETWORK_ACL_ADMIN` host ACEs and `VERTEX_AI_CRED`) or through Litestar's local OpenAI-compatible gateway (`http://host.docker.internal:8000/api/apex/ai/v1` on `ApexAIController` in `src/app/domain/products/controllers/_apex_ai.py`) for zero-expiry local sessions and mTLS workstations.
- **External tool endpoints (`/mcp` and `/a2a`):**
  - The same product, store, and inventory queries are also exposed over the Model Context Protocol (`POST /mcp`, configured by `src/app/server/mcp/_config.py` with `mcp_tool="get_product"`, `mcp_tool="get_store_inventory"`, and `mcp_tool="search_products"` on `src/app/domain/products/controllers/_products.py` and `src/app/domain/products/controllers/_vector.py` alongside prompts and skills in `src/app/domain/ai/mcp/`) and Agent-to-Agent protocol (`POST /a2a` and `GET /.well-known/agent-card.json` in `src/app/domain/ai/a2a/`), gated by `MCP_API_KEY` when configured.

---

## Slide 8 — Caching, query telemetry, and location privacy (Deck Slides 20, 24)

**What we store in Oracle and what we keep out of the database**

- **Stored in Oracle:**
  - `embedding_cache` — caches the 3,072-float vector for repeated search phrases so we do not re-call Vertex AI for the same text
  - `response_cache` — caches final answers keyed by `chat:{sha256(version:model:persona:normalized_query)}` (`make_response_cache_key()` in `src/app/domain/ai/services/_agent.py`)
  - `search_metric` — logs query latency, vector vs. hybrid search timings, and result counts for the analytics dashboard
- **Shown in the UI telemetry drawer:**
  - Every `final` SSE event includes `sql_phases`: the named query key, elapsed milliseconds, row count, and sanitized bind parameters
- **Kept out of the database (browser coordinates):**
  - If a user clicks "Share location" to find nearby stores, their latitude and longitude are used only in memory for that single request's Haversine distance calculation. Coordinates are replaced with `<REQUEST_COORDINATES>` in telemetry, never written to `agent_session`, `agent_event`, `search_metric`, or logs, and bypass `response_cache` so one user's nearby store result is never served to another user.

---

## Appendix — Handling off-menu brands (`"Do you carry Folgers?"`) without an extra LLM call (Deck Slides 31–32)

**Why pure vector search gets this wrong**

If a customer asks *"I want a bold morning coffee"* and another asks *"Do you carry Folgers?"*, `gemini-embedding-2` places both questions at roughly the same cosine similarity (`~0.65–0.72`) against our dark roasts—because Folgers is coffee.

If you only run vector search, you cannot tell those two questions apart with a distance cutoff:

- Set the similarity cutoff around `0.60`, and *"Do you carry Folgers?"* gets answered with *"Try our Dark Roast House Blend."* as if we sell Folgers or didn't read the question.
- Raise the cutoff to `0.80`, and *"I want a bold morning coffee"* returns zero results.

**How `hybrid-term-hits` solves this in SQL**

Instead of making a second LLM call to check whether the user asked for a brand we don't carry, we check the user's words against the `product` Oracle Text index in the same database turn (`hybrid-term-hits` in `src/app/db/sql/hybrid.sql`):

1. **Extract candidate brand/product nouns from the question:** `extract_candidate_terms()` (`src/app/domain/chat/services/_router.py`) pulls quoted terms and capitalized brand/product tokens from the prompt (for *"Do you carry Folgers?"*, the token is `"Folgers"`).
2. **Count exact matches per word using `JSON_TABLE` + `CONTAINS`:**

   ```sql
   SELECT jt.term AS term,
          (SELECT COUNT(*)
           FROM product p
           WHERE CONTAINS(p.description, '{' || jt.term || '}') > 0) AS hit_count
   FROM JSON_TABLE(
       :terms_json,
       '$[*]' COLUMNS (term VARCHAR2(128) PATH '$')
   ) jt;
   ```

3. **Branch in Python (`GroundedRouteService.handle_product_rag` in `src/app/domain/chat/services/_grounded.py`):**
   - `hybrid-search-turn` still returns our closest coffees (`Dark Roast House Blend` at `\$4.99` and `Signature Bold Blend` at `\$4.99`) via the vector leg, while `hybrid-term-hits` tells us `Folgers -> 0` rows in `product(description)` (`MULTI_COLUMN_DATASTORE` over `name`, `category`, `sku`, `description`).
   - When the prompt asks for a specific noun that has `0` catalog hits, `compose_off_menu_alternative()` (`src/app/domain/chat/services/_composers.py`) replies directly:
     > *"Cymbal Coffee does not carry Folgers, but Dark Roast House Blend (\$4.99) is the closest menu option: A smooth, dark roast coffee with notes of chocolate and caramel. Another good menu option is Signature Bold Blend (\$4.99)."*
   - When the user asks *"Do you carry Matcha Green Tea Latte?"* or quotes *`"Espresso Romano"`*, `hybrid-term-hits` finds `hit_count > 0` (`off_menu_terms` stays empty) and `CONTAINS` boosts the matching catalog rows to the top of `hybrid-search-turn`.
