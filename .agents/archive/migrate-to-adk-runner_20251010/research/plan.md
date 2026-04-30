# Detailed Plan: ADK Migration

This document contains the detailed 4-phase plan for migrating the application to a modern ADK architecture.

## Phase 1: Research and Analysis

1.  **Analyze Postgres Demo:** Examine the directory structure and key ADK-related files of the reference PostgreSQL project to understand its architecture and identify modern patterns.
2.  **Research Latest ADK Practices:** Use `google_web_search` and `context7` to find the latest documentation, best practices, and API references for the Google Agent Development Kit (ADK), focusing on the `Runner`, agent design, and tool definition patterns for 2025.
3.  **Review Current Implementation:** Conduct a detailed review of the existing ADK code within `app/services/adk/`, including `orchestrator.py`, `agent.py`, and `prompts.py`, to identify legacy patterns such as manual workflow enforcement, complex orchestration logic, and rigid prompting.

## Phase 2: Define New Architecture and Migration Path

Based on the research and analysis, define a new architecture that aligns with modern ADK best practices.

**Proposed Architecture:**

1.  **New Directory:** All new ADK logic will reside in a new `app/adk/` directory to ensure a clean separation from the legacy `app/services/adk/` code during development.
2.  **Simplified Runner:** A new, lean `ADKRunner` class will replace the existing `ADKOrchestrator`. Its sole responsibility will be to initialize the `adk.Runner` and expose a simple `process_request` method that calls `runner.run_async()`. All complex logic (caching, fallbacks, retries) will be removed from this layer.
3.  **Goal-Oriented Agent:** The current `CoffeeAssistantAgent` and its rigid, step-by-step prompt will be replaced. The new agent will have a goal-oriented instruction set, empowering the LLM to decide the sequence of tool calls based on the user's query and the tools' descriptions.
4.  **Decoupled Services:** The underlying business logic in `AgentToolsService` is well-structured and will be reused. Caching and other cross-cutting concerns will be handled within this service layer, completely decoupling them from the agent orchestration logic.

## Phase 3: Implementation Steps

This phase involves creating the new ADK module and integrating it into the application.

1.  **Create New Directory Structure:** Create the `app/adk/` directory and populate it with the initial files: `__init__.py`, `agent.py`, `runner.py`, `prompts.py`, and `tools.py`.
2.  **Implement the New Goal-Oriented Agent:** In `app/adk/agent.py` and `app/adk/prompts.py`, define the new `CoffeeAssistantAgent` with a flexible, goal-oriented prompt that encourages reasoning over a fixed workflow.
3.  **Implement the Simplified Runner:** In `app/adk/runner.py`, create the new `ADKRunner` class. This class will initialize the `google.adk.Runner` and contain a streamlined `process_request` method that delegates directly to the runner.
4.  **Adapt Tools:** Copy the tool definitions from `app/services/adk/tools.py` to `app/adk/tools.py` and ensure their docstrings are descriptive and clear to facilitate better understanding by the LLM.
5.  **Update Service Locator:** Modify `app/services/locator.py` to ensure the new `ADKRunner` and its dependencies are correctly instantiated.
6.  **Integrate the New Runner:** Identify the controller that handles chat requests (likely in `app/server/controllers.py`) and switch it from using the old `ADKOrchestrator` to the new `ADKRunner`.

## Phase 4: Verification and Cleanup

After the new implementation is integrated, ensure it works correctly and then remove the legacy code.

1.  **Testing:** Manually test the new agent via the application's chat interface to verify that it responds correctly to various queries.
2.  **Code Cleanup:** Once the new implementation is verified as stable, remove the old `app/services/adk/` directory and any other related legacy code.
