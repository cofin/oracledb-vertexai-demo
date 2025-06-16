# Migration Guide

This guide helps developers update their code to work with the recent architectural changes.

## 1. Updating Method Calls for Cache Information

### Problem
Many methods now return tuples instead of single values to include cache hit information.

### Solution

#### Vector Search
```python
# Old
results = await vector_search_service.similarity_search(query, k=5)

# New
results, cache_hit = await vector_search_service.similarity_search(query, k=5)
# Or if you don't need cache info
results, _ = await vector_search_service.similarity_search(query, k=5)
```

#### Chat Generation
```python
# Old
response = await vertex_ai.chat_with_history(query, context, history)

# New
response, cache_hit = await vertex_ai.chat_with_history(query, context, history)
```

#### Content Generation
```python
# Old
content = await vertex_ai.generate_content(prompt)

# New
content, cache_hit = await vertex_ai.generate_content(prompt)
```

#### Embedding Cache
```python
# Old
embedding = await cache.get_embedding(query, vertex_ai)

# New
embedding, cache_hit = await cache.get_embedding(query, vertex_ai)
```

#### Intent Routing
```python
# Old
intent, confidence, exemplar = await router.route_intent_single(query, conn)

# New
intent, confidence, exemplar, cache_hit = await router.route_intent_single(query, conn)
```

## 2. Exception Handling

### Problem
Nested try/except blocks make code harder to read and maintain.

### Solution
Use the new custom exceptions that are handled centrally:

```python
# Old
try:
    if not message:
        return HTMXTemplate(
            template_name="error.html",
            context={"error": "Message cannot be empty"}
        )
except Exception as e:
    return HTMXTemplate(
        template_name="error.html",
        context={"error": str(e)}
    )

# New
if not message:
    raise HTMXValidationException(detail="Message cannot be empty", field="message")
# Exception handler automatically returns HTMX response with proper events
```

### Available Custom Exceptions

```python
from app.server.exception_handlers import (
    HTMXValidationException,  # For validation errors
    HTMXAPIException,        # For API errors
    VectorDemoException      # For vector demo specific errors
)

# Usage examples
raise HTMXValidationException(detail="Invalid input", field="query")
raise HTMXAPIException(detail="Service unavailable", status_code=503, retry=True)
raise VectorDemoException(
    detail="Embedding generation failed",
    operation="embedding",
    error_type="vertex_ai_error"
)
```

## 3. HTMX Response Updates

### Problem
Manual header manipulation is error-prone and not type-safe.

### Solution
Use Litestar's native HTMX integration:

```python
# Old
response = HTMXTemplate(template_name="chat.html", context={...})
response.headers["HX-Trigger"] = json.dumps({
    "event:name": {"param": "value"}
})

# New
return HTMXTemplate(
    template_name="chat.html",
    context={...},
    trigger_event="event:name",
    params={"param": "value"},
    after="settle"  # or "receive" or "swap"
)
```

### Multiple Events
For multiple events, you need separate responses or use frontend JavaScript to chain events.

## 4. Type Annotations

### Problem
Type checkers fail due to changed return types.

### Solution
Update your type annotations:

```python
# Old
async def process_query(query: str) -> list[dict]:
    results = await vector_search.similarity_search(query)
    return results

# New
async def process_query(query: str) -> list[dict]:
    results, _ = await vector_search.similarity_search(query)
    return results

# Or if you need cache info
async def process_query(query: str) -> tuple[list[dict], bool]:
    return await vector_search.similarity_search(query)
```

## 5. Frontend Event Handling

### Problem
Need to handle new HTMX events on the frontend.

### Solution
Add event listeners for the new events:

```javascript
// Handle validation errors
document.body.addEventListener("validation:error", function(evt) {
    const { error, field } = evt.detail;
    // Show error message
    showFieldError(field, error);
});

// Handle API errors
document.body.addEventListener("api:error", function(evt) {
    const { type, retry } = evt.detail;
    if (retry) {
        // Show retry button
        showRetryOption();
    }
});

// Handle vector errors
document.body.addEventListener("vector:error", function(evt) {
    const { operation, error_type, retry } = evt.detail;
    // Handle based on operation type
    handleVectorError(operation, error_type, retry);
});
```

## 6. Removing Deprecated Methods

### Problem
Code uses deprecated `_with_cache_info` methods.

### Solution
Simply remove the suffix:

```python
# Old
embedding, cache_hit = await cache.get_embedding_with_cache_info(query, ai)
response, cache_hit = await ai.chat_with_history_cache_info(...)
results, cache_hit = await search.similarity_search_with_cache_info(query)

# New (same functionality, cleaner API)
embedding, cache_hit = await cache.get_embedding(query, ai)
response, cache_hit = await ai.chat_with_history(...)
results, cache_hit = await search.similarity_search(query)
```

## 7. Testing Updates

### Unit Tests
Update mocks to return tuples:

```python
# Old mock
mock_search.similarity_search.return_value = [{"id": 1, "name": "Coffee"}]

# New mock
mock_search.similarity_search.return_value = (
    [{"id": 1, "name": "Coffee"}],
    True  # cache_hit
)
```

### Integration Tests
Verify HTMX events are triggered:

```python
async def test_validation_error_triggers_event(client):
    response = await client.post("/", data={"message": ""})
    assert response.status_code == 400
    # Check that HTMXTemplate was used with correct event
    # This depends on your test setup
```

## Common Pitfalls

1. **Forgetting to unpack tuples**: Always check if a method now returns a tuple
2. **Not handling cache info**: Even if you don't use it, you must unpack it
3. **Using old exception patterns**: Centralized handlers make nested try/except unnecessary
4. **Manual HTMX headers**: Use the native integration instead

## Benefits After Migration

- **Cleaner code**: Less boilerplate, more readable
- **Better error handling**: Consistent error responses with proper HTMX events
- **Cache visibility**: Know when data comes from cache vs. fresh generation
- **Type safety**: Better IDE support and fewer runtime errors
- **Performance tracking**: Built-in metrics for all operations
