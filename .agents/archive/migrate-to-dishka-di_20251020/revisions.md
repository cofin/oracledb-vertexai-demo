## [2026-02-26 03:55] Revision 1

**Type:** both
**Reason:** Align Dishka route injection guidance with `accelerator` best practices (`DomainPlugin(use_dishka_router=True)` + centralized `setup_dishka`).

### Changes Made

**Spec Changes:**
- Clarified that controller handlers should use `Inject[T]` parameters without route-level `@inject` decorators.
- Clarified plugin-level DI wiring expectations in `core.py`/`plugins.py` (`use_dishka_router=True`).

**Plan Changes:**
- Revised task bd-2ri.4 wording to include Dishka router integration in plugin setup.
- Revised task bd-2ri.9 wording to replace `@inject` usage with `Inject[T]` + Dishka router pattern.

### Impact Assessment
- Tasks affected: bd-2ri.4, bd-2ri.9
- Timeline impact: None
- Dependencies updated: None
