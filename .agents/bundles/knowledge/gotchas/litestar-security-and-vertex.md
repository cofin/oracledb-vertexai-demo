---
type: Guide
title: Litestar Security, Dishka & Vertex AI Gotchas
description: Dishka runtime annotations, PublicController CSRF exemptions, GEMINI_CHAT_LOCATION=global, and coordinate privacy
tags:
  - gotchas
  - dishka
  - litestar-security
  - vertex-ai
---

# Litestar Security, Dishka & Vertex AI Gotchas

## 1. Dishka Provider Modules Must Omit `from __future__ import annotations`

- **Trap**: Dishka inspects `@provide` parameter and return annotations at runtime. Adding `from __future__ import annotations` to `src/app/ioc/_database.py`, `_ai.py`, or `_domain.py` turns annotations into strings and breaks container construction.
- **Rule**: Never add `from __future__ import annotations` in `src/app/ioc/*.py`.

## 2. Vertex AI Preview Gemini Models Require `location="global"`

- **Trap**: Calling `gemini-3.8-flash` against a regional Vertex AI endpoint (such as `us-central1`) fails with `404 NOT_FOUND` while `gemini-embedding-2` succeeds on regional endpoints.
- **Rule**: `AISettings` splits `LOCATION` (`us-central1` for embeddings) from `CHAT_LOCATION` (`global` for `genai.Client` chat/agent turns).

## 3. Placeholder `GOOGLE_CLOUD_PROJECT` Must Raise Typed 503 (`AIServiceUnconfigured`)

- **Trap**: Unconfigured `.env` files with placeholder project IDs (`your-project-id`) cause unhandled 500 tracebacks during Vertex AI calls if not caught early, or cause `Settings.configure_genai_env()` to pop a valid `GOOGLE_API_KEY` if checked with a plain truthy string check.
- **Rule**: Validate against `PLACEHOLDER_VALUES` via `settings.ai.has_valid_project_id()` / `settings.ai.has_valid_api_key()` in `Settings.configure_genai_env()` and raise `AIServiceUnconfigured` (mapped to HTTP 503 with actionable setup guidance) when neither is configured.

## 4. Browser Coordinates and Multi-Turn Session Context Must Bypass Global Response Cache

- **Trap**: Caching or logging `LocationContext` (`latitude`, `longitude`) leaks user geolocation across sessions or into database tables, and caching multi-turn follow-up responses (where `history` or `session.state["last_products"]` is active, e.g. *"Is it available near me?"* or *"Which of those is lowest acid?"*) contaminates global `response_cache` across sessions.
- **Rule**: Use `safe_location_context()` and `request_coordinates()` in `src/app/domain/chat/services/_telemetry.py`, bypass `CacheService` reads and writes whenever browser coordinates or prior session history (`has_session_context=bool(history)`) are present, and never store coordinates in `agent_session`, `agent_event`, `response_cache`, or `search_metrics`.
