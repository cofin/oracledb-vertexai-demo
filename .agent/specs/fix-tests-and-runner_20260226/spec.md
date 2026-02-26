# Spec: Restore ADK Runner Functionality and Fix Test Suite

## Overview
Restore lost UI functionality from the initial ADK Runner migration and fix the project's test suite, aligning all changes with the newly adopted Domain-Driven Design (DDD) structure.

## Goals
- **Restore Full UI Functionality:** Provide the chat interface with rich contextual data (product recommendations, debug details) from the legacy orchestrator.
- **Fix the Test Suite:** Repair broken tests to pass `uv run pytest` reliably within the new DDD layout.
- **Complete the Migration:** Finalize the ADK architecture within `app/domain/chat/`.

## Implementation Plan

### Phase 1: Test Suite Repair (DDD Alignment)
- [ ] Task bd-3gq.1: Fix circular imports breaking test collection in the new domain layout.
- [ ] Task bd-3gq.2: Address `ModuleNotFoundError` for deleted legacy services (`app/services/*`).
- [ ] Task bd-3gq.3: Correct fixture errors in `tests/integration/conftest.py`.

### Phase 2: ADKRunner Enhancement
- [ ] Task bd-3gq.4: Modify `app/domain/chat/services/_adk_runner.py` to extract tool outputs and re-implement caching.
- [ ] Task bd-3gq.5: Update `app/domain/chat/controllers/_chat.py` to handle the enhanced runner response.

### Phase 3: Verification
- [ ] Task bd-3gq.6: Verify chat UI displays full context.
- [ ] Task bd-3gq.7: Ensure `uv run pytest` runs clean.