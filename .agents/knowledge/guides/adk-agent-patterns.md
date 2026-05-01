# ADK Agent Patterns

Current guide for the Cymbal Coffee Google ADK 2.0 chat implementation.

## Runtime Shape

The chat implementation is a Litestar-hosted ADK 2.0 workflow:

```text
CoffeeChatController
  -> ADKRunner.stream_request()
  -> SQLSpecSessionService
  -> Runner(node=coffee_workflow, ...)
  -> Workflow graph
  -> SSE delta and final events
```

The graph is deterministic at the orchestration layer and adaptive inside the
LLM node:

```text
START -> intent FunctionNode -> JoinNode
START -> LlmAgent coffee_turn -> JoinNode
JoinNode -> classify_and_respond FunctionNode
```

`max_concurrency=2` lets the Flash-Lite classifier and coffee response run in
parallel.

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

`CoffeeChatController._adk_session_identity()` bridges them by storing:

- `adk_session_id`
- `adk_user_id`

inside the Litestar session, then passing those identifiers to ADK.

Do not treat Litestar's session object as the ADK session. It is only the web
identity anchor.

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

## Debugging Checklist

Menu question not using RAG:
Check the classifier system instruction and the `search_products_by_vector`
docstring first. Both must include menu, catalog, recommendation, and idiomatic
preference examples.

`Workflow coffee_workflow: cancelling leftover tasks`:
Look for exceptions or early returns while consuming ADK events. The expected
path should drain the async event stream or return only after the final event.

Session state missing:
Confirm `_adk_session_identity()` stores IDs in the Litestar session and that
`SQLSpecSessionService` is backed by `OracleAsyncADKStore`, not an in-memory
ADK session service.

No streaming in the UI:
Confirm the form action is `/api/chat/stream`, the request accepts
`text/event-stream`, and `src/resources/main.js` is loaded by Vite.
