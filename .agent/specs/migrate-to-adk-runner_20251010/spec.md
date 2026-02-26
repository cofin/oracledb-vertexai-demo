# Spec: Migration to Modern ADK Runner Architecture

## Overview
Replace the legacy `ADKOrchestrator` with a lean implementation using `google.adk.Runner` in a modern Domain-Driven Design (DDD) layout.

## Goals
- **Modernize the Agentic System:** Use the latest `google.adk.Runner` patterns.
- **Empower the Agent:** Transition to a flexible, goal-oriented prompt.
- **Decouple Concerns:** Separate orchestration, tool logic, and caching into appropriate domains (`app/domain/chat/`, `app/domain/products/`).

## Implementation Plan

### Phase 1: Modern ADK Domain Setup
- [ ] Task bd-36f.1: Create `app/domain/chat/services/_adk_runner.py` for the modern implementation.
- [ ] Task bd-36f.2: Write a goal-oriented system prompt for the `CoffeeAssistantAgent`.

### Phase 2: Controller Integration
- [ ] Task bd-36f.3: Update `app/domain/chat/controllers/_chat.py` to use the new runner via Dishka DI.

### Phase 3: Legacy Decommissioning
- [ ] Task bd-36f.4: Fully decouple and remove the legacy `ADKOrchestrator`.
- [ ] Task bd-36f.5: Delete legacy `app/services/adk/` directory after verification.