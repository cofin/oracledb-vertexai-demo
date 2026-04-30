# Detailed Technical Plan: Agent UI Response Speed Optimization

**Research Date:** 2025-10-24
**Agent:** Planner
**Technologies Researched:** HTMX, Litestar, Google ADK, SSE

## Current Implementation Analysis

### Form Submission Pattern
- **Template:** `app/server/templates/coffee_chat.html`
- **Method:** Standard HTMX POST to `/` with `hx-swap="beforeend"` on `#chat-container`
- **Controller:** `app/server/controllers.py:93-217` - `handle_coffee_chat()` method
- **Pattern:** Synchronous blocking - waits for complete ADK processing

### ADK Processing
- **File:** `app/services/_adk/runner.py:77-173`
- **Method:** `process_request()`
- **Pattern:** Uses `runner.run_async()` with event processing
- **Key Insight:** ADK ALREADY streams internally via AsyncGenerator
- **Response cache:** 5-minute TTL, checked before agent processing
- **Return:** Complete response dict with all metadata

### Response Template
- **File:** `app/server/templates/partials/chat_response.html`
- **Returns:** Full user + AI message pair in single response
- **Display:** Swapped into DOM after complete processing

## Technology Research

### HTMX Capabilities (v1.9.10 in use)

#### Out-of-Band (OOB) Swaps
- **Feature:** `hx-swap-oob="true"` allows multiple DOM updates from single response
- **Use Case:** Display user message immediately, AI response separately
- **Pattern:**
  ```html
  <div id="user-msg">...</div>
  <div id="ai-response" hx-swap-oob="beforeend:#chat-container">...</div>
  ```

#### Server-Sent Events (SSE)
- **Extension:** `sse-ext` (must add to project)
- **Attributes:**
  - `hx-ext="sse"` - Enable SSE on element
  - `sse-connect="/stream"` - Connect to SSE endpoint
  - `sse-swap="eventName"` - Swap on specific event
- **Events:** `chunk`, `metadata`, `complete`, `error`
- **Auto-reconnect:** Built-in HTMX feature

#### Event Triggers
- **Pattern:** `hx-trigger="sse:event_name"`
- **Use Case:** Reactive updates based on SSE events

### Litestar Streaming (Already available)

#### Stream Response
```python
from litestar.response import Stream
from collections.abc import AsyncGenerator

@get("/stream")
async def stream_endpoint() -> Stream:
    async def generate() -> AsyncGenerator[bytes, None]:
        yield b"chunk1"
        yield b"chunk2"

    return Stream(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )
```

#### Server-Sent Event Format
```python
from litestar.response import ServerSentEventMessage

async def generate() -> AsyncGenerator[ServerSentEventMessage, None]:
    yield ServerSentEventMessage(
        data={"text": "Hello"},
        event_type="chunk",
        id="1",
        retry=5000
    )
```

#### HTMXTemplate Integration
- **Feature:** `trigger_event`, `params`, `after="settle"`
- **Use Case:** Coordinate client-side events after response

### Google ADK Streaming (2025 capabilities)

#### Native Async Streaming
- **Method:** `runner.run_async()` returns `AsyncGenerator` of events
- **Pattern:** Already yields events progressively during processing
- **Event types:** Text parts, function responses, metadata
- **Key Insight:** We're currently buffering all events - we can stream them directly

#### Event Structure
```python
async for event in runner.run_async(...):
    # event.content.parts - text parts
    # event.get_function_responses() - tool results
    # event.is_final_response() - completion indicator
```

#### Tool Streaming
- **Feature:** AsyncGenerator return types for streaming tools
- **Use Case:** Progressive product search results

### Research Summary: Key Insights

1. **ADK already streams internally** - we're just not exposing it to the UI
2. **HTMX SSE extension** - perfect match for real-time AI response streaming
3. **OOB swaps** - can immediately show user message + loading state
4. **Existing streaming endpoint** - `controllers.py:219-263` exists but unused
5. **Litestar Stream** - full SSE support built-in
6. **No polling needed** - SSE is standard, reliable, auto-reconnects

## Architectural Decisions

### Decision 1: SSE vs WebSocket

**Analysis:**
- **SSE:** Unidirectional (server → client), HTTP-based, simpler, auto-reconnect
- **WebSocket:** Bidirectional, more complex, overkill for our use case

**Decision:** Use SSE with HTMX extension
- Perfect for our unidirectional streaming needs
- Native HTMX support
- Simpler than WebSocket
- Works over HTTP (no firewall issues)

### Decision 2: Query State Storage

**Problem:** SSE endpoint needs query context after initial POST

**Options:**
1. Redis/Memory Cache (using existing CacheService)
2. Server Session Storage
3. URL Parameters (security risk)

**Decision:** Use existing CacheService
- Already have Redis infrastructure
- Fast, async-friendly
- TTL-based cleanup (5 min)
- Secure (not exposed in URLs)

**Implementation:**
```python
# Store query state
await cache_service.set_query_state(
    query_id=query_id,
    state={
        "query": clean_message,
        "session_id": session_id,
        "persona": validated_persona,
        "user_id": "web_user",
    },
    ttl_minutes=5
)

# Retrieve in SSE endpoint
query_state = await cache_service.get_query_state(query_id)
```

### Decision 3: Streaming Strategy

**Dual Path Approach:**

**Fast Path (Cached Response):**
```
Check response cache → If hit → Yield complete response immediately → Done
```

**Slow Path (Live Streaming):**
```
Call ADKRunner.stream_request() →
    Yield text chunks progressively →
    Yield metadata →
    Yield completion →
    Record metrics →
    Cache final response
```

**Decision:** Unified streaming endpoint handles both paths
- Simplifies client code
- Preserves cache performance
- Consistent SSE format

### Decision 4: No Fallback Mechanisms (Clean Cut)

**Decision:** Complete replacement, no fallback code

**Removed:**
- No `if request.htmx:` conditionals
- No full-page response fallback
- No polling fallback
- No feature flags
- No gradual rollout

**Rationale:**
- Simpler implementation
- Single code path to maintain
- Modern browsers all support SSE
- Demo app can require modern browser
- Easier to test and debug

## Detailed Implementation Specifications

### Phase 1: Optimistic UI

#### Backend: CacheService Methods

```python
# File: app/services/_cache.py

async def set_query_state(
    self,
    query_id: str,
    state: dict[str, Any],
    ttl_minutes: int = 5,
) -> None:
    """Store query state for streaming endpoint."""
    cache_key = f"query:{query_id}"
    await self._set(cache_key, state, ttl_minutes)

async def get_query_state(self, query_id: str) -> dict[str, Any] | None:
    """Retrieve query state for streaming."""
    cache_key = f"query:{query_id}"
    return await self._get(cache_key)

async def delete_query_state(self, query_id: str) -> None:
    """Clean up query state after streaming completes."""
    cache_key = f"query:{query_id}"
    await self._delete(cache_key)
```

#### Backend: Controller Replacement

```python
# File: app/server/controllers.py

@post(path="/", name="coffee_chat.get")
@inject
async def handle_coffee_chat(
    self,
    data: Annotated[schemas.CoffeeChatMessage, Body(...)],
    adk_runner: Inject[ADKRunner],
    cache_service: Inject[CacheService],
    metrics_service: Inject[MetricsService],
    request: HTMXRequest,
) -> HTMXTemplate:
    """Handle chat submission with optimistic UI pattern."""

    csp_nonce = self.generate_csp_nonce()
    clean_message = self.validate_message(data.message)
    validated_persona = self.validate_persona(data.persona)
    query_id = str(uuid.uuid4())

    # Get/create session
    session_id = request.session.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session["session_id"] = session_id

    # Store query state for streaming endpoint
    query_state = {
        "query": clean_message,
        "session_id": session_id,
        "persona": validated_persona,
        "user_id": "web_user",
        "timestamp": time.time(),
    }
    await cache_service.set_query_state(
        query_id=query_id,
        state=query_state,
        ttl_minutes=5
    )

    # ALWAYS return optimistic UI (no fallback)
    return HTMXTemplate(
        template_name="partials/chat_optimistic.html",
        context={
            "user_message": clean_message,
            "query_id": query_id,
            "persona": validated_persona,
            "csp_nonce": csp_nonce,
        },
        trigger_event="chat:user-message-added",
        params={"query_id": query_id},
        after="settle",
    )
```

#### Frontend: Optimistic Template

```html
<!-- File: app/server/templates/partials/chat_optimistic.html -->

<!-- User message - displays immediately -->
<div class="message user" data-message-id="{{ query_id }}" id="user-msg-{{ query_id }}">
    <strong>You:</strong> {{ user_message }}
</div>

<!-- AI response placeholder with SSE connection -->
<div class="message assistant loading"
     id="ai-response-{{ query_id }}"
     data-message-id="{{ query_id }}"
     hx-ext="sse"
     sse-connect="/chat/stream/{{ query_id }}"
     sse-swap="message">
    <strong>AI Coffee Expert:</strong>
    <span class="ai-response-content">
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
    </span>
    <span class="help-triggers" style="display: none; gap: 4px; margin-left: 8px;">
        <!-- Help buttons populated after completion -->
    </span>
</div>

<!-- SSE event handlers -->
<script nonce="{{ csp_nonce }}">
document.addEventListener('htmx:sseClose', function(evt) {
    if (evt.detail.elt.id === 'ai-response-{{ query_id }}') {
        // Cleanup after stream closes
        evt.detail.elt.removeAttribute('hx-ext');
        evt.detail.elt.removeAttribute('sse-connect');
        evt.detail.elt.removeAttribute('sse-swap');
        evt.detail.elt.classList.remove('loading');

        // Reload metrics
        if (typeof loadMetrics === 'function') {
            loadMetrics();
        }
    }
});
</script>
```

### Phase 2: SSE Streaming

#### Backend: ADKRunner Streaming Method

```python
# File: app/services/_adk/runner.py

async def stream_request(
    self,
    query: str,
    user_id: str = "default",
    session_id: str | None = None,
    persona: str = "enthusiast",
    cache_service: CacheService | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Stream ADK events progressively for real-time UI updates.

    Yields:
        Dictionary with 'type' and 'data' keys:
        - type: 'text' - Text chunk
        - type: 'intent' - Intent classification result
        - type: 'products' - Product search results
        - type: 'cache_hit' - Cache hit indicator
    """
    logger.debug("Streaming request via ADKRunner", query=query, persona=persona)

    session = await self._ensure_session(user_id, session_id)
    content = types.Content(role="user", parts=[types.Part(text=query)])

    # Get persona-specific runner
    runner = self._get_runner_for_persona(persona)

    # Start ADK async generator
    events = runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=content,
    )

    # Process and stream events
    async for event in events:
        # Extract and stream text progressively
        text_parts = self._extract_text_from_event(event)
        if text_parts and not self._should_filter_text("".join(text_parts)):
            for text in text_parts:
                yield {
                    "type": "text",
                    "text": text,
                    "timestamp": time.time()
                }

        # Extract function responses for metadata
        function_responses = event.get_function_responses() if hasattr(event, "get_function_responses") else []
        for func_response in function_responses:
            if func_response.name == "classify_intent":
                intent_result = func_response.response or {}
                yield {
                    "type": "intent",
                    "data": {
                        "intent": intent_result.get("intent"),
                        "confidence": intent_result.get("confidence"),
                        "timing_ms": intent_result.get("timing_ms"),
                    },
                    "timestamp": time.time(),
                }
                if intent_result.get("embedding_cache_hit"):
                    yield {"type": "cache_hit", "cache_type": "embedding"}

            elif func_response.name == "search_products_by_vector":
                search_result = func_response.response or {}
                timing = search_result.get("timing", {})
                yield {
                    "type": "products",
                    "data": {
                        "products": search_result.get("products", []),
                        "embedding_ms": timing.get("embedding_ms", 0),
                        "search_ms": timing.get("search_ms", 0),
                    },
                    "timestamp": time.time(),
                }
                if search_result.get("embedding_cache_hit"):
                    yield {"type": "cache_hit", "cache_type": "embedding"}
```

#### Backend: SSE Endpoint

```python
# File: app/server/controllers.py

@get(path="/chat/stream/{query_id:str}", name="chat.stream")
@inject
async def stream_response(
    self,
    query_id: str,
    adk_runner: Inject[ADKRunner],
    cache_service: Inject[CacheService],
    metrics_service: Inject[MetricsService],
) -> Stream:
    """Stream AI response using Server-Sent Events."""

    # Validate query_id
    if not re.match(r"^[a-fA-F0-9\-]+$", query_id):
        async def error_generate() -> AsyncGenerator[str, None]:
            yield "event: error\ndata: {\"error\": \"Invalid query ID\"}\n\n"
        return Stream(error_generate(), media_type="text/event-stream")

    async def generate() -> AsyncGenerator[str, None]:
        try:
            # 1. Retrieve query state
            query_state = await cache_service.get_query_state(query_id)
            if not query_state:
                yield "event: error\ndata: {\"error\": \"Query not found or expired\"}\n\n"
                return

            query = query_state["query"]
            session_id = query_state["session_id"]
            persona = query_state["persona"]
            user_id = query_state["user_id"]

            # 2. Check response cache (fast path)
            cache_key = f"{query}|{persona}"
            cached = await cache_service.get_cached_response(cache_key=cache_key)

            if cached:
                logger.info("Streaming cached response", query_id=query_id)
                # Render and send complete response
                response_html = self._render_ai_message(cached.response_data)
                yield f"event: message\ndata: {json.dumps({'html': response_html})}\n\n"
                yield f"event: complete\ndata: {json.dumps({'done': True, 'from_cache': True})}\n\n"
                await cache_service.delete_query_state(query_id)
                return

            # 3. Stream from ADK (slow path)
            logger.info("Streaming from ADK", query_id=query_id)

            start_time = time.time()
            accumulated_text = []
            intent_details = {}
            search_details = {}
            products_found = []
            embedding_cache_hit = False

            # Set context var
            from app.lib.di import query_id_var
            token = query_id_var.set(query_id)

            try:
                events = await adk_runner.stream_request(
                    query=query,
                    user_id=user_id,
                    session_id=session_id,
                    persona=persona,
                    cache_service=cache_service,
                )

                # Stream events to client
                async for chunk in events:
                    chunk_type = chunk.get("type")

                    if chunk_type == "text":
                        text = chunk.get("text", "")
                        accumulated_text.append(text)
                        yield f"event: chunk\ndata: {json.dumps({'text': text})}\n\n"

                    elif chunk_type == "intent":
                        intent_details = chunk.get("data", {})
                        yield f"event: metadata\ndata: {json.dumps({'type': 'intent', 'data': intent_details})}\n\n"

                    elif chunk_type == "products":
                        search_details = chunk.get("data", {})
                        products_found = search_details.get("products", [])
                        yield f"event: metadata\ndata: {json.dumps({'type': 'products', 'data': search_details})}\n\n"

                    elif chunk_type == "cache_hit":
                        embedding_cache_hit = True

                # 4. Send completion event
                total_time_ms = round((time.time() - start_time) * 1000, 2)
                completion_data = {
                    "done": True,
                    "query_id": query_id,
                    "response_time_ms": total_time_ms,
                    "embedding_cache_hit": embedding_cache_hit,
                }
                yield f"event: complete\ndata: {json.dumps(completion_data)}\n\n"

                # 5. Record metrics
                await metrics_service.record_search(...)

                # 6. Cache final response
                await cache_service.set_cached_response(
                    cache_key=cache_key,
                    response_data={
                        "answer": " ".join(accumulated_text),
                        "response_time_ms": total_time_ms,
                        "intent_details": intent_details,
                        "search_details": search_details,
                        "products_found": products_found,
                        "embedding_cache_hit": embedding_cache_hit,
                    },
                    ttl_minutes=5,
                )

            finally:
                query_id_var.reset(token)
                await cache_service.delete_query_state(query_id)

        except Exception as e:
            logger.exception("Stream error", query_id=query_id, error=str(e))
            yield f"event: error\ndata: {json.dumps({'error': 'Service error'})}\n\n"

    return Stream(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Content-Type-Options": "nosniff",
        },
    )
```

#### Frontend: SSE Handling

```javascript
// File: app/server/static/js/chat-streaming.js

// Handle SSE chunk events - append text progressively
document.body.addEventListener('htmx:sseMessage', function(evt) {
    const msgType = evt.detail.type;

    if (msgType === 'chunk') {
        const data = JSON.parse(evt.detail.data);
        const responseEl = evt.target.querySelector('.ai-response-content');
        if (responseEl) {
            // Remove typing indicator on first chunk
            const typingIndicator = responseEl.querySelector('.typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
            // Append text
            responseEl.textContent += data.text;
        }
    }

    else if (msgType === 'complete') {
        // Show help buttons
        const helpTriggers = evt.target.querySelector('.help-triggers');
        if (helpTriggers) {
            helpTriggers.style.display = 'inline-flex';
        }

        // Scroll to bottom
        const container = document.getElementById('chat-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }
});

// Handle SSE errors - display error message
document.body.addEventListener('htmx:sseError', function(evt) {
    const container = document.getElementById('chat-container');
    if (container) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message error';
        errorDiv.innerHTML = '<strong>Error:</strong> Unable to connect. Please refresh the page.';
        container.appendChild(errorDiv);
    }
});
```

## Performance Considerations

### Bottlenecks Identified
1. **ADK Processing:** ~agent_processing_ms (measured in logs)
2. **Embedding Generation:** ~embedding_ms (0 when cache hit)
3. **Vector Search:** ~search_ms (0 when no products)
4. **Template Rendering:** Final blocking step (eliminated with streaming)

### Optimizations Applied
1. **Parallel Operations:** User message display + ADK processing
2. **Progressive Enhancement:** Show text as it's generated
3. **Cache-First:** Response cache hit = instant display
4. **Lazy Loading:** Metrics/tooltips load after main response

### Expected Performance Improvements
- **Time to First Byte (User Message):** <100ms (was ~agent_processing_ms)
- **Time to First AI Token:** <500ms (start streaming)
- **Perceived Latency:** 50%+ reduction
- **Streaming Overhead:** <50ms

## Testing Strategy

### Unit Tests
- CacheService query state CRUD operations
- ADKRunner.stream_request() with mocked ADK events
- SSE format validation
- Error handling (query not found, timeout)

### Integration Tests
- End-to-end streaming flow
- Cached response fast path
- Live ADK streaming slow path
- Connection drop and reconnect
- Concurrent requests (5+)

### Manual Tests
- Progressive text rendering
- Cache hit instant display
- Network throttling (slow 3G)
- Browser compatibility (Chrome, Firefox, Safari)
- Mobile devices (iOS Safari, Chrome Android)

### Load Tests
- 50+ concurrent SSE connections
- Sustained load (10 minutes)
- Memory leak detection
- Connection leak detection

## Rollout Strategy

### Development Process
1. Implementation (Phase 1-4)
2. Comprehensive testing
3. Staging deployment
4. **Direct production deployment**

### Monitoring
- SSE connection success rate
- Streaming duration (p50, p95, p99)
- Cache hit rates (response, embedding)
- Error rates
- Memory usage

### Rollback Plan
- Revert commit
- Redeploy previous version
- No configuration changes

## Conclusion

This plan provides a complete, research-grounded approach to transforming the agent UI into a modern streaming architecture. The clean cut approach eliminates fallback complexity while leveraging existing ADK streaming capabilities and HTMX's native SSE support.

**Key Takeaway:** ADK already streams events internally - we're simply exposing that stream to the UI through SSE, providing instant user feedback and real-time progressive responses.
