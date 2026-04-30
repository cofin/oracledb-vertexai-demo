# Learnings: htmx-retirement_20260226

- Keep chat/metrics/vector controllers API-first: return JSON payloads for SPA consumers and remove template rendering from active product paths.
- Once React routes are canonical, remove legacy HTMX routes/templates in the same pass to avoid partial dual-stack maintenance.
- Central Dishka plugin wiring in `core.py` is sufficient for controller dependency injection; avoid redundant route-level `@inject` decorators.
