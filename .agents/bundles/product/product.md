---
type: Guide
title: Core Product Definition
description: Cymbal Coffee reference application product definition and mandates
tags:
  - product
  - reference-app
---

# Initial Concept

An intelligent coffee recommendation and store-operations system showcasing Oracle AI Database 26ai Hybrid RRF search, Oracle APEX 26.1, Google Vertex AI, and native agentic orchestration.

<!-- truth: start -->
## Core Product Definition

This project is a reference application demonstrating a fictitious company named **Cymbal Coffee**.

Its primary purpose is to showcase the features, functionality, and best practices of building AI-powered applications using:
- **Oracle AI Database 26ai & Autonomous AI Database Free** (Vector Search `VECTOR(3072, FLOAT32)`, HNSW `FETCH APPROX`, Oracle Text `CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE`, single-query Hybrid RRF, `FOR UPDATE SKIP LOCKED` background queues, and managed local `adb-free:latest-26ai` mTLS `.envs/tns` runtime)
- **Oracle APEX 26.1 + ORDS 26.3** (`src/apex/cymbal-coffee-ops/` App ID `100` in APEXlang `compatibilityMode: 26.1` with direct Vertex AI `/endpoints/openapi` `APEX_AI.GENERATE` grounding and optional Litestar OpenAI-compatible gateway)
- **Google Vertex AI** (`gemini-embedding-2` 3072-dim embeddings and `gemini-3.8-flash` via `google-genai`)
- **Native Agentic AI Runtime** (`AgentRuntime`, `LitestarMCP` `0.15`, `LitestarA2A`)
- **Litestar 2 & SQLSpec `0.69.0`** (`OracleLoaderService`, `FrozenBaseStruct` `msgspec` schemas, Dishka DI, `litestar-queues`, `litestar-security`, `litestar-autowire`, `litestar-htmx`, `litestar-vite`)

### Key Features
- **Barista Chat Application:** A streaming SSE chat interface allowing users to converse with an AI barista across 4 personas.
- **Single-Query Hybrid RRF Routing & Retrieval:** Fusing BM25-style lexical ranking (`CONTAINS`/`SCORE`) and HNSW cosine similarity (`VECTOR_DISTANCE`) across routes, products, and stores in one database round trip.
- **Grounded Off-Menu Detection:** Using in-database `hybrid-term-hits` (`JSON_TABLE` + `CONTAINS`) to distinguish taste preferences from off-menu brands (`"Folgers"`).
- **Location & Inventory Grounding:** Store coordinates, Haversine nearest-store search, `store_product_inventory` stock lookups, and privacy-preserving keyless Google Maps links.
- **Oracle APEX 26.1 Operations Portal:** Declarative APEXlang store-operations app (`cymbal-coffee-ops`, App ID `100`) combining live catalog, store inventory, and availability views with Page 6 `APEX_AI.GENERATE` recommendations powered by Vertex AI `gemini-3.8-flash`.

## Reference Application Mandates
- **Simplicity & Conciseness:** Logic must be straightforward and easy to follow.
- **Correctness:** Adhere strictly to type safety and architectural patterns.
- **No Dead Code:** Rigorously remove unused imports, variables, and logic.
<!-- truth: end -->
