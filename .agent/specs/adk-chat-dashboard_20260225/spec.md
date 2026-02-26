# Spec: ADK Chat & Dashboard (adk-chat-dashboard_20260225)

## Overview
Port the modern frontend architecture from the `accelerator` project into `oracledb-vertexai-demo` to replace the HTMX application. Build a modern, full-stack application featuring a simple, intuitive chat interface powered by Google ADK (Agent Development Kit) and `google.genai`, along with a secondary, more complex dashboard page. The backend will follow the new Domain-Driven Design (DDD) layout.

## Goals
1. **Frontend Architecture Bootstrapping**: Introduce `litestar-vite`, `react` 19, `bun`, `tanstack`, and `shadcn` into the repository.
2. **Dependency Exclusion**: Use `uv` overrides in `pyproject.toml` to prevent legacy ADK dependencies.
3. **Simple Chat Interface (Page 1)**: A clean chat interface for interacting with a Google ADK agent.
4. **Complex Dashboard (Page 2)**: A sophisticated data view displaying chat history using `TanStack Table`.
5. **Backend Architecture (DDD)**: Explicit DI configuration using `app/lib/di.py` and `DomainPlugin` for auto-discovery of controllers in `app/domain/chat/`.

## Implementation Plan

### Phase 0: HTMX Code & Template Removal
- [ ] Task bd-2t6.1: Delete legacy HTMX templates (`app/server/templates/`) and static assets.
- [ ] Task bd-2t6.2: Remove HTMXPlugin from `app/server/plugins.py` and HTMX exception handlers.

### Phase 1: Environment & Dependency Setup
- [ ] Task bd-2t6.3: Update `pyproject.toml` with `uv` overrides for legacy dependencies.
- [ ] Task bd-2t6.4: Install `google-adk` and `google-genai`.

### Phase 2: Database & Domain Services (SQLSpec & DDD)
- [ ] Task bd-2t6.5: Configure Dishka Dependency Injection in `app/domain/chat/services/` for `OracleAsyncADKStore`.
- [ ] Task bd-2t6.6: Implement the Litestar `ChatController` in `app/domain/chat/controllers/_chat.py` using `@inject`.
- [ ] Task bd-2t6.7: Integrate Google ADK Agent within the domain service.

### Phase 3: Frontend Bootstrapping (Litestar-Vite & React)
- [ ] Task bd-2t6.8: Add `litestar-vite` and configure `VitePlugin`.
- [ ] Task bd-2t6.9: Scaffold `src/js/web` directory (React, Bun, TanStack, Shadcn).

### Phase 4: Frontend Setup & Routing (TanStack)
- [ ] Task bd-2t6.10: Run `litestar assets generate-types` for TanStack Query hooks.
- [ ] Task bd-2t6.11: Scaffold TanStack Router file-based route tree.

### Phase 5: UI Implementation (React & Shadcn)
- [ ] Task bd-2t6.12: Build the Simple Chat Interface (`/chat`).
- [ ] Task bd-2t6.13: Build the Complex Dashboard (`/dashboard`).

### Phase 6: Testing & Quality Gate
- [ ] Task bd-2t6.14: Write Pytest unit/integration tests for the backend.
- [ ] Task bd-2t6.15: Write Vitest tests for frontend components.