---
type: Guide
title: Application Settings Guide
description: Dataclass settings structure, environment parsing precedence, and settings hygiene
tags:
  - settings
  - configuration
  - dataclass
---

# Application Configuration & Settings Guide

This guide details the settings contract, environment variables parsing, and configuration structure.

## Settings Architecture

Configuration uses a modular dataclass-based structure under `src/app/lib/settings/` (`_base.py`, `_app.py`, `_database.py`, `_ai.py`, `_vite.py`, `_maps.py`, `_mcp.py`, `_queue.py`).
- **Initialization:** Settings are instantiated via a cached factory function:
  ```python
  from app.lib.settings import Settings

  settings = Settings.from_env()
  ```
- **Immutability:** Setting instances must be treated as read-only (immutable or effectively immutable) once loaded.
- **Typed Parsing:** All values parsed from environment variables must use explicit parser helpers to handle booleans, integers, lists, and nested objects.

## Environment Resolution Order

Settings resolution follows a strict priority:
1. **Shell Environment:** Active shell variables win.
2. **Environment Files:** `.env` values are fallback.
3. **Defaults:** Hardcoded dataclass field defaults are the final fallback.

## Clean Contract Principles

We adhere to a "no placeholder" configuration contract:
- **No Unused Knobs:** Do not add environment variables or settings fields for "future" work. If a setting is not actively consumed in the code, it must be removed.
- **No Silent Placeholders:** If a feature is removed or disabled permanently, its configuration parameters must be scrubbed from `src/app/lib/settings/` and default `.env` files.

## Wired Configuration Groups

Settings are segmented into logical groups:
- **App Settings (`_app.py`):** Server host, port, debug mode, log level, allowed CORS origins.
- **Database Settings (`_database.py`):** DSN credentials, pool sizes, `ORACLE_AGENT_IN_MEMORY`, `ORACLE_LITESTAR_SESSION_IN_MEMORY`, and dedicated `get_queue_config()` pool.
- **AI Settings (`_ai.py`):** Vertex AI project ID, location, default chat model (`gemini-3.8-flash`), default embedding model (`gemini-embedding-2`), dimensions (`3072`).
- **Vite/Assets Settings (`_vite.py`):** Path configurations, static folders, Vite dev server port.
- **Maps Settings (`_maps.py`):** `MAPS_ENABLE_EMBED` and `GOOGLE_MAPS_EMBED_API_KEY`.
- **MCP Settings (`_mcp.py`):** `MCP_ENABLED`, `A2A_ENABLED`, optional `MCP_API_KEY` header guard.
- **Queue Settings (`_queue.py`):** `QUEUE_ENABLED`, `QUEUE_BACKEND`, `QUEUE_EXECUTION_BACKEND`, `QUEUE_WAKEUP_MODE`, `QUEUE_CONCURRENCY`, `QUEUE_POLL_INTERVAL`, `ORACLE_QUEUE_IN_MEMORY`.
