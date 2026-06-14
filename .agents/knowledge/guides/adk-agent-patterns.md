# ADK Agent Patterns

Current guide for the Cymbal Coffee Google ADK 2.0 chat implementation.

## Runtime Shape

The chat implementation is a Litestar-hosted ADK 2.0 workflow:

```text
CoffeeChatController
  -> ADKRunner.stream_request()
  -> SQLSpecSessionService
  -> response cache lookup
  -> FlashLiteIntentClassifier
  -> Product RAG direct path OR Runner(node=coffee_workflow, ...)
  -> final event, with SSE deltas only for model-streamed non-RAG turns
```

The ADK workflow graph is still available for model-streamed conversational
turns:

```text
START -> intent FunctionNode -> JoinNode
START -> LlmAgent coffee_turn -> JoinNode
JoinNode -> classify_and_respond FunctionNode
```

`max_concurrency=2` lets the Flash-Lite classifier and coffee response run in
parallel inside the workflow path.

For product/menu/RAG turns, the runner classifies first and bypasses speculative
model streaming. It searches the menu through `AgentToolsService`, formats the
answer from returned Cymbal Coffee rows, and yields a single final event. This
prevents the browser from showing an ungrounded model delta and then replacing it
with a grounded final answer.

## Runner Boundary

`ADKRunner` is an APP-scoped Dishka dependency. It owns:

- `SQLSpecSessionService`
- `FlashLiteIntentClassifier`
- `PersonaManager`

It does not own the request-scoped database driver. Each request passes an
`AgentToolsService` into `stream_request()` or `process_request()`. That service
holds the current SQLSpec driver and the product/cache/metrics/store services.

This keeps ADK sessions durable while keeping domain database work aligned to
Litestar request scope.

## Session Identity

The browser session and ADK session are separate stores:

- Litestar server-side session table: `app_session`
- ADK session/event tables: `adk_sessions`, `adk_events`
- Optional ADK memory table: `adk_memory_entries`

`app.domain.chat.session.adk_session_identity()` bridges them by storing:

- `adk_session_id`
- `adk_user_id`

inside the Litestar session, then passing those identifiers to ADK.

Do not treat Litestar's session object as the ADK session. It is only the web
identity anchor.

`GET /` uses that same bridge to hydrate chat history. The page asks
`ADKRunner.get_history()` for display messages. The runner first reads
`session.state["display_history"]`, then falls back to persisted ADK events when
that display history is missing. If neither exists, the template shows the
static welcome message.

The sidebar `Clear chat` button calls `POST /api/chat/session/clear`. That
deletes the current ADK session/events and removes the Litestar bridge keys. It
does not clear products, metrics, response cache, or embedding cache.

## SQLSpec ADK Store

`src/app/ioc.py` wires the SQLSpec ADK extension:

```python
@provide(scope=Scope.APP)
def provide_adk_store(self, config: OracleAsyncConfig) -> OracleAsyncADKStore:
    return OracleAsyncADKStore(config=config)

@provide(scope=Scope.APP)
def provide_session_service(self, store: OracleAsyncADKStore) -> SQLSpecSessionService:
    return SQLSpecSessionService(store)
```

The Oracle-specific table names and INMEMORY flags live in `DatabaseSettings`:

```python
"adk": {
    "session_table": "adk_sessions",
    "events_table": "adk_events",
    "memory_table": "adk_memory_entries",
    "enable_memory": settings.db.ADK_ENABLE_MEMORY,
    "include_memory_migration": settings.db.ADK_ENABLE_MEMORY,
    "in_memory": settings.db.ADK_IN_MEMORY,
}
```

Use SQLSpec's ADK store for session persistence instead of an in-memory ADK
session service in application code.

## Closure-Bound Tools

The LLM node receives plain async Python callables created per request:

```python
async def search_products_by_vector(
    query: str,
    limit: int = 5,
    similarity_threshold: float = 0.7,
) -> dict[str, Any]:
    result = await tools_service.search_products_by_vector(
        query, limit, similarity_threshold
    )
    ...
    return result
```

The callable docstrings are part of the model contract. Keep them explicit about
when the model should call each tool.

For Cymbal Coffee, `search_products_by_vector` must mention menu/catalog/flavor,
recommendation, availability, substitution, and idiomatic preference requests.
That text is what makes "wake me up", "what is good today", and "do you have
decaf" eligible for product RAG.

For `PRODUCT_RAG` turns, the final answer must be grounded to the products
returned by Cymbal Coffee tools. If the LLM node skips tool use or emits an
internal tool-schema message, run the product search fallback and format the
final answer from returned menu rows rather than trusting the speculative model
text.

The current preferred path is classifier-first:

```text
request text
  -> response cache lookup
  -> FlashLiteIntentClassifier
  -> if PRODUCT_RAG:
       search_products_by_vector(query, 3, 0.5)
       format final answer from returned products only
       persist intent + display_history in ADK session state
       cache response
       yield final event only
  -> otherwise:
       run ADK workflow with SSE streaming
       yield model deltas
       yield final event
```

This keeps menu answers deterministic and menu-grounded while preserving model
streaming for genuine conversation.

## Intent Classification

Intent classification is a separate Gemini Flash-Lite call using
`response_mime_type="text/x.enum"`:

```python
response = await client.aio.models.generate_content(
    model="gemini-2.5-flash-lite",
    contents=phrase,
    config=types.GenerateContentConfig(
        response_mime_type="text/x.enum",
        response_schema={"type": "STRING", "enum": INTENT_VALUES},
        system_instruction=_SYSTEM_INSTRUCTION,
        temperature=0,
    ),
)
```

Labels:

- `PRODUCT_RAG`
- `GENERAL_CONVERSATION`
- `STORE_LOCATION`
- `ORDER_STATUS`

The classifier instructions intentionally include concrete menu and idiom
examples. Keep those examples when changing labels; removing them makes the
classifier under-route obvious menu questions and idiomatic requests.

## Context-Aware Availability

To support conversational continuity, product availability queries (`PRODUCT_AVAILABILITY`) are context-aware:

1.  **Session-State Tracking**: When answering a `PRODUCT_RAG` query (e.g. recommending items), the runner extracts the names of the recommended products and stores them in the ADK session state under the `last_products` key.
2.  **Pronoun Resolution**: In `_product_availability_event`, if the cleaned query does not contain a specific product name (e.g. "Is that in stock?"), the system retrieves the `last_products` from the session state and uses the primary recommended product as the target query.
3.  **Vector Fallback Resolution**: When searching stock via `find_stores_with_product`, the system first attempts an exact match on name/SKU/ID. If the lookup returns no results, it falls back to embedding the product query and running a vector similarity search (threshold 0.6) to resolve the query to the closest actual menu product (e.g. matching "Gemini" to "Gemini Rush").

This combination allows the user to seamlessly ask follow-up questions about recommended items without repeating their names, while remaining tolerant to minor name variations.

## Streaming

The current browser path streams:

- `pages/chat.html.j2` posts to `/api/chat/stream`.
- `CoffeeChatController.stream_chat_message()` returns `ServerSentEvent`.
- `ADKRunner.stream_request()` runs ADK with `RunConfig(streaming_mode=StreamingMode.SSE)`.
- `src/resources/main.js` parses SSE blocks from `fetch()` and updates the
  pending message.

`process_request()` exists for JSON/non-streaming callers and drains
`stream_request()` until the final event.

When debugging slow chat, verify the browser is using `/api/chat/stream`, not
`/api/chat`.

Do not emit Product RAG deltas before grounding. For Product RAG, the only
browser-visible response should be the final grounded payload. Non-RAG turns may
stream partial model text.

## Credential Guard

`credential_guard_callback()` short-circuits model execution when local AI config
is missing. `ADKRunner.stream_request()` also preflights placeholder Vertex
project IDs before ADK starts.

Expected local misconfiguration should return a clean 503 through the controller,
not a stack trace from ADK internals.

## Result Contract

Every final chat result must include:

- `answer`
- `session_id`
- `response_time_ms`
- `intent_detected`
- `search_metrics`
- `from_cache`
- `embedding_cache_hit`
- `sql_phases`

Keep this shape stable for HTMX partials, JSON clients, and tests.

## Cache And Metrics

Chat response cache keys include model, persona, and normalized query text.
Embedding cache state is reported separately from response cache state.

When product search runs, the tool records:

- `vector_query`
- `embedding_ms`
- `oracle_ms`
- `tool_ms`
- `results_count`
- `products_found`
- `embedding_cache_hit`

The UI reads these fields for message-level telemetry badges and for "did RAG
happen?" debugging. Preserve the vector query and phase timings when changing
ADK tools, because the demo is meant to make intent routing, Oracle vector
lookup, embedding cache hits, and response cache hits visible in the chat
message itself.

Search metric inserts must use the app serializer boundary:
`schema_dump(metrics, wire_format=False)`. Database writes need Python field
names such as `result_count`; wire-format/camelized names such as `resultCount`
produce invalid Oracle identifiers.

## Debugging Checklist

Menu question not using RAG:
Check the classifier system instruction and the `search_products_by_vector`
docstring first. Both must include menu, catalog, recommendation, and idiomatic
preference examples.

`Workflow coffee_workflow: cancelling leftover tasks`:
Look for exceptions or early returns while consuming ADK events. The expected
path should drain the async event stream or return only after the final event.

`Exception caught after response started` on `/api/chat/stream`:
An exception escaped the SSE generator after headers were sent. Keep exception
handling inside the generator, log the real exception there, and yield a
sanitized `error` event for the browser.

`can't compare offset-naive and offset-aware datetimes` during cache lookup:
Do not compare cache expiry datetimes in Python during the read path. Filter
fresh cache rows in SQL with `CURRENT_TIMESTAMP`, return the typed
`ResponseCache` via `schema_type`, and keep expired-row deletion behind the
explicit cache cleanup operation.

Session state missing:
Confirm `app.domain.chat.session.adk_session_identity()` stores IDs in the
Litestar session and that `SQLSpecSessionService` is backed by
`OracleAsyncADKStore`, not an in-memory ADK session service.

No streaming in the UI:
Confirm the form action is `/api/chat/stream`, the request accepts
`text/event-stream`, and `src/resources/main.js` is loaded by Vite.
