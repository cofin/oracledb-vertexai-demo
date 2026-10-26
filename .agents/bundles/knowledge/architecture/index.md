---
type: Index
title: Architecture Knowledge Index
description: System architecture, native Gemini 3.8 Flash runtime, and Oracle 26ai Hybrid RRF design
---

# Architecture Knowledge Index

- [System Architecture](system-architecture.md) - Multi-protocol Litestar 2 request pipeline, APEX REST and OpenAI-compatible Vertex AI gateway routes, package boundaries, Dishka DI scopes, SQLSpec `0.69.0` pools, background queues, and ADB-Free 26ai + APEX 26.1 tooling
- [Native Agentic AI Runtime](native-ai-runtime.md) - Re-entrant `AgentRuntime`, `GeminiModelClient`, `SpecTree` delegation, `OracleLoaderService` session/event persistence, SSE `AgentStreamService`, `LitestarMCP` 0.15, and `LitestarA2A`
- [Oracle 26ai Hybrid RRF Search](oracle-26ai-hybrid-rrf.md) - Single-query Hybrid Reciprocal Rank Fusion (`CONTAINS`/`SCORE` + HNSW `FETCH APPROX`), `app.lib.text_search` token sanitization, and `hybrid-term-hits` off-menu brand detection
