# Flow: HTMX Retirement (htmx-retirement_20260226)

## Specification

### Objective
Remove remaining HTMX-specific coupling from the active product path so the application is React-first and API-driven.

### Requirements
1. Identify all HTMX route/controller/template/plugin dependencies in active UX paths.
2. Remove or replace HTMX-specific request/response types where no longer needed.
3. Delete obsolete templates/assets once React paths are validated.
4. Preserve startup health and endpoint reliability after cleanup.

### Acceptance Criteria
- No core UX path requires HTMX artifacts.
- Startup and smoke tests pass after HTMX retirement.
- React pages remain fully functional.

## Implementation Plan

### Phase 1: Discovery and Removal
- [x] 1.1 Inventory HTMX dependencies and remove active route coupling. (`bd-5oj.4.1`)
- [x] 1.2 Retire legacy template/plugin wiring. (`bd-5oj.4.2`)
- [x] 1.3 Refactor backend handlers away from HTMX-specific types. (`bd-5oj.4.3`)

### Phase 2: Regression Validation
- [x] 2.1 Execute regression test and startup/smoke verification. (`bd-5oj.4.4`)
