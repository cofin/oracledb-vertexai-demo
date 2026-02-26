# Tasks: Fix Tests and Restore Runner Functionality

This document outlines the tasks to complete the ADK migration.

## Phase 1: Enhance ADKRunner (Expert Agent)

- [ ] **Task 1.1:** Read `app/services/adk/runner.py`.
- [ ] **Task 1.2:** Modify the `_process_events` method in `ADKRunner` to parse tool call results (products, intent) from the event stream and store them.
- [ ] **Task 1.3:** Modify the `process_request` method in `ADKRunner` to re-implement response caching logic.
- [ ] **Task 1.4:** Update the dictionary returned by `process_request` to include the full context: `answer`, `products`, `session_id`, `debug_info`, `from_cache`, etc.
- [ ] **Task 1.5:** Update the `handle_coffee_chat` method in `app/server/controllers.py` to correctly handle the new, richer response from `ADKRunner` and pass it to the template.

## Phase 2: Fix Test Suite (Testing Agent)

- [ ] **Task 2.1:** Fix the circular import issue between `app/config.py` and `app/services/adk/tools.py` by moving the `service_locator` import inside the tool functions.
- [ ] **Task 2.2:** Address `ModuleNotFoundError` errors in the test suite by renaming obsolete test files (e.g., `test_embedding_cache.py`, `test_intent_router.py`) with a `.disabled` extension.
- [ ] **Task 2.3:** Fix the `AttributeError: 'async_generator' object has no attribute 'cursor'` in `tests/integration/conftest.py` by correctly handling the `oracle_connection` fixture.
- [ ] **Task 2.4:** Fix the `TypeError` in `tests/integration/test_oracle_deploy.py` related to the `DatabaseConfig` constructor.
- [ ] **Task 2.5:** Run `uv run pytest` to confirm that the major collection errors are resolved.

## Phase 3: Final Verification (Expert Agent)

- [ ] **Task 3.1:** Run `make lint` and fix any remaining issues in the modified files.
- [ ] **Task 3.2:** Manually test the application to ensure all functionality is working as expected.
