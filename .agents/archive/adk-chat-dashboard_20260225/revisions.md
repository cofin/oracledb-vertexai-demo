## [2026-02-26 02:15] Revision 1

**Type:** both
**Reason:** Adoption of Domain-Driven Design (DDD) and advanced Dishka DI structure from accelerator reference project.

### Changes Made

**Spec Changes:**
- Unified `prd.md` and `tasks.md` into `spec.md`.
- Added explicit DDD pathways for Domain Services (`app/domain/chat/`).
- Updated DI implementations to leverage `DomainPlugin` and `app/lib/di.py`.

**Plan Changes:**
- Added: Task bd-2t6.1 to bd-2t6.15 to track all implementation phases correctly under the new DDD structure.

### Impact Assessment
- Tasks affected: All
- Timeline impact: Minor overhead to refactor initial boilerplate
- Dependencies updated: Requires `migrate-to-dishka-di` foundational utilities

## [2026-02-26 03:56] Revision 2

**Type:** both
**Reason:** Align controller DI guidance with `accelerator` best practices (Dishka router integration instead of route-level `@inject`).

### Changes Made

**Spec Changes:**
- Updated Backend Architecture goal to require centralized `setup_dishka(container, app)` and `DomainPlugin(use_dishka_router=True)`.

**Plan Changes:**
- Revised task bd-2t6.5 to explicitly follow provider/scope layering used in accelerator (`LitestarPersistenceProvider` + domain provider pattern).
- Revised task bd-2t6.6 to require `Inject[T]` handler parameters without route-level `@inject`.

### Impact Assessment
- Tasks affected: bd-2t6.5, bd-2t6.6
- Timeline impact: None
- Dependencies updated: None
