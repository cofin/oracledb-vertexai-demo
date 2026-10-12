---
type: Index
title: Knowledge Base Index
description: Authoritative component guides, architecture patterns, and conventions for Cymbal Coffee
---

# Knowledge Base Index

This index lists the active, component-based guides, patterns, and styleguides for Cymbal Coffee.

## Workflow & Core Invariants
- [Project Workflow](workflow.md) - Canonical commands, TDD execution sequence, and quality gates

## Component Guides
- [System Architecture](guides/architecture.md) - High-level system architecture, package boundaries, and dependency injection boundaries
- [Oracle Database & SQLSpec](guides/oracle-database.md) - SQLSpec configurations, named SQL query patterns, vector storage, and HNSW indexing
- [Hybrid Search & RRF Routing](guides/hybrid-search.md) - Single-query Oracle 26ai Hybrid RRF (`CONTAINS`/`SCORE` + HNSW `FETCH APPROX`) and `hybrid-term-hits` off-menu detection
- [Native Agentic AI Runtime](guides/agentic-ai-runtime.md) - Architecture, execution loop, streaming SSE adapter, Oracle 26ai persistence, MCP, and A2A protocol integration
- [Store, Inventory & Maps](guides/store-inventory-maps.md) - Store hours, nearest-store location (Haversine), stock availability, and Google Maps
- [Frontend & UI Development](guides/frontend-ui.md) - Jinja templating, HTMX events, Tailwind CSS, and client-only Vite widgets
- [Testing & Verification](guides/testing-verification.md) - pytest AnyIO async tests, mock boundaries, and parallel worker safety
- [Operations & Packaging](guides/operations-packaging.md) - PyApp onefile Bundle-Patch-Compile pipelines, distroless Docker builds, and Release CI
- [Application Settings](guides/settings.md) - Dataclass settings structure, environment parsing precedence, and settings cleanliness

## Patterns
- [Architecture Patterns](patterns/architecture.md) - Framework boundaries, DI providers, named queries, and streaming
- [Code Style Patterns](patterns/code-style.md) - SPDX headers, PEP 604/585 typing, and module layout
- [Testing Patterns](patterns/testing.md) - AnyIO async conventions, test layout, and deterministic fixtures
- [Operations Patterns](patterns/operations.md) - Oracle HNSW sizing, APEX/ORDS lifecycle, and packaging gotchas
- [Patterns Catalog](patterns/index.md) - Complete patterns catalog

## Styleguides
- [Python Styleguide](styleguides/python.md) - Python 3.12+ style, modern typing, and docstring standards
- [TypeScript Styleguide](styleguides/typescript.md) - TypeScript type safety and client widget conventions
- [HTML & CSS Styleguide](styleguides/html-css.md) - HTML, HTMX, and Tailwind CSS conventions
- [Bash Styleguide](styleguides/bash.md) - Shell script safety and styling
- [General Styleguide](styleguides/general.md) - General coding standards

## Historical & Planning References
- [PyApp Packaging Milestone (2026-04-29)](pyapp-packaging_20260429.md)
- [Beautify UI Plan](plans/beautify-ui.md)
- [Camelized Wire Format Plan](plans/camelized.md)
- [HTMX Evaluation Plan](plans/htmx-retirement_20260226.md)
- [Installation Simplification Plan](plans/installation-simplification.md)
