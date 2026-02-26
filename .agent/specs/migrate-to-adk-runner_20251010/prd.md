# PRD: Migration to Modern ADK Runner Architecture

## 1. Overview

The current implementation of the Google Agent Development Kit (ADK) in this project relies on legacy patterns, characterized by a complex and rigid `ADKOrchestrator` that manually handles conversation flow, state management, and error handling. This creates a brittle system that is difficult to maintain and does not fully leverage the reasoning capabilities of modern LLMs.

This document outlines the plan to migrate the system to a modern, agent-native architecture following a "clean break" approach. The new architecture will be developed in a separate module (`app/adk`) to ensure no disruption to the existing system until the final integration step.

## 2. Goals and Objectives

- **Modernize the Agentic System:** Replace the legacy orchestrator with a lean implementation that uses the latest `google.adk.Runner` patterns.
- **Simplify Orchestration:** Eliminate complex, hard-coded workflow logic, retries, and fallbacks from the orchestration layer.
- **Empower the Agent:** Transition from a rigid, step-by-step prompt to a flexible, goal-oriented prompt that allows the LLM to reason about the best sequence of tool calls.
- **Decouple Concerns:** Ensure a clean separation between the agent/runner (orchestration), tool service (business logic), and caching services.
- **Improve Maintainability:** Produce a simpler, more readable, and more robust codebase that is easier to extend.

## 3. Technical Scope

### In Scope

- Creation of a new `app/adk/` module to house the modern implementation.
- A new `ADKRunner` class that simplifies the `process_request` loop by delegating orchestration to `google.adk.Runner`.
- A new goal-oriented system prompt for the `CoffeeAssistantAgent`.
- Refactoring `app/services/locator.py` to integrate the new ADK components.
- Updating the chat controller in `app/server/controllers.py` to use the new runner.
- Decommission and removal of the legacy `app/services/adk/` module upon successful verification.

### Out of Scope

- Changes to the underlying business logic within `AgentToolsService`.
- Modifications to the database schema (`product`, `intent_exemplar`, etc.).
- Alterations to the frontend UI or HTMX templates.
- Changes to the existing testing framework, other than updating tests to target the new implementation.

## 4. Acceptance Criteria

- The application's chat functionality must be fully operational, handling product searches and general conversation as effectively as or better than the legacy system.
- The legacy `ADKOrchestrator` class must be fully decoupled and no longer used for processing chat requests.
- The new `ADKRunner` class must be the primary entry point for handling agent-based chat.
- All complex workflow logic (manual retries, hardcoded fallbacks) must be removed from the orchestration layer.
- The legacy `app/services/adk/` directory and its contents must be successfully deleted after the new system is verified.

## 5. Implementation Phases

The migration will follow the structured 4-phase plan detailed in `specs/migrate-to-adk-runner/research/plan.md`.
