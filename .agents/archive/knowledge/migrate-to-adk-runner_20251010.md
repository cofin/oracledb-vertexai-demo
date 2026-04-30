# Knowledge Entry: migrate-to-adk-runner_20251010

- **Flow ID:** `migrate-to-adk-runner_20251010`
- **Description:** Replace legacy ADK orchestrator with modern ADK runner and DDD-aligned integration
- **Completed:** 2026-02-26
- **Archived:** 2026-02-26
- **Topics:** adk, dishka, ddd, runner

<!-- truth: start -->
## Summary
This flow finalized the ADK runner migration by validating current-domain placement, controller injection wiring, and legacy orchestrator removal. It aligned task definitions with the modern folder layout and closed the remaining migration bookkeeping.

## Patterns Elevated
- Use `app/domain/chat/services/adk.py` as the canonical ADK runner location in DDD projects.

## Key Files
- `app/domain/chat/services/adk.py`
- `app/domain/chat/controllers.py`
- `app/domain/system/services.py`
- `.agent/archive/migrate-to-adk-runner_20251010/spec.md`

## Learnings (verbatim)

- In DDD layout, ADK runner implementation should live under `app/domain/chat/services/adk.py`, not legacy flat service paths.
- Persona-aware system prompt composition (`BASE_SYSTEM_INSTRUCTION` + persona overlay) keeps one static ADK agent reusable while preserving behavioral flexibility.
- Dishka router integration (`Inject[ADKRunner]` on handlers, no route decorators) keeps DI explicit and framework-native.
<!-- truth: end -->
