---
type: Index
title: Knowledge Base Index
description: Authoritative OKF v0.2 architecture, domain, testing, pattern, gotcha, styleguide, and presentation guides for Cymbal Coffee
---

# Knowledge Base Index

This index organizes the authoritative engineering knowledge base for Cymbal Coffee under the Open Knowledge Format (OKF v0.2).

## Workflow & Core Invariants
- [Project Workflow](workflow.md) - Canonical commands, TDD execution sequence, and quality gates

## Architecture
- [Architecture Index](architecture/index.md)
- [System Architecture](architecture/system-architecture.md) - Multi-protocol Litestar 2 request pipeline, package boundaries, Dishka DI scopes, and background queue architecture
- [Native Agentic AI Runtime](architecture/native-ai-runtime.md) - Re-entrant `AgentRuntime`, `GeminiModelClient`, `SpecTree` delegation, Oracle session/event persistence, SSE streaming, MCP 0.15, and A2A 1.0
- [Oracle 26ai Hybrid RRF Search](architecture/oracle-26ai-hybrid-rrf.md) - Single-query Hybrid Reciprocal Rank Fusion (`CONTAINS`/`SCORE` + HNSW `FETCH APPROX`) and `hybrid-term-hits` off-menu brand detection

## Domains
- [Domains Index](domains/index.md)
- [Core Platform (`lib/`, `ioc/`, `server/`, `cli/`)](domains/core-lib-ioc-server-cli.md) - Modular settings, SQLSpec loader, Dishka providers, Litestar plugin wiring, and `coffee` CLI
- [AI & Protocols (`domain/ai/`)](domains/ai-and-protocols.md) - Native `AgentRuntime`, `AgentOrchestrationService`, `LitestarMCP` 0.15 controllers, and `LitestarA2A` executor
- [Chat, Products, Stores & System (`domain/{chat,products,system,web}/`)](domains/chat-products-stores-system.md) - Hybrid RRF routing, grounded composers, HNSW product/store queries, maps, cache, metrics, and UI templates

## Testing
- [Testing Index](testing/index.md)
- [Unit & Integration Test Catalog](testing/unit-and-integration-catalog.md) - Flattened test tree layout, AnyIO async rules, AST/tokenize meta-guards, and Oracle 26ai integration fixtures

## Patterns
- [Patterns Index](patterns/index.md)
- [Architecture Patterns](patterns/architecture.md) - Framework boundaries, DI providers, named queries, and streaming
- [Code Style Patterns](patterns/code-style.md) - SPDX headers, PEP 604/585 typing, and module layout
- [Testing Patterns](patterns/testing.md) - AnyIO async conventions, test layout, and deterministic fixtures
- [Operations Patterns](patterns/operations.md) - Oracle HNSW sizing, APEX/ORDS lifecycle, and packaging gotchas

## Gotchas
- [Gotchas Index](gotchas/index.md)
- [Oracle 26ai, SQLSpec & Queues Gotchas](gotchas/oracle-sqlspec-and-queues.md) - HNSW `FETCH APPROX`, `vector_memory_size`, `OracledbAsyncQueueStore` LOB pool isolation, and Oracle Text `{token}` escaping
- [Litestar Security, Dishka & Vertex AI Gotchas](gotchas/litestar-security-and-vertex.md) - Dishka runtime annotations, `PublicController` CSRF exemptions, `GEMINI_CHAT_LOCATION="global"`, and coordinate privacy

## Presentation Guide
- [Oracle in the Age of Gemini (2026)](presentation/index.md) - Speaker guide, storyboard, verified facts, and porting corrections for the DBA talk built on this demo

## Styleguides
- [Python Styleguide](styleguides/python.md) - Python 3.12+ style, modern typing, and docstring standards
- [TypeScript Styleguide](styleguides/typescript.md) - TypeScript type safety and client widget conventions
- [HTML & CSS Styleguide](styleguides/html-css.md) - HTML, HTMX, and Tailwind CSS conventions
- [Bash Styleguide](styleguides/bash.md) - Shell script safety and styling
- [General Styleguide](styleguides/general.md) - General coding standards
