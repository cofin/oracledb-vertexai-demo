# Application Configuration & Settings Guide

This guide details the settings contract, environment variables parsing, and configuration structure.

## Settings Architecture

Configuration uses a dataclass-based structure under `src/app/lib/settings.py` (exposed as settings structures).
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
- **No Silent Placeholders:** If a feature is removed or disabled permanently, its configuration parameters must be scrubbed from `settings.py` and default `.env` files.

## Wired Configuration Groups

Settings are segmented into logical groups:
- **App Settings:** Server host, port, debug mode, log level.
- **Database Settings:** DSN credentials, pool sizes, extension flags (`ADK_ENABLE_MEMORY`, `ADK_IN_MEMORY`, `LITESTAR_SESSION_IN_MEMORY`).
- **AI Settings:** Vertex AI project ID, location, default model, default embedding model, dimensions.
- **Vite/Assets Settings:** Path configurations, static folders, Vite dev server port.
- **Maps Settings:** `MAPS_ENABLE_EMBED` and `GOOGLE_MAPS_EMBED_API_KEY`. These are read in `build_security_headers` to determine CSP permissions.
