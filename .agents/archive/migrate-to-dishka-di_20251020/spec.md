# Spec: Migrate to Dishka DI and Domain-Driven Architecture

## Overview
Migrate the Litestar + SQLSpec application from a custom service locator pattern to Dishka Dependency Injection framework, and restructure the codebase into a Domain-Driven Design (DDD) layout inspired by the `accelerator` reference project. This will eliminate architectural debt, provide advanced async dependency injection context control, enable Litestar plugin-based auto-discovery, and separate concerns strictly by domain.

## Goals
- Replace custom `ServiceLocator` with Dishka.
- Refactor the project structure into isolated domains (`app/domain/system`, `app/domain/chat`, `app/domain/products`, etc.) containing their own `controllers.py`, `services.py`, `schemas.py`, and `jobs.py`.
- Implement an advanced `app/lib/di.py` matching the accelerator (including `worker_scope`, `get_from_connection`, `with_websocket_request`).
- Refactor `app/server/core.py` to use `ApplicationCore` and Litestar plugins (`DomainPlugin`, `SQLSpecPlugin`) with `use_dishka_router=True`.
- Ensure Dishka wiring is centralized (`setup_dishka(container, app)` in app startup/factory) and route handlers use `Inject[T]` parameters without `@inject` decorators.
- Eliminate dead code (`locator.py`, `deps.py`).

## Implementation Plan

### Phase 1: Foundational Framework and DI Utilities
- [x] Task bd-2ri.1: Install `dishka` and update `pyproject.toml`
- [x] Task bd-2ri.2: Implement advanced `app/lib/di.py` (with `Inject`, `worker_scope`, `with_websocket_request`, `job_inject`)
- [x] Task bd-2ri.3: Implement `app/utils/domains.py` (DomainPlugin) to auto-discover controllers, jobs, and listeners
- [x] Task bd-2ri.4: Refactor `app/server/core.py` and `app/server/plugins.py` to use `ApplicationCore`, register `DomainPlugin`/`SQLSpecPlugin`, and enable `use_dishka_router=True`

### Phase 2: Domain-Driven Code Restructuring
- [x] Task bd-2ri.5: Create `app/domain/system/` (controllers, services, schemas) and migrate base application logic
- [x] Task bd-2ri.6: Create `app/domain/products/` and migrate `ProductService`, vector search, and related controllers
- [x] Task bd-2ri.7: Create `app/domain/chat/` and migrate `IntentService`, `AgentToolsService`, `ADKRunner`, and related chat controllers
- [x] Task bd-2ri.8: Ensure all services within domains provide Dishka Providers explicitly (or utilize auto-discovery if supported)

### Phase 3: Controller and Service Refactoring
- [x] Task bd-2ri.9: Update all controllers across domains to use `Inject[T]` with Dishka router integration (no route-level `@inject`) instead of dependencies dictionary
- [x] Task bd-2ri.10: Update all services to receive their dependencies via `__init__` rather than accessing `service_locator`
- [x] Task bd-2ri.11: Refactor ADK tool functions to extract the active `request_container_var` context from `app.lib.di` instead of instantiating local sessions

### Phase 4: Cleanup and Verification
- [x] Task bd-2ri.12: Remove old `app/server/controllers.py`, `app/services/locator.py`, `app/server/deps.py`, and legacy `app/services/`
- [x] Task bd-2ri.13: Verify that `uv run manage.py doctor` and `make test` complete successfully with the new structure
- [x] Task bd-2ri.14: Document the new Domain-Driven Architecture and DI patterns in `.agent/product-guidelines.md`
