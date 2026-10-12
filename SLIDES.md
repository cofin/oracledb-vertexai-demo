# How the Cymbal Coffee Native AI & Hybrid Search Pipeline Works

> A walkthrough of the Cymbal Coffee architecture: Litestar → single-query
> Oracle 26ai Hybrid RRF routing & retrieval → deterministic grounded composers
> & native `AgentRuntime` (`google-genai`) → Oracle-backed sessions, MCP/A2A
> protocols, and `litestar-queues`. Code references point at
> `src/app/domain/chat/`, `src/app/domain/ai/`, and `src/app/db/sql/`.

---

## Slide 0 — The whole turn at a glance

```text
Browser ──POST /api/chat/stream (SSE)──► CoffeeChatController
                                              │ validate msg/persona, read opt-in coords
                                              │ derive (user_id, session_id)
                                              ▼
                              AgentOrchestrationService.stream_conversation_turn
       ┌──────────────────────────────────────┼────────────────────────────────────────┐
       ▼                                      ▼                                        ▼
  Response-cache check          Single-Query Oracle 26ai Hybrid RRF            Oracle AI Session
  (skipped if coords)           `hybrid-search-turn` + `hybrid-term-hits`      (`agent_session` /
       │ hit → yield final      1 embedding + 1 SQL round trip (~15–25 ms)      `agent_event`)
       │                        fuses BM25-style CONTAINS/SCORE + HNSW vector
       └──────────────────────► Route + Product & Store Candidates + Term Hits
                                              │
        ┌──────────────┬───────────────┬──────┴─────────┬──────────────────────┐
        ▼              ▼               ▼                ▼                      ▼
   PRODUCT_RAG   STORE_LOCATION  PRODUCT_AVAIL    ORDER_STATUS         GENERAL_CONVERSATION
   (grounded +    (grounded +     (grounded +      (explicit            → Native AgentRuntime
    off-menu       distance/maps)  inventory SQL)   unsupported)          (`Gemini 3.8 Flash`
    term_hits)                                                             + 5 closure tools)
        │              │               │                │                      │
        └──────────────┴───────────────┴────────────────┴──────────────────────┘
                                              ▼
                     AgentStreamService → SSE frames (`session`, `tool_call`,
                     `tool_end`, `delta`, `ping`, `final` with full telemetry)
```

---

## Slide 1 — One chat turn, one SSE stream

**The shape of the system**

- Single streaming endpoint: `POST /api/chat/stream` → returns a
  `ServerSentEvent` stream (`domain/chat/controllers/_chat.py`)
- Structured wire frames (`AgentStreamService` in `domain/ai/runtime/_stream.py`):
  - `session` → establishes `session_id` and `turn_id`
  - `tool_call` / `tool_end` → live tool invocation progress
  - `delta` → incremental token chunks
  - `ping` → 5-second keep-alive frames
  - `final` → complete `ChatResponse` payload (`answer`, `intent_detected`,
    `search_metrics`, `sql_phases`, `from_cache`, `embedding_cache_hit`,
    `store_results`, `inventory_results`, `map_actions`, `location_context`)

> Every turn—whether served from the response cache, answered by a deterministic
> grounded route, or streamed from the multi-step `AgentRuntime`—emits the exact
> same SSE frame contract consumed by `chat-stream.js` and `telemetry.js`.

---

## Slide 2 — From browser session to native Oracle AI session

**Durable session & event persistence (`domain/ai/runtime/_store.py`)**

- Litestar assigns each browser an anonymous cookie session
- At the controller boundary, `session_id` and `user_id = f"web:{session_id}"`
  bridge the browser session into the AI runtime
- Conversation state and ordered turn events live in **Oracle 26ai** via
  `OracleSessionStore` and `OracleEventStore` (`db/sql/ai-runtime.sql`):
  - `agent_session` — session metadata, persona/state JSON CLOB, timestamps
  - `agent_event` — monotonically sequenced (`UNIQUE (session_id, seq)`),
    cascade-deleted (`ON DELETE CASCADE`) user, model, and tool events
- Each store operation opens a short-lived session from the app-scoped `SQLSpec`
  manager and explicitly commits (`await driver.commit()`), preventing
  interleaved streaming transactions

---

## Slide 3 — Why One Hybrid RRF Query Lets Us Skip the Classifier Search

**Replacing "Classify-Then-Search" with Single-Query Hybrid RRF (`domain/chat/services/_router.py`)**

Previously, every uncached chat turn made **two serial steps** before composing an answer:
1. An LLM intent-classification call (`Gemini Flash-Lite` enum output, ~300–450 ms)
2. A separate Oracle vector search (`vector-search-products`) or store query

Now, **one query embedding** (`gemini-embedding-2`, 3072 dims, cached in `embedding_cache`) drives **one Oracle 26ai Hybrid RRF SQL statement (`hybrid-search-turn`)** that simultaneously ranks route exemplars (`chat_route`), products (`product`), and stores (`coffee_store`):

| Dimension | Old: LLM Classifier + Vector Search | New: Single-Query Oracle 26ai Hybrid RRF |
|---|---|---|
| **Network round trips before answer** | 1 Vertex embedding + 1 LLM call + 1–2 SQL queries | **1 Vertex embedding (cached) + 1 Hybrid SQL query** |
| **Routing + retrieval latency** | ~350–500 ms | **~15–25 ms inside Oracle 26ai** |
| **Exact token matching** (`"decaf"`, `"75208"`, `"Bishop Arts"`, SKUs) | Weak (dense embeddings blur exact tokens & negations) | **Strong** — BM25-style lexical ranking via Oracle Text `CONTAINS`/`SCORE` (`MULTI_COLUMN_DATASTORE`) |
| **Semantic vibe matching** (`"bright citrus morning pour-over"`) | Strong (`VECTOR_DISTANCE` cosine similarity) | **Strong** — HNSW `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX` |
| **Off-menu brand detection** (`"Do you carry Folgers?"`) | Required a second constrained LLM call | **In-DB lexical term hits (`hybrid-term-hits`)** proves `folgers = 0` hits in the same turn |

> **Note on Oracle 26ai Lexical Scoring & Sparse Vectors:** Oracle Text `CONTAINS(...)` / `SCORE(1)` uses an inverse-frequency TF-IDF scoring formula (0–100) over `CTXSYS.CONTEXT` indexes—providing **BM25-style lexical ranking** directly on relational columns (`MULTI_COLUMN_DATASTORE` across `name`, `description`, `category`, and store `city`/`state`/`postal_code`). Oracle AI Database 26ai also supports `VECTOR(..., SPARSE)` for client-generated BM25/SPLADE sparse vectors when external sparse encoders are used.

---

## Slide 4 — Inside the Single-Query Hybrid RRF SQL

**Reciprocal Rank Fusion (`db/sql/hybrid.sql` — `hybrid-search-turn`)**

Oracle 26ai fuses the **lexical rank** ($r_{\text{lex}}$ from `CONTAINS` / `SCORE(1)`) and the **HNSW vector rank** ($r_{\text{vec}}$ from `VECTOR_DISTANCE(..., COSINE) FETCH APPROX`) across `chat_route`, `product`, and `coffee_store` in a single statement using Reciprocal Rank Fusion ($k = 60$):

$$\text{RRF}(d) = \frac{1}{k + r_{\text{lex}}(d)} + \frac{1}{k + r_{\text{vec}}(d)}, \quad k = 60$$

```sql
WITH vec_products AS (
    SELECT p.id AS entity_id,
           ROW_NUMBER() OVER (
               ORDER BY VECTOR_DISTANCE(p.embedding, TO_VECTOR(:query_vector, 3072, FLOAT32), COSINE)
           ) AS vec_rank,
           ROUND(1 - VECTOR_DISTANCE(p.embedding, TO_VECTOR(:query_vector, 3072, FLOAT32), COSINE), 4) AS similarity_score
    FROM product p
    WHERE p.embedding IS NOT NULL AND p.in_stock = 1
    ORDER BY VECTOR_DISTANCE(p.embedding, TO_VECTOR(:query_vector, 3072, FLOAT32), COSINE)
    FETCH APPROX FIRST :vec_k ROWS ONLY
),
lex_products AS (
    SELECT p.id AS entity_id,
           SCORE(1) AS lex_score,
           ROW_NUMBER() OVER (ORDER BY SCORE(1) DESC, p.id ASC) AS lex_rank
    FROM product p
    WHERE :has_text_query = 1 AND p.in_stock = 1
      AND CONTAINS(p.search_text, :text_query, 1) > 0
    FETCH FIRST :lex_k ROWS ONLY
)
SELECT COALESCE(v.entity_id, l.entity_id) AS entity_id,
       (NVL(1.0 / (:rrf_k + l.lex_rank), 0) + NVL(1.0 / (:rrf_k + v.vec_rank), 0)) AS rrf_score
FROM vec_products v
FULL OUTER JOIN lex_products l ON v.entity_id = l.entity_id;
```

- **Why `FETCH APPROX` matters:** Ordering directly by `VECTOR_DISTANCE(..., COSINE)` with `FETCH APPROX FIRST :vec_k ROWS ONLY` activates the Oracle 26ai `INMEMORY NEIGHBOR GRAPH` (HNSW) index instead of falling back to a full table scan.
- **Injection-safe Oracle Text queries:** `build_oracle_text_query()` wraps every sanitized token in `{token}` literal braces and joins them with `ACCUM` (`{decaf} ACCUM {espresso}`), neutralizing Oracle Text operators (`SYN`, `NEAR`, `FUZZY`, `%`) in user input.

---

## Slide 5 — Native `AgentRuntime` & Per-Request Closure-Bound Tools

**Skipping static ADK graphs for a native `google-genai` runtime (`domain/ai/runtime/_loop.py`)**

When the hybrid router selects `GENERAL_CONVERSATION`, execution enters our lightweight, re-entrant `AgentRuntime`:

- **Single aggregated model event per step:** `GeminiModelClient.generate_stream` yields `partial=True` token chunks for low-latency SSE `delta` frames, then `AgentRuntime.run_stream` emits one `partial=False` `AgentEvent` carrying the full text, tool calls, `usage_metadata`, and base64-encoded Gemini 3 `thought_signature` + `call_id`s
- **5 grounded tools bound per turn (`domain/chat/services/_tools.py`):**
  - `search_products` (Oracle 26ai Hybrid RRF product search)
  - `get_product_details` (catalog lookup by name or ID)
  - `find_nearby_stores` (Haversine distance + city/ZIP search + Google Maps links)
  - `check_product_availability` (store-by-store `store_product_inventory` join)
  - `check_order_status` (explicit unsupported stub)
- Each tool closure captures the request-scoped Dishka services and `TurnTelemetryState`, recording every executed SQL statement (`sql_phases`) for the frontend telemetry drawer

---

## Slide 6 — Multi-Protocol Surface & Oracle 26ai Background Queues

**One domain layer powering Web SSE, MCP, A2A, and `litestar-queues`**

- **Model Context Protocol (`LitestarMCP` 0.15 at `POST /mcp`):**
  - `CoffeeMCPController` exposes `search_coffee_products`, `find_coffee_stores`, and `check_coffee_inventory`
  - `CoffeeSkillController` and `CoffeePromptController` publish structured agent skills and prompt templates
- **Agent-to-Agent Protocol (`LitestarA2A` at `POST /a2a` & `/.well-known/agent-card.json`):**
  - `CoffeeAgentExecutor` reuses the app-scoped Dishka container and `OwnerScopedTaskStore` with deterministic caller identity and `X-Session-ID` continuity
- **Oracle 26ai Background Task Queues (`litestar-queues[sqlspec]>=0.12.0`):**
  - Uses Oracle `FOR UPDATE SKIP LOCKED` via a dedicated `DatabaseSettings.get_queue_config()` pool (`session_key="queue_db_session"`) so `SQLSpecBackend`'s `fetch_lobs=False` setting never mutates `config.db`'s `enable_AutoLob=True`
  - Runs `@task("system.cache_cleanup", cron="*/15 * * * *")` and `@task("products.embed_missing")` (`coffee bulk-embed` / `coffee worker run`)

---

## Slide 7 — State, Caching, Telemetry & Privacy

**What persists, what's measured, what's protected**

- **Persisted in Oracle 26ai:** `agent_session` and `agent_event` conversation history; `response_cache`; `embedding_cache`; per-turn `search_metric` telemetry; and `litestar-queues` task tables
- **Live SQL phase telemetry:** Every turn records `sql_phases` (`hybrid-search-turn`, `hybrid-term-hits`, `hybrid-search-products`, store/inventory queries) with execution time, row count, and masked binds for the UI's "What Queries Ran" inspector
- **Coordinate privacy by construction:** Browser geolocation coordinates are opt-in, request-scoped, masked as `<REQUEST_COORDINATES>` in telemetry, never written to `agent_event` or logs, and automatically bypass `response_cache`

---

## Appendix A — What's deterministic vs. LLM-written

| Stage | Engine | Free-form LLM text? |
|---|---|---|
| Turn routing & candidate retrieval | **Oracle 26ai Hybrid RRF (`hybrid-search-turn`)** | **No** (single SQL query over `chat_route`, `product`, `coffee_store`) |
| Off-menu token verification | **Oracle Text `JSON_TABLE` + `CONTAINS` (`hybrid-term-hits`)** | **No** (exact per-token catalog hit counts) |
| `PRODUCT_RAG` answer | Deterministic grounded formatter (`_grounded.py`) over RRF candidates + `term_hits` | **No** (facts, prices, and off-menu pivot built directly from Oracle rows) |
| `STORE_LOCATION` answer | Deterministic formatter over store/distance rows + Maps URLs | **No** |
| `PRODUCT_AVAILABILITY` answer | Deterministic formatter over `store_product_inventory` rows | **No** |
| `ORDER_STATUS` answer | Explicit unsupported response | **No** |
| `GENERAL_CONVERSATION` answer | Native `AgentRuntime` (`Gemini 3.8 Flash` + 5 grounded tools) | **Yes** |

**Takeaway:** Routing, candidate retrieval, and off-menu brand detection all happen in **one Oracle 26ai database turn** without an extra LLM classifier or post-generation guard call. The LLM is invoked only when open-ended conversation or multi-step tool reasoning is needed.

---

## Appendix B — Off-menu / competitor handling with BM25-style `term_hits` + RRF

**Example: user asks `"Do you carry Folgers?"` vs `"I need something bold"`**

### The Dense-Vector Trap

In 3,072-dimensional embedding space (`gemini-embedding-2`), `"Do you carry Folgers?"` and `"I need something bold"` land in the **exact same cosine similarity band (~0.65–0.72)** against Cymbal Coffee dark roasts because *Folgers is coffee*. A vector distance threshold cannot separate a valid taste preference from an off-menu brand request.

### How Single-Query Hybrid RRF + `hybrid-term-hits` Solves It Without an Extra LLM Call

Instead of paying for a second LLM call to guess whether the user named an off-menu brand, we let **Oracle Text lexical matching and dense vector search work together in the same database turn**:

1. **Hybrid RRF (`hybrid-search-turn`)** runs both legs at once:
   - The **dense vector leg** (`VECTOR_DISTANCE ... FETCH APPROX`) retrieves our closest in-stock dark/medium roasts (e.g., *House Blend*, *Midnight Espresso*).
   - The **lexical leg** (`CONTAINS(p.search_text, '{folgers}', 1)`) returns **0 rows** because `"Folgers"` appears nowhere in `product(name, description, category)`.
2. **Per-Token Lexical Hit Check (`hybrid-term-hits`)** evaluates each content token from the user's message against the `product` Oracle Text index in a single `JSON_TABLE` query:
   ```sql
   SELECT t.term,
          (SELECT COUNT(*) FROM product p
           WHERE p.in_stock = 1 AND CONTAINS(p.name, t.term_query, 1) > 0) AS hit_count
   FROM JSON_TABLE(:terms_json, '$[*]'
       COLUMNS (term VARCHAR2(64) PATH '$.term', term_query VARCHAR2(128) PATH '$.term_query')
   ) t;
   ```
3. **Deterministic Grounded Pivot (`compose_product_rag_answer` in `domain/chat/services/_grounded.py`)**:
   - When a specific product/brand noun token has `term_hits[token] == 0` while vector candidates exist, the composer deterministically responds:
     > *"We don't carry **Folgers** on our menu, but based on your interest, our closest match is **House Blend** (\$3.75) — a smooth, balanced medium roast."*
   - When the user asks for `"decaf oat milk latte"`, `term_hits` confirms catalog matches AND the lexical RRF leg boosts exact `"decaf"` products to rank #1 above higher-vector-similarity caffeinated roasts.
