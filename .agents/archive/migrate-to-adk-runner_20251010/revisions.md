## [2026-02-26 02:15] Revision 1

**Type:** both
**Reason:** Adoption of Domain-Driven Design (DDD) and advanced Dishka DI structure from accelerator reference project.

### Changes Made

**Spec Changes:**
- Unified `prd.md` and `tasks.md` into `spec.md`.
- Re-routed ADK integration from `app/services/adk/` to `app/domain/chat/`.

**Plan Changes:**
- Added: Tasks bd-36f.1 to bd-36f.5 focusing on DDD-aligned ADK runner implementations.

### Impact Assessment
- Tasks affected: All
- Timeline impact: None
- Dependencies updated: None

## [2026-02-26 03:56] Revision 2

**Type:** both
**Reason:** Keep ADK runner migration aligned with Dishka handler best practices from `accelerator`.

### Changes Made

**Spec Changes:**
- Added explicit DI best-practice goal: `Inject[T]` handler parameters with Dishka router wiring, no route-level `@inject`.

**Plan Changes:**
- Revised task bd-36f.3 to require `Inject[ADKRunner]` with router-integrated Dishka DI instead of decorator-based injection.

### Impact Assessment
- Tasks affected: bd-36f.3
- Timeline impact: None
- Dependencies updated: None
