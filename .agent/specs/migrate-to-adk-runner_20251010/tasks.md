# Tasks: ADK Migration

This document outlines the tasks required to migrate the application to the modern ADK Runner architecture. Tasks are assigned to the appropriate agent role.

## Phase 1: Planning & Research (Planner Agent)

- [x] Analyze user requirement for ADK migration.
- [x] Research latest Google ADK best practices (2025+).
- [x] Analyze current ADK implementation in `app/services/adk/`.
- [x] Identify and document legacy patterns (orchestrator complexity, rigid prompts).
- [x] Create workspace structure in `specs/migrate-to-adk-runner/`.
- [x] Write Product Requirements Document (`prd.md`).
- [x] Write Task Breakdown (`tasks.md`).
- [x] Write Recovery Guide (`recovery.md`).

## Phase 2: Core Implementation (Expert Agent)

- [ ] **Task 2.1:** Create the new directory `app/adk/`.
- [ ] **Task 2.2:** Create `app/adk/prompts.py` with a new goal-oriented `SYSTEM_INSTRUCTION` for the agent.
- [ ] **Task 2.3:** Create `app/adk/tools.py` by adapting the existing tools from `app/services/adk/tools.py`. Ensure docstrings are clear and descriptive for the LLM.
- [ ] **Task 2.4:** Create `app/adk/agent.py` to define the new `CoffeeAssistantAgent` using the new prompt and tools.
- [ ] **Task 2.5:** Create `app/adk/runner.py` with a new `ADKRunner` class. This class will contain the simplified `process_request` logic that calls `google.adk.Runner`.
- [ ] **Task 2.6:** Create `app/adk/__init__.py` to export the new components.

## Phase 3: Framework Integration (Expert Agent)

- [ ] **Task 3.1:** Update `app/services/locator.py` to recognize and instantiate the new `ADKRunner` from `app/adk/runner.py`.
- [ ] **Task 3.2:** Identify the chat endpoint in `app/server/controllers.py`.
- [ ] **Task 3.3:** Modify the chat endpoint to use the new `ADKRunner` service instead of the legacy `ADKOrchestrator`.

## Phase 4: Verification and Cleanup (Testing & Docs & Vision Agents)

- [ ] **Task 4.1 (Testing):** Manually test the new implementation via the application's chat interface. Verify that product search, recommendations, and general conversation work correctly.
- [ ] **Task 4.2 (Docs & Vision):** Once verification is complete, remove the entire legacy `app/services/adk/` directory.
- [ ] **Task 4.3 (Docs & Vision):** Update any relevant documentation if necessary.
- [ ] **Task 4.4 (Docs & Vision):** Run final linting and quality checks.