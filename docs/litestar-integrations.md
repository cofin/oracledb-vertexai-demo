# Litestar Framework Integrations

This document outlines the Litestar framework integrations used in the Oracle + Vertex AI demo application.

## Currently Used Integrations

### 1. HTMX Plugin

- **Plugin**: `HTMXPlugin` - Enables HTMX-specific functionality globally
- **Request Class**: `HTMXRequest` - Provides access to HTMX headers and details
- **Response Class**: `HTMXTemplate` - Returns templates with HTMX-specific headers

## Enhanced HTMX Integration

We've updated the controller to use Litestar's native HTMX response features:

```python
# Before: Manual header setting
response.headers["HX-Trigger"] = """{"help:vector-search-complete": {}, "help:llm-complete": {}}"""

# After: Native HTMX support
return HTMXTemplate(
    template_name="partials/chat_response.html.j2",
    context={...},
    trigger_event="help:process-complete",
    params={
        "vector_search": "complete",
        "llm_generation": "complete",
        "query_id": reply.query_id,
    },
    after="settle",  # Trigger after DOM settles
)
```

## Available HTMX Response Classes

### 1. TriggerEvent

Trigger custom client-side events:

```python
return TriggerEvent(
    content="Success!",
    name="showMessage",
    params={"alert": "Confirm your Choice."},
    after="receive"  # 'receive', 'settle', or 'swap'
)
```

### 2. Reswap

Control DOM swapping method:

```python
return Reswap(content="Success!", method="outerHTML")
```

### 3. Retarget

Dynamically change target element:

```python
return Retarget(content="Success!", target="#new-target")
```

### 4. PushUrl/ReplaceUrl

Control browser history:

```python
return PushUrl(content="Success!", push_url="/about")
return ReplaceUrl(content="Success!", replace_url="/contact-us")
```

### 5. HXLocation

Redirect without full page reload:

```python
return HXLocation(
    redirect_to="/contact-us",
    target="#target",
    swap="outerHTML",
    values={"val": "one"}
)
```

### 6. ClientRedirect/ClientRefresh

Force page actions:

```python
return ClientRedirect(redirect_to="/contact-us")
return ClientRefresh()
```

### 7. HXStopPolling

Stop HTMX polling:

```python
return HXStopPolling()
```

## Benefits of Using Native Integrations

1. **Type Safety**: Better IDE support and type checking
2. **Cleaner Code**: Less manual header manipulation
3. **Framework Features**: Access to all HTMX response options
4. **Consistency**: Following Litestar best practices
5. **Future Compatibility**: Updates handled by framework

## Example Use Cases

### Dynamic UI Updates

Use `Retarget` to change where content appears based on user actions.

### Progress Indicators

Use `TriggerEvent` to update progress bars during long operations.

### Form Validation

Use `Reswap` with `beforebegin` to add validation messages.

### Navigation

Use `HXLocation` for SPA-like navigation without full reloads.
