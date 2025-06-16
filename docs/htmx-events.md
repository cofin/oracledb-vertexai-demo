# HTMX Events Documentation

This document lists all custom HTMX events triggered by the Oracle + Vertex AI demo application using Litestar's native HTMX integration.

## Chat Interface Events

### `validation:error`
- **Triggered by**: `/` (POST) - handle_coffee_chat
- **When**: User input validation fails
- **Parameters**:
  - `error`: Error message string
  - `field`: Field that failed validation (e.g., "message")
- **Trigger timing**: `settle`

### `api:error`
- **Triggered by**: `/` (POST) - handle_coffee_chat
- **When**: Google API or general error occurs during recommendation
- **Parameters**:
  - `type`: "service_error"
  - `retry`: boolean (true)
- **Trigger timing**: `receive`

### `help:process-complete`
- **Triggered by**: `/` (POST) - handle_coffee_chat
- **When**: Successful chat response
- **Parameters**:
  - `vector_search`: "complete"
  - `llm_generation`: "complete"
  - `query_id`: UUID string
- **Trigger timing**: `settle`

## Dashboard Events

### `dashboard:loaded`
- **Triggered by**: `/dashboard` - performance_dashboard
- **When**: Dashboard page loads
- **Parameters**:
  - `total_searches`: Number of total searches
- **Trigger timing**: `settle`

## Metrics Events

### `metrics:high-cache-rate`
- **Triggered by**: `/api/metrics/summary` - get_metrics_summary
- **When**: Cache hit rate exceeds 90%
- **Parameters**:
  - `rate`: Cache hit rate percentage
- **Trigger timing**: `settle`

### `metrics:slow-response`
- **Triggered by**: `/api/metrics/summary` - get_metrics_summary
- **When**: Average search time exceeds 1000ms
- **Parameters**:
  - `time`: Average search time in milliseconds
- **Trigger timing**: `settle`

## Vector Search Demo Events

### `vector:error`
- **Triggered by**: Exception handlers for VectorDemoException
- **When**: Any vector operation fails (embedding, search, metrics)
- **Parameters**:
  - `operation`: Type of operation that failed ("embedding", "vector_search", "metrics")
  - `error_type`: Error classification
  - `retry`: Boolean indicating if retry is recommended
- **Trigger timing**: `settle`

### `vector:embedding-error` (deprecated)
- **Triggered by**: `/api/vector-demo` - vector_search_demo
- **When**: Embedding generation fails
- **Parameters**:
  - `query`: Original query string
- **Trigger timing**: `receive`
- **Note**: This event is deprecated in favor of the more general `vector:error` event

### `vector:search-fast`
- **Triggered by**: `/api/vector-demo` - vector_search_demo
- **When**: Total search time < 100ms
- **Parameters**:
  - `level`: "excellent"
  - `total_ms`: Total time in milliseconds
- **Trigger timing**: `settle`

### `vector:search-normal`
- **Triggered by**: `/api/vector-demo` - vector_search_demo
- **When**: Total search time between 100-500ms
- **Parameters**:
  - `level`: "good"
  - `total_ms`: Total time in milliseconds
- **Trigger timing**: `settle`

### `vector:search-slow`
- **Triggered by**: `/api/vector-demo` - vector_search_demo
- **When**: Total search time > 500ms
- **Parameters**:
  - `level`: "needs-optimization"
  - `total_ms`: Total time in milliseconds
- **Trigger timing**: `settle`

## Polling Control

### HXStopPolling
- **Triggered by**: `/metrics` - get_metrics
- **When**: No searches have been made (total_searches = 0)
- **Effect**: Stops HTMX polling on the client

## Usage Example

To listen for these events in JavaScript:

```javascript
// Listen for validation errors
document.body.addEventListener("validation:error", function(evt) {
    console.log("Validation error:", evt.detail.error);
    // Show error message to user
});

// Listen for high cache rate
document.body.addEventListener("metrics:high-cache-rate", function(evt) {
    console.log("Cache hit rate is high:", evt.detail.rate + "%");
    // Show success notification
});

// Listen for slow vector search
document.body.addEventListener("vector:search-slow", function(evt) {
    console.log("Search was slow:", evt.detail.total_ms + "ms");
    // Show performance warning
});
```

## Event Timing

- **`receive`**: Triggered as soon as the response is received
- **`settle`**: Triggered after the DOM has been updated
- **`swap`**: Triggered after content is swapped (not used in our events)

## Benefits of Native HTMX Events

1. **Decoupled UI Logic**: Frontend can react to backend events without tight coupling
2. **Progressive Enhancement**: Events enhance functionality without breaking basic features
3. **Real-time Feedback**: Users get immediate feedback about system state
4. **Performance Monitoring**: Frontend can track and display performance metrics
5. **Error Handling**: Graceful error handling with specific event types
