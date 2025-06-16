# Architecture Updates Documentation

This document describes the significant architectural improvements made to the Oracle + Vertex AI demo application.

## 1. HTMX Native Integration

### Overview
Migrated all endpoints to use Litestar's native HTMX plugins instead of manual header manipulation.

### Key Changes
- Replaced manual `HX-Trigger` headers with native `trigger_event` parameters
- Added comprehensive event system for UI feedback
- Implemented automatic polling control with `HXStopPolling`

### Benefits
- Type-safe HTMX responses
- Cleaner, more maintainable code
- Better IDE support and autocomplete

## 2. Centralized Exception Handling

### Overview
Implemented a centralized exception handling system that replaces nested try/except blocks throughout the codebase.

### Implementation
Created `app/server/exception_handlers.py` with:

#### Custom Exceptions
```python
class HTMXValidationException(ValidationException):
    """Validation exception that triggers HTMX events."""

class HTMXAPIException(HTTPException):
    """API exception that triggers HTMX events."""

class VectorDemoException(HTTPException):
    """Exception specific to vector demo operations."""
```

#### Exception Handlers
- `handle_validation_exception`: Returns HTMX templates with validation error events
- `handle_google_api_exception`: Handles Google API errors with retry suggestions
- `handle_htmx_api_exception`: Handles custom API exceptions
- `handle_vector_demo_exception`: Specialized handler for vector demo errors
- `handle_value_error`: Handles ValueError exceptions from Vertex AI
- `handle_generic_exception`: Catches any unexpected exceptions

### Benefits
- Consistent error handling across the application
- Automatic HTMX event triggering on errors
- Better user experience with contextual error messages
- Reduced code duplication

## 3. Unified Cache Information API

### Overview
Removed duplicate methods with `_with_cache_info` suffixes and updated all methods to return cache information directly.

### Changes Made

#### Before
```python
# Two separate methods for each operation
async def similarity_search(query: str) -> list[dict]:
    result, _ = await self.similarity_search_with_cache_info(query)
    return result

async def similarity_search_with_cache_info(query: str) -> tuple[list[dict], bool]:
    # Implementation
```

#### After
```python
# Single method that returns both data and cache info
async def similarity_search(query: str) -> tuple[list[dict], bool]:
    # Implementation returns (results, cache_hit)
```

### Updated Methods
1. **OracleVectorSearchService.similarity_search**
   - Now returns: `tuple[list[dict], bool]`
   - Second element indicates embedding cache hit

2. **VertexAIService.chat_with_history**
   - Now returns: `tuple[str, bool]`
   - Second element indicates response cache hit

3. **VertexAIService.generate_content**
   - Now returns: `tuple[str, bool]`
   - Second element indicates response cache hit

4. **EmbeddingCache.get_embedding**
   - Now returns: `tuple[list[float], bool]`
   - Second element indicates embedding cache hit

5. **IntentRouter.route_intent**
   - Now returns: `tuple[list[tuple[str, float, str]], bool]`
   - Second element indicates embedding cache hit

6. **IntentRouter.route_intent_single**
   - Now returns: `tuple[str, float, str, bool]`
   - Fourth element indicates embedding cache hit

### Benefits
- Cleaner API with no duplicate methods
- Consistent pattern across all services
- Better cache hit tracking throughout the system
- Simplified maintenance

## 4. Enhanced Cache Hit Tracking

### Overview
Improved tracking of embedding cache hits across all layers of the application.

### Implementation Details

#### Intent Detection Cache Tracking
```python
# Intent router now tracks embedding cache hits
intent, confidence, exemplar, intent_embedding_cache_hit = await self.intent_router.route_intent_single(query, connection)
```

#### Product Search Cache Tracking
```python
# Vector search tracks its own embedding cache
matched_documents, product_embedding_cache_hit = await self.vector_search.similarity_search(query, k=4)
```

#### Overall Cache Hit Calculation
```python
# Combine both cache hits for overall status
overall_embedding_cache_hit = intent_embedding_cache_hit or product_embedding_cache_hit
```

### UI Integration
The cache hit information is now properly displayed in the UI:
- Shows "EMBEDDING_CACHE" when embeddings are retrieved from cache
- Shows "RESPONSE_CACHE" when full responses are cached
- Displays cache statistics including hit rate and TTL

## 5. CSP Nonce Integration

### Overview
Added Content Security Policy (CSP) nonce generation to enhance security.

### Implementation
```python
# In startup.py
app.state.csp_nonce_generator = lambda: secrets.token_urlsafe(16)

# In exception handlers
csp_nonce = request.app.state.get("csp_nonce_generator", lambda: "")()
```

### Benefits
- Enhanced security for inline scripts and styles
- Available throughout the application via app state
- Consistent nonce generation for all responses

## 6. Vector Demo Exception Handling

### Overview
Created specialized exception handling for vector search demonstrations.

### Features
- Operation-specific error messages (embedding, vector_search, metrics)
- Appropriate HTMX events for different error types
- Retry logic based on error type
- User-friendly error display in the same template

### Error Types
```python
error_messages = {
    "embedding": "Failed to generate embedding for your query. Please try a different search term.",
    "vector_search": "Vector search failed. The database might be temporarily unavailable.",
    "metrics": "Failed to record search metrics, but your search was processed.",
}
```

## 7. Type Safety Improvements

### Overview
Fixed type annotations throughout the codebase to match the new return types.

### Key Fixes
- Updated all method calls to unpack tuples properly
- Fixed type hints in method signatures
- Ensured pyright passes with no errors

## Migration Guide

### For Developers

#### Updating Method Calls
```python
# Old way
results = await vector_search.similarity_search(query)

# New way
results, cache_hit = await vector_search.similarity_search(query)
# Or if you don't need cache info
results, _ = await vector_search.similarity_search(query)
```

#### Raising Exceptions
```python
# Instead of nested try/except
if not message:
    raise HTMXValidationException(detail="Message cannot be empty", field="message")
# The exception handler will automatically return an HTMX response
```

#### Using HTMX Events
```python
# Use native Litestar HTMX integration
return HTMXTemplate(
    template_name="template.html.j2",
    context={...},
    trigger_event="event:name",
    params={"key": "value"},
    after="settle"
)
```

## Testing Considerations

1. **Cache Hit Testing**: Verify that cache hits are properly tracked across all layers
2. **Exception Handling**: Test that all exception types return appropriate HTMX responses
3. **Type Safety**: Run `pyright` to ensure all types are correct
4. **Event Testing**: Verify that all HTMX events are triggered correctly

## Performance Impact

- **Positive**: Better cache hit tracking enables optimization
- **Positive**: Centralized exception handling reduces overhead
- **Neutral**: Additional tuple unpacking has negligible impact
- **Overall**: Improved performance visibility and debugging capabilities
