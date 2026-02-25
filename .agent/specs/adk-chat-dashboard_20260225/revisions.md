## [2026-02-25 20:44] Revision 2

**Type:** plan
**Reason:** Analyzed the `sqlspec` ADK extension code (`OracleAsyncADKStore` and `SQLSpecSessionService`). Discovered it handles all schema migrations natively (including JSON storage detection and `INMEMORY` configurations) via `await store.ensure_tables()`. This removes the need to write manual `.sql` files or build custom Domain Services to duplicate this logic.

### Changes Made

**Spec Changes:**
- Updated the "Persistence" architecture note to explicitly mention native management via `sqlspec.extensions.adk.SQLSpecSessionService` and `OracleAsyncADKStore`.

**Plan Changes:**
- Removed: Task 3 - Create SQL files for chat and metrics. (Redundant)
- Removed: Task 4 - Implement Domain Services. (Redundant, using native service)
- Added: Task 3.1 - Update `dma/config.py` with ADK extension settings (`in_memory: True`).
- Added: Task 4.1 - Configure Dishka DI to provide `OracleAsyncADKStore` and `SQLSpecSessionService`.
- Modified: Task 5 & 6 - Reworded to inject `SQLSpecSessionService` directly into the `ChatController` and pass it to the ADK `Agent`.

### Impact Assessment

- Tasks affected: Task 3, 4, 5, 6.
- Timeline impact: Will save significant time by removing the need to write raw SQL blocks and map them through custom classes.
- Dependencies updated: None.

## [2026-02-25 20:53] Revision 3

**Type:** both
**Reason:** Realized that the oracledb-vertexai-demo project does not currently have the modern frontend stack (React, Vite, TanStack, Shadcn). It is entirely HTMX-based right now. To port the UI over from the accelerator project as requested, the plan must explicitly include bootstrapping the entire Litestar-Vite and React ecosystem before we can build the new UI.

### Changes Made

**Spec Changes:**
- Added explicit requirement to bootstrap the frontend architecture (Litestar-Vite, React, Bun, TanStack, Shadcn) in Section 1.2.

**Plan Changes:**
- Added Phase 3: Frontend Bootstrapping (Tasks 7.1, 7.2, 7.3).
- Reworded Phase 4: Frontend Setup & Routing (Tasks 8.1, 8.2).
- Removed original Tasks 7 & 8.

### Impact Assessment

- Tasks affected: Task 7, Task 8 (replaced with 7.1-7.3, 8.1-8.2).
- Timeline impact: Adds significant bootstrapping time, but provides all necessary detail to do it in one pass correctly.
- Dependencies updated: Requires adding litestar-vite to pyproject.toml.

## [2026-02-25 21:35] Revision 4

**Type:** both
**Reason:** The user requested explicit documentation of all legacy HTMX code and files that must be removed as part of the frontend transition.

### Changes Made

**Spec Changes:**
- Added **Phase 0: HTMX Code & Template Removal** detailing specific files to delete and code blocks to refactor.

**Plan Changes:**
- Added Phase 0 Tasks:
  - Task 0.1: Remove HTMX templates and static assets.
  - Task 0.2: Strip HTMX from Litestar configuration.
  - Task 0.3: Refactor Exception Handlers.
  - Task 0.4: Refactor Controllers for JSON APIs.

### Impact Assessment

- Tasks affected: Added new initial cleanup phase.
- Timeline impact: Adds necessary cleanup steps before building the new API and frontend.
- Dependencies updated: None.
