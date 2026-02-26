# Knowledge Entry: adk-chat-dashboard_20260225

- **Flow ID:** `adk-chat-dashboard_20260225`
- **Description:** Implement ADK-powered chat plus dashboard using Litestar-Vite and TanStack frontend stack
- **Completed:** 2026-02-26
- **Archived:** 2026-02-26
- **Topics:** adk, dishka, litestar, react, tanstack, testing

## Summary
This flow delivered the full ADK chat/dashboard surface on the modern frontend stack and aligned DI and domain boundaries with accelerator-style Dishka practices. It also established test coverage for both backend API behavior and frontend route rendering.

## Patterns Elevated
- Prefer centralized Dishka setup (`setup_dishka`) with `DomainPlugin(use_dishka_router=True)` and handler-level `Inject[T]` over route-level `@inject`.

## Key Files
- `app/ioc.py`
- `app/server/asgi.py`
- `app/domain/chat/controllers/_chat.py`
- `app/domain/chat/services/_adk/runner.py`
- `app/domain/chat/services/_adk/tools.py`
- `src/js/web/src/routes/chat.tsx`
- `src/js/web/src/routes/dashboard.tsx`
- `src/js/web/src/routes/chat.test.tsx`
- `src/js/web/src/routes/dashboard.test.tsx`

## Learnings (verbatim)

- For Dishka + Litestar domain routing, keep DI wiring centralized (`setup_dishka(container, app)` + `DomainPlugin(use_dishka_router=True)`) and avoid route-level `@inject` decorators.
- Preserve generated API/types artifacts and route scaffolding early (`litestar assets generate-types`) to reduce frontend/backend contract drift.
- Maintain both lightweight chat UI and richer dashboard UI tests to keep quick-path and analytics-path regressions visible.
