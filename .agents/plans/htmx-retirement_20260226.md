# Knowledge Entry: htmx-retirement_20260226

- **Flow ID:** `htmx-retirement_20260226`
- **Completed:** 2026-02-26
- **Archived:** 2026-02-26
- **Topics:** htmx, react, litestar, routing
- **Patterns Elevated:** React-first controller pattern (API-only core controllers)

## Summary
Completed retirement of HTMX-specific coupling in the active product path after the React redesign chapters landed. The backend now serves SPA routes and JSON APIs without relying on HTMX request/response types or template rendering in core UX controllers.

## Key Files
- `src/py/app/domain/chat/controllers/_chat.py`
- `src/py/app/domain/system/controllers/_metrics.py`
- `src/py/app/domain/products/controllers/_vector.py`
- `src/py/app/config.py`
- `src/py/app/server/core.py`

## Learnings (verbatim)
- Keep chat/metrics/vector controllers API-first: return JSON payloads for SPA consumers and remove template rendering from active product paths.
- Once React routes are canonical, remove legacy HTMX routes/templates in the same pass to avoid partial dual-stack maintenance.
- Central Dishka plugin wiring in `core.py` is sufficient for controller dependency injection; avoid redundant route-level `@inject` decorators.
