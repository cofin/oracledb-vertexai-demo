# Phase 1 Complete: Dependencies & Configuration

## Summary

Phase 1 has been successfully completed. All configuration and dependency changes are in place to support the ADK Runner migration.

## Changes Made

### 1. Updated `pyproject.toml`
- **Removed**: `google-generativeai>=0.3.2` (legacy SDK)
- **Added**:
  - `google-cloud-aiplatform` (for Vertex AI initialization)
  - `litestar-mcp` (for MCP support)
  - `msgspec` (for schema handling)
  - `rich-click` (for CLI)
  - Updated `numpy>=2.3.3`
- **Updated entry point**: Changed from `app.__init__:run_cli` to `app.__main__:run_cli`

### 2. Created `app/__main__.py`
- Standard Litestar CLI entry point
- Matches Postgres repository pattern
- Handles environment setup and plugin loading

### 3. Updated `app/lib/settings.py`
- **Added `VertexAISettings`**:
  - PROJECT_ID, LOCATION, EMBEDDING_MODEL, CHAT_MODEL
  - Cache TTL and prefix settings
  - Streaming buffer/timeout configuration
- **Added `AgentSettings`**:
  - Intent and vector search thresholds
  - Conversation history limits
  - Session expiration settings
- **Added `CacheSettings`**:
  - Response TTL
  - Embedding cache toggle
- **Updated `Settings`**: Now includes `vertex_ai`, `agent`, and `cache` fields

### 4. Updated `app/config.py`
- **Added**: `service_locator = ServiceLocator()` for dependency injection
- **Added**: `db_manager.load_sql_files()` for SQL file loading
- **Added**: Logging configuration for ADK and GenAI SDKs:
  - `google.adk`
  - `google.genai`
  - `google_genai`
  - `google_genai.types`
  - `sqlspec` and `sqlglot`
- **Note**: ADK extension config was already present in `DatabaseSettings.create_config()`

### 5. Created `app/lib/context.py`
- Thread-safe context variable storage
- Functions: `get_timing_context()`, `set_timing_data()`, `clear_timing_context()`, `reset_timing_context()`
- Used by ADK tools to store timing data across async operations

### 6. Created `app/services/locator.py`
- Service locator pattern for dependency injection
- Auto-wiring based on type hints
- Special handling for:
  - `VertexAIService` (singleton with CacheService injection)
  - `IntentService` (with ExemplarService and VertexAI dependencies)
  - `AgentToolsService` (with Product, Metrics, Intent, VertexAI, Store services)
- Supports transient (session-scoped) and singleton services

## Verification Steps

### 1. Install Dependencies
```bash
cd /home/cody/code/g/oracledb-vertexai-demo
uv sync
```

### 2. Verify Imports
```bash
uv run python -c "
import google.genai
import google.adk
from app.lib.settings import get_settings
settings = get_settings()
print(f'Vertex AI Project: {settings.vertex_ai.PROJECT_ID}')
print(f'Chat Model: {settings.vertex_ai.CHAT_MODEL}')
print(f'Embedding Model: {settings.vertex_ai.EMBEDDING_MODEL}')
print('✅ Phase 1 configuration verified')
"
```

### 3. Check ADK Extension Config
The ADK extension configuration is already in place in `DatabaseSettings.create_config()`:
- Session table: `adk_sessions`
- Events table: `adk_events`

When migrations are run, these tables will be created automatically.

## Next Phase: Phase 2 - Modernize VertexAI Service

Phase 2 will modernize `app/services/vertex_ai.py` to use the `google.genai` SDK:

1. Replace `google.generativeai` imports with `google.genai`
2. Use `google.genai.Client()` for embeddings
3. Use async methods: `aio.models.embed_content()`, `aio.models.generate_content_stream()`
4. Integrate with `app.lib.settings.VertexAISettings`
5. Keep Oracle-specific caching logic

## Files Modified in Phase 1

- ✅ `pyproject.toml`
- ✅ `app/__main__.py` (new)
- ✅ `app/lib/settings.py`
- ✅ `app/config.py`
- ✅ `app/lib/context.py` (new)
- ✅ `app/services/locator.py` (new)

## Phase 1 Status: COMPLETE ✅
