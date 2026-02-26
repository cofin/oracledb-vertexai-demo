# PRD: Restore ADK Runner Functionality and Fix Test Suite

## 1. Overview

The initial migration to a modern ADK Runner was structurally successful, but the implementation was oversimplified, leading to a loss of critical UI functionality that was present in the legacy system. The UI is no longer receiving the rich contextual information (product recommendations, debug details) it requires. Additionally, the project's test suite is currently broken, preventing automated verification of the new implementation and overall code health.

This document outlines the plan to address these two issues by enhancing the new `ADKRunner` to restore all previous functionality and by systematically fixing the broken test suite.

## 2. Goals and Objectives

- **Restore Full UI Functionality:** The primary goal is to make the chat interface fully functional again by providing it with the same rich, contextual data it received from the legacy orchestrator.
- **Fix the Test Suite:** Repair the broken test suite so that `uv run pytest` can be used as a reliable verification gate for this and future development.
- **Complete the Migration:** Finalize the migration to the new ADK architecture by ensuring it is both fully functional and testable.

## 3. Technical Scope

### In Scope

-   **`ADKRunner` Enhancement:** Modifying `app/services/adk/runner.py` to process events, extract tool outputs (products, intents), and re-implement response caching.
-   **Controller Update:** Updating `app/server/controllers.py` to handle the enhanced response from the `ADKRunner` and pass the full context to the HTMX template.
-   **Test Suite Repair:**
    -   Fixing circular imports that are breaking test collection.
    -   Addressing `ModuleNotFoundError` errors in test files by removing or updating imports for deleted services.
    -   Correcting fixture errors in `tests/integration/conftest.py` and other test files.

### Out of Scope

-   Introducing new features not present in the original implementation.
-   Major refactoring of the business logic within the `AgentToolsService`.
-   Changes to the database schema.

## 4. Acceptance Criteria

-   The chat UI must display product recommendations, intent details, and other debug information as it did prior to the migration.
-   The application must utilize response caching for repeated queries, which can be verified by checking for the `from_cache` flag in the UI debug section.
-   The command `uv run pytest` must execute without collection errors and show a clear summary of passing and (known) failing tests.
-   The primary test failures related to circular imports and missing modules must be resolved.
