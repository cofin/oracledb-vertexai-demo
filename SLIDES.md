# How the Cymbal Coffee ADK Chat Works

> A walkthrough of the chat pipeline: Litestar → intent routing → ADK agent →
> Oracle-grounded answers. Code references point at `src/app/domain/chat/`.

---

## Slide 0 — The whole turn at a glance

```
Browser ──POST /api/chat/stream (SSE)──► CoffeeChatController
                                              │ validate msg/persona, read opt-in coords
                                              │ bridge Litestar session → ADK (user_id, session_id)
                                              ▼
                                         ADKRunner.stream_request
       ┌──────────────────────────────────────┼───────────────────────────────────┐
       ▼                                        ▼                                   ▼
  Response-cache check                    Flash-Lite intent                   Oracle ADK session
  (skipped if coords)                     classifier (1 call)                 get-or-create
       │ hit → yield final                      │
       └────────────────────────────► deterministic route?
                                               │
        ┌──────────────┬───────────────┬───────┴────────┬─────────────────┐
        ▼              ▼               ▼                ▼                  ▼
   PRODUCT_RAG   STORE_LOCATION  PRODUCT_AVAIL    ORDER_STATUS     GENERAL_CONVERSATION
   (grounded)     (grounded)      (grounded)       (stub)           → ADK Workflow
                                                                         │
                                              ┌──────────────────────────┴─────────┐
                                              │ Workflow graph (max_concurrency=2)  │
                                              │   START→intent ┐                    │
                                              │   START→coffee ┴► JoinNode → merge  │
                                              │   LlmAgent + 7 closure-bound tools  │
                                              └──────────────────────────┬──────────┘
                                                  if vector tool fired → relabel PRODUCT_RAG + re-ground
                                                                         ▼
                                                          stream deltas → final event (SSE)
```

---

## Slide 1 — One chat turn, one SSE stream

**The shape of the system**

- Single endpoint: `POST /api/chat/stream` → returns a `ServerSentEvent` stream
  (`controllers/_chat.py`)
- Events on the wire: many `delta` (token chunks) → exactly one `final` (full
  payload) → `error` on failure
- The `final` event carries the answer **plus all telemetry**: SQL phases,
  timings, cache hits, map actions, masked location context

> Everything below happens inside one async generator that yields dicts. The
> controller just validates input and serializes each yielded dict to SSE.

---

## Slide 2 — From browser session to ADK session

**The identity bridge (`session.py`)**

- Litestar gives each browser an anonymous cookie session
- ADK needs its own `(user_id, session_id)` to key conversation state in Oracle
- `adk_session_identity(request)` derives them once and stores them back in the
  cookie: `session_id = <litestar session id>`, `user_id = "web:{session_id}"`
- ADK session state + event history live in **Oracle**, via
  `OracleAsyncADKStore` → `SQLSpecSessionService` (wired APP-scoped in `ioc.py`)

> This is the "ADK sessions are separate and bridged only at the chat controller
> boundary" rule made concrete — they touch in exactly one file.

---

## Slide 3 — Classify first, then decide who answers

**`ADKRunner.stream_request` orchestration (`services/adk.py`)**

1. Get-or-create the Oracle ADK session
2. **Response cache** lookup — key = `sha256(version:model:persona:normalized_query)`;
   a hit returns instantly. *Skipped entirely when the user shared browser
   coordinates* (privacy)
3. **Intent classification** — one `gemini-3.1-flash-lite` call, `temperature=0`,
   structured `text/x.enum` output → one of 5 labels (`classifier.py`)
4. **Route** on the label

| Intent | Path | Answer source |
|---|---|---|
| `PRODUCT_RAG` | deterministic | vector search → templated |
| `STORE_LOCATION` | deterministic | named SQL → templated |
| `PRODUCT_AVAILABILITY` | deterministic | inventory SQL → templated |
| `ORDER_STATUS` | deterministic | static "not supported yet" |
| `GENERAL_CONVERSATION` | **ADK agent** | LLM + tools |

> The classifier is the real router. The expensive agentic loop is reserved for
> open-ended chat.

---

## Slide 4 — The ADK workflow graph (the agent path)

**`make_workflow()` (`services/workflow.py`)** — only runs for `GENERAL_CONVERSATION`

```python
Workflow(
    name="coffee_workflow",
    edges=[
        ("START", intent, join),   # FunctionNode: re-classify intent
        ("START", coffee, join),   # LlmAgent: generate + call tools
        (join, merge),             # combine intent + answer
    ],
    max_concurrency=2,             # intent ∥ coffee run in parallel
)
```

- A **static fan-out graph**: intent classification and the LLM turn run
  *concurrently*, a `JoinNode` waits for both, a `merge` `FunctionNode` picks
  `{answer, intent}`
- Driven by ADK's `Runner.run_async(..., StreamingMode.SSE)` — partial events
  become `delta`s on the SSE stream

---

## Slide 5 — Tools are bound per-request

**`_make_tool_factories()` — the key DI pattern**

- The `LlmAgent` gets **7 tools defined as closures**, freshly built for *each
  request*: `search_products_by_vector`, `get_product_details`,
  `get_all_store_locations`, `find_stores_by_location`, `get_store_hours`,
  `find_nearest_stores`, `find_stores_with_product`
- Each closure captures two things from the current request:
  - `tools_service` → the **request-scoped Dishka services** (Oracle driver,
    Vertex AI, cache, metrics)
  - `metric_state` → a mutable dict that **records what happened** (SQL phases,
    products retrieved, embedding cache hits) for the telemetry panel
- The tool's **docstring is the LLM's tool description** — it tells Gemini when
  to call it
- `before_agent_callback=credential_guard_callback` short-circuits with a 503
  message if Vertex AI isn't configured

> Closure-bound tools give plain ADK functions request-scoped DB connections
> *and* a side-channel (`metric_state`) to surface SQL telemetry the LLM never
> sees.

---

## Slide 6 — Grounding: the answer is rebuilt from data

**Why the demo doesn't hallucinate menu items**

- Deterministic routes build the answer with **templated formatters over real
  Oracle rows** — the model never writes the product list, price, or description
- In the *agent* path, after the turn: `_effective_intent()` checks whether the
  model actually called the vector tool. If it did → relabel to `PRODUCT_RAG` and
  call `_ground_product_rag_turn()` to **regenerate the answer from the recorded
  search results**
- Net effect: *recommendations only ever name products that came back from the
  database*

```python
# _grounded_product_answer(): facts from Oracle, wording hard-coded
answer = f"{lead}, I'd start with {name}{_format_price(first.get('price'))}"
if description:
    answer += f": {description}"
```

> "Only these returned products may be recommended" is enforced in code, not
> trusted to the prompt.

---

## Slide 7 — State, caching, telemetry & privacy

**What persists, what's measured, what's protected**

- **Persisted (Oracle):** ADK session events + a trimmed `display_history` in
  session state; response cache; embedding cache; per-search metrics
  (`MetricsService`)
- **Measured per tool:** every tool emits `sql_phases` — named SQL key, bind
  values, row count, runtime, cache hit/miss — which flows into the `final` event
  and powers the live "what queries ran" demo panel
- **Privacy by construction:** browser coordinates are **request-scoped, never
  cached, never persisted**, and masked everywhere (`<REQUEST_COORDINATES>` in
  SQL phases, `_safe_location_context` in the payload). Sharing location also
  disables the response cache so a located answer can't leak to another user

> The telemetry panel is what makes the demo *show* Oracle vector search + ADK
> working, not just assert it.

---

## Appendix A — What's deterministic vs. LLM-written

| Stage | Engine | Free-form LLM text? |
|---|---|---|
| Intent classification | `gemini-3.1-flash-lite`, `temp=0`, enum output | No (picks a label) |
| `PRODUCT_RAG` answer | **Constrained LLM over retrieved candidates** (guarded; template fallback) | **Yes, bounded** |
| `STORE_LOCATION` answer | Python template over SQL rows | No |
| `PRODUCT_AVAILABILITY` answer | Python template over inventory rows | No |
| `ORDER_STATUS` answer | Static string | No |
| `GENERAL_CONVERSATION` answer | `LlmAgent` (chat model) | **Yes** |
| Agent calls vector tool mid-chat | answer re-grounded by the constrained composer | **Yes, bounded** |

**Takeaway:** for store/availability/order the LLM is a *router and retriever*,
not the *author*. For product recommendations the LLM *does* write the words, but
only ever names retrieved candidates — a post-generation guard rejects any
off-candidate mention and falls back to the deterministic template. Grounding
shifts from "model never writes the answer" to "model writes it, but can only
name real products, and we verify that."

---

## Appendix B — Off-menu / competitor handling (implemented)

**Example: user types "what about Folgers"**

The hard part is that `"I need something bold"` (valid preference) and
`"what about Folgers"` (off-menu brand) land in the **same** `similarity_score`
range — Folgers is also coffee. So a distance threshold can't separate them:
set it low and Folgers gets a confident rec; set it high and "something bold"
gets wrongly hedged. Telling them apart needs world knowledge + language
understanding — i.e. an **LLM**, not arithmetic. (Semantic *retrieval* vs.
entity *resolution*: vector search answers "find products *like* this," not
"do we carry this *named* thing.")

**The fix — constrained, guarded LLM composition (`_compose_grounded_answer`):**

1. Retrieve candidates via vector search (as before).
2. One Gemini call composes the reply, instructed to **only name candidate
   products**; for an off-menu brand, say "We don't carry Folgers, but…" and
   offer the closest candidate; for a preference, recommend directly.
3. Structured JSON (`answer`, `off_menu`, `off_menu_term`, `mentioned_products`).
4. **Guard:** every `mentioned_products` name must be a real candidate; on any
   off-candidate mention, malformed output, or API failure → fall back to the
   deterministic template. Credential failures → `AIServiceUnconfigured`.
5. Cached via the existing response cache, so each unique query pays the LLM
   cost once.

Result: `"something bold"` → confident recommendation; `"Folgers"` → "We don't
carry Folgers, but our House Blend ($3.75) is a classic medium roast." — without
ever naming a product that isn't on the menu.
