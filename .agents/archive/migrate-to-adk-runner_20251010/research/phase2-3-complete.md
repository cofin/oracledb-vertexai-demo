# Phases 2-3 Complete: VertexAI Service & ADK Components

## Summary

Phases 2 and 3 have been successfully completed. The Oracle repository now uses the modern `google.genai` SDK and has full ADK Runner support matching the Postgres sister repository.

## Phase 2: Modernize VertexAI Service ✅

### Changes Made:

1. **Backed up legacy code**: `app/services/vertex_ai_legacy.py`
   - Original implementation preserved for reference
   - Uses deprecated `google.generativeai` SDK

2. **Modernized `app/services/vertex_ai.py`**:
   - **SDK Migration**:
     - ❌ Removed: `import google.generativeai as genai`
     - ✅ Added: `from google import genai` (modern SDK)
     - ✅ Added: `from google.cloud import aiplatform`

   - **Client Initialization**:
     ```python
     aiplatform.init(
         project=self.settings.vertex_ai.PROJECT_ID,
         location=self.settings.vertex_ai.LOCATION,
     )
     self._genai_client = genai.Client()
     ```

   - **Async Methods**:
     - `_genai_client.aio.models.embed_content()` for embeddings
     - `_genai_client.aio.models.generate_content_stream()` for chat

   - **Settings Integration**:
     - Uses `self.settings.vertex_ai.PROJECT_ID`
     - Uses `self.settings.vertex_ai.LOCATION`
     - Uses `self.settings.vertex_ai.EMBEDDING_MODEL`
     - Uses `self.settings.vertex_ai.CHAT_MODEL`

   - **Preserved Oracle Features**:
     - Embedding caching via `CacheService`
     - Batch embedding with rate limiting
     - Overloaded `get_text_embedding()` for single/batch
     - Cache status tracking

### Quality Standards Met:
- ✅ No defensive coding (hasattr/getattr)
- ✅ Proper type hints on all functions
- ✅ All imports at top of file
- ✅ Clean naming without workarounds
- ✅ Matches Postgres implementation exactly

## Phase 3: ADK Components ✅

### 3.1 Updated `app/services/adk/tool_service.py`

**Oracle-Specific SQL Queries**:

1. **Vector Search** (line 108-113):
   ```sql
   SELECT p.id, p.name, p.description, p.price,
          1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) as similarity
   FROM product p
   WHERE 1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) > :threshold
   ORDER BY similarity DESC
   FETCH FIRST :limit ROWS ONLY
   ```
   - ✅ Oracle `VECTOR_DISTANCE()` function
   - ✅ Named parameter binding (`:query_vector`, `:threshold`, `:limit`)
   - ✅ `FETCH FIRST` instead of PostgreSQL `LIMIT`

2. **Intent Classification** (line 175-185):
   ```sql
   WITH query_embedding AS (
       SELECT intent, phrase,
           1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) AS similarity,
           confidence_threshold,
           usage_count
       FROM intent_exemplar)
   SELECT intent, phrase, similarity, confidence_threshold, usage_count
   FROM query_embedding
   WHERE similarity > :min_threshold
   ORDER BY similarity DESC
   FETCH FIRST :limit ROWS ONLY
   ```
   - ✅ Oracle CTE syntax
   - ✅ Named parameter binding
   - ✅ `FETCH FIRST` clause

### 3.2 Verified `app/services/adk/tools.py`

- ✅ Already matches Postgres version exactly
- ✅ Uses `service_locator.get(AgentToolsService, session)`
- ✅ Proper session management with `db_manager.provide_session(db)`
- ✅ Stores timing data in context via `set_timing_data()`
- ✅ All tools return ADK-compatible types

### 3.3 Updated `app/services/adk/orchestrator.py`

**Key Changes**:
- ❌ Removed: `from sqlspec.adapters.asyncpg.adk.store import AsyncpgADKStore`
- ✅ Added: `from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore`
- ✅ Updated instantiation: `store = OracleAsyncADKStore(config=db)`

**Architecture**:
```python
class ADKOrchestrator:
    def __init__(self) -> None:
        store = OracleAsyncADKStore(config=db)
        self.session_service = SQLSpecSessionService(store)
        self.runner = Runner(
            agent=CoffeeAssistantAgent,
            app_name="coffee-assistant",
            session_service=self.session_service,
        )
```

**Features Preserved**:
- ✅ Session persistence via SQLSpec ADK store
- ✅ Retry logic for transient errors
- ✅ Fallback search when agent fails workflow
- ✅ Response caching
- ✅ Detailed timing tracking
- ✅ Metrics recording
- ✅ Markdown to HTML conversion

## Files Modified in Phases 2-3

### Phase 2:
- ✅ `app/services/vertex_ai.py` (modernized)
- ✅ `app/services/vertex_ai_legacy.py` (backup)

### Phase 3:
- ✅ `app/services/adk/tool_service.py` (Oracle SQL)
- ✅ `app/services/adk/tools.py` (verified)
- ✅ `app/services/adk/orchestrator.py` (Oracle ADK store)

## Database Schema Required

The ADK extension configuration (already in `app/lib/settings.py`) defines:
- **adk_sessions** table: Session state storage
- **adk_events** table: Event history storage

These will be created by SQLSpec migrations when `uv run app db upgrade` is executed.

## Next Phase: Phase 4 - Update Controllers

Controllers need to be updated to use `ADKOrchestrator` instead of direct `VertexAIService` calls.

**Files to update**:
- `app/server/controllers.py` (chat endpoint, streaming endpoint)

**Expected changes**:
```python
# Before:
vertex_service = request.app.state.vertex_ai_service
response, cache_hit = await vertex_service.chat_with_history(...)

# After:
orchestrator = ADKOrchestrator()
response = await orchestrator.process_request(
    query=data.message,
    user_id=user_id,
    session_id=session_id,
    persona=data.persona,
)
```

## Quality Checklist ✅

- ✅ No defensive coding patterns
- ✅ Clean naming without workarounds
- ✅ Proper type hints throughout
- ✅ All imports at module top
- ✅ Oracle named parameter binding (`:name`)
- ✅ SQLSpec service patterns followed
- ✅ Matches Postgres architecture
- ✅ No nested imports (except TYPE_CHECKING)

## Phases 2-3 Status: COMPLETE ✅
