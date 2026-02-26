# Implementation Tasks: Agent UI Response Speed Optimization

**Requirement:** agent-ui-update
**Status:** Phase 1-3 COMPLETE, Ready for Testing
**Current Phase:** Comprehensive Testing
**Implementation Date:** 2025-10-24

**Requirement:** agent-ui-update
**Status:** Active
**Current Phase:** Ready for Implementation

## Phase 1: Optimistic UI + Query State Storage

### Backend

- [ ] **Add CacheService query state methods** (`app/services/_cache.py`)
  - [ ] Implement `set_query_state(query_id, state, ttl_minutes=5)`
  - [ ] Implement `get_query_state(query_id) -> dict | None`
  - [ ] Implement `delete_query_state(query_id)`
  - [ ] Add type hints
  - [ ] Handle TTL expiration

- [ ] **REPLACE handle_coffee_chat() method** (`app/server/controllers.py`)
  - [ ] Remove `if request.htmx:` conditional (clean cut)
  - [ ] Remove full-page response fallback
  - [ ] Add query state storage call
  - [ ] Always return `chat_optimistic.html` template
  - [ ] Keep validation and session logic
  - [ ] Add proper error handling

### Frontend

- [ ] **Create chat_optimistic.html template** (`app/server/templates/partials/`)
  - [ ] User message div (immediate display)
  - [ ] AI placeholder div with SSE attributes
    - [ ] `hx-ext="sse"`
    - [ ] `sse-connect="/chat/stream/{query_id}"`
    - [ ] `sse-swap="message"`
  - [ ] Typing indicator animation
  - [ ] SSE cleanup event handlers
  - [ ] CSP nonce support

- [ ] **Add CSS loading animations** (`app/server/static/css/cymbal-theme.css`)
  - [ ] Shimmer animation for loading state
  - [ ] Typing indicator bounce animation
  - [ ] Smooth transitions for state changes

- [ ] **Add SSE extension to template** (`app/server/templates/coffee_chat.html`)
  - [ ] Add SSE extension script tag (after HTMX core)
  - [ ] Ensure correct load order

### Cleanup

- [ ] **DELETE old template** (`app/server/templates/partials/chat_response.html`)

### Testing

- [ ] Unit test: `set_query_state()` method
- [ ] Unit test: `get_query_state()` method
- [ ] Unit test: `delete_query_state()` with TTL
- [ ] Unit test: Controller returns correct template
- [ ] Manual test: User message displays immediately
- [ ] Manual test: Loading indicator shows correctly
- [ ] Manual test: Network throttling (slow 3G)

## Phase 2: SSE Streaming Implementation

### Backend

- [ ] **Create ADKRunner.stream_request() method** (`app/services/_adk/runner.py`)
  - [ ] Accept query, user_id, session_id, persona parameters
  - [ ] Return `AsyncGenerator[dict[str, Any], None]`
  - [ ] Get persona-specific runner
  - [ ] Call `runner.run_async()`
  - [ ] Yield text chunks: `{"type": "text", "text": ...}`
  - [ ] Yield intent metadata: `{"type": "intent", "data": ...}`
  - [ ] Yield product results: `{"type": "products", "data": ...}`
  - [ ] Yield cache hits: `{"type": "cache_hit", ...}`
  - [ ] Add comprehensive logging

- [ ] **REPLACE stream_response() endpoint** (`app/server/controllers.py`)
  - [ ] Remove all fallback logic (clean cut)
  - [ ] Validate query_id format
  - [ ] Retrieve query state from cache
  - [ ] Check response cache (fast path)
    - [ ] If cached: yield complete response immediately
    - [ ] Send completion event
    - [ ] Cleanup query state
  - [ ] Stream from ADK (slow path)
    - [ ] Call `adk_runner.stream_request()`
    - [ ] Yield SSE events (chunk, metadata, complete)
    - [ ] Accumulate text for final response
    - [ ] Record metrics after streaming
    - [ ] Cache final aggregated response
    - [ ] Cleanup query state
  - [ ] Error handling: yield error event, log exception
  - [ ] Proper SSE format with event types

### Frontend

- [ ] **Create chat-streaming.js** (`app/server/static/js/`)
  - [ ] Listen for `htmx:sseMessage` events
  - [ ] Handle `chunk` event: append text to response
  - [ ] Handle `metadata` event: store for tooltips
  - [ ] Handle `complete` event: show help buttons, cleanup
  - [ ] Handle `error` event: display error message
  - [ ] Remove typing indicator on first chunk
  - [ ] Auto-scroll to new content

- [ ] **Update coffee_chat.html** (`app/server/templates/`)
  - [ ] Include chat-streaming.js script
  - [ ] Add proper script ordering

### Testing

- [ ] Unit test: `stream_request()` with mocked ADK events
- [ ] Unit test: SSE format validation
- [ ] Unit test: Error handling (query not found, timeout)
- [ ] Integration test: End-to-end streaming flow
- [ ] Integration test: Cached response fast path
- [ ] Integration test: Live ADK streaming
- [ ] Integration test: Connection drop and reconnect
- [ ] Integration test: Concurrent requests (5+)
- [ ] Manual test: Progressive text rendering
- [ ] Manual test: Cache hit scenario (instant display)
- [ ] Manual test: Slow network (throttling)
- [ ] Manual test: Browser compatibility (Chrome, Firefox, Safari)
- [ ] Manual test: Mobile devices (iOS Safari, Chrome Android)

## Phase 3: Help Bubbles & Polish

### Backend

- [ ] **Update get_query_log() for lazy loading** (`app/server/controllers.py`)
  - [ ] Support async loading with OOB swaps
  - [ ] Return partial HTML for tooltips

### Frontend

- [ ] **Update help button triggers**
  - [ ] Load tooltip content on-demand
  - [ ] Use `hx-trigger="click once"` for lazy loading
  - [ ] Show loading spinner while fetching

- [ ] **Add smooth transitions** (CSS)
  - [ ] Fade-in for help buttons after completion
  - [ ] Smooth scroll to new messages

### Testing

- [ ] Manual test: Tooltips load async
- [ ] Manual test: Tooltip positioning
- [ ] Manual test: Metrics update correctly

## Phase 4: Performance Optimization

### Optimization

- [ ] **Benchmark streaming overhead**
  - [ ] Measure latency with/without streaming
  - [ ] Profile SSE connection setup time
  - [ ] Identify bottlenecks

- [ ] **Ensure connection pooling**
  - [ ] Verify Redis connections reused
  - [ ] Monitor connection count under load

- [ ] **Cache optimization**
  - [ ] Monitor cache hit rate changes
  - [ ] Verify query state cleanup

### Load Testing

- [ ] **Stress testing**
  - [ ] Test 50+ concurrent SSE connections
  - [ ] Sustained load over 10 minutes
  - [ ] Monitor memory usage
  - [ ] Check for connection leaks
  - [ ] Verify graceful degradation

## Handoff Checklist

### To Testing Agent
- [ ] All Phase 1 & 2 tasks completed
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual testing validated
- [ ] Code follows specs/AGENTS.md standards
- [ ] Updated recovery.md with progress

### To Docs & Vision Agent
- [ ] All phases completed
- [ ] Testing comprehensive
- [ ] Documentation updated
- [ ] Ready for quality gate

## Progress Tracking

**Last Updated:** 2025-10-24
**Phase:** Not Started
**Completed Tasks:** 0 / 60+
**Blockers:** None
