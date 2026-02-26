# Vertex AI Integration Guide (Modern Architecture - 2025)

Comprehensive guide to integrating Google Vertex AI with Oracle Database 23ai using the **modern `google.genai` SDK** and **Google ADK Runner** for embeddings, generation, and AI-powered agent orchestration.

> **Last Updated**: 2025-10-10
> **Status**: ✅ Current (reflects modern google.genai SDK)
> **Architecture**: Google ADK Runner + SQLSpec + google.genai

## Table of Contents

- [Overview](#overview)
- [Quick Reference](#quick-reference)
- [SDK Setup](#sdk-setup)
- [Text Embeddings (google.genai)](#text-embeddings-google-genai)
- [Content Generation (Gemini)](#content-generation-gemini)
- [Google ADK Integration](#google-adk-integration)
- [Oracle Integration](#oracle-integration)
- [Caching Strategies](#caching-strategies)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

## Overview

This application uses **modern Google GenAI SDK patterns** with the Google Agent Development Kit (ADK) for sophisticated agent orchestration:

**Key Components**:

- **google.genai SDK**: Modern async SDK for Vertex AI services
- **Google ADK Runner**: Production-ready agent orchestration framework
- **OracleAsyncADKStore**: SQLSpec adapter for persisting ADK sessions/events
- **Gemini 2.5 Flash**: Advanced language model for generation
- **Oracle Vector Search**: Native VECTOR type for storing embeddings

**Architecture Flow**:

```
User Query
    ↓
ADKOrchestrator (orchestrates agents)
    ↓
Google ADK Runner
    ↓ [manages agent lifecycle]
CoffeeAssistantAgent (LlmAgent)
    ├─→ classify_intent tool
    ├─→ search_products_by_vector tool
    └─→ VertexAIService (embeddings)
    ↓
google.genai.Client()
    ├─→ embed_content() [768-dim vector]
    └─→ generate_content_stream() [streaming response]
    ↓
Oracle Database 23ai
    ├─→ Vector Search (COSINE similarity)
    ├─→ ADK Sessions (adk_sessions table)
    └─→ ADK Events (adk_events table)
    ↓
User
```

**This Guide Uses 2025 Modern Patterns**:

- ✅ `google.genai` SDK (NOT `google-generativeai`)
- ✅ `genai.Client()` with async patterns
- ✅ `embed_content()` method (NOT `create_embedding()`)
- ✅ `generate_content_stream()` for streaming
- ✅ Google ADK Runner for agent orchestration
- ✅ OracleAsyncADKStore for session persistence
- ✅ SQLSpec for database operations

## Quick Reference

| Operation        | Code                                                                        | Notes                           |
| ---------------- | --------------------------------------------------------------------------- | ------------------------------- |
| Initialize SDK   | `genai.Client()`                                                            | Async client for all operations |
| Embed content    | `client.aio.models.embed_content(model=MODEL, contents=text)`               | Returns `EmbedContentResponse`  |
| Get vector       | `response.embeddings[0].values`                                             | List of float values            |
| Generate content | `client.aio.models.generate_content_stream(model=MODEL, contents=messages)` | Async streaming                 |
| ADK Runner       | `Runner(agent=Agent, session_service=service)`                              | Orchestrates agents             |
| ADK Session      | `SQLSpecSessionService(OracleAsyncADKStore(config))`                        | Persists to Oracle              |

## SDK Setup

### Installation

```bash
# Install modern Google GenAI SDK
pip install "google-genai>=1.0.0"

# Install Google ADK (includes genai)
pip install "google-cloud-aiplatform[adk]>=1.101.0"

# Install SQLSpec with ADK support
pip install "sqlspec[adk,oracledb]"
```

**Package includes**:

- Modern `google.genai` client
- Google ADK framework (Runner, LlmAgent, tools)
- SQLSpec ADK adapter (OracleAsyncADKStore)
- Async patterns throughout

### Initialization

```python
from google import genai
from google.cloud import aiplatform

# Initialize Vertex AI platform
aiplatform.init(
    project="your-project-id",
    location="us-central1"
)

# Create Google GenAI client
client = genai.Client()
```

**Location Options**:

- `us-central1`: US (Iowa)
- `us-east4`: US (Virginia)
- `europe-west4`: Europe (Netherlands)
- `asia-southeast1`: Asia (Singapore)

**Best Practice**: Store configuration in settings:

```python
# app/lib/settings.py
class VertexAISettings:
    PROJECT_ID: str = "your-project"
    LOCATION: str = "us-central1"
    EMBEDDING_MODEL: str = "text-embedding-004"
    CHAT_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_DIMENSIONS: int = 768

# app/services/vertex_ai.py
from google import genai
from google.cloud import aiplatform
from app.lib.settings import get_settings

class VertexAIService:
    def __init__(self):
        settings = get_settings()
        aiplatform.init(
            project=settings.vertex_ai.PROJECT_ID,
            location=settings.vertex_ai.LOCATION
        )
        self._genai_client = genai.Client()
```

### Authentication

**Option 1: Application Default Credentials (Recommended)**

```bash
# Local development
gcloud auth application-default login

# Production (automatic in Google Cloud)
# Uses service account attached to compute resource
```

**Option 2: Service Account Key File**

```python
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/service-account-key.json"

from google.cloud import aiplatform
aiplatform.init(project=PROJECT_ID, location=LOCATION)
```

## Text Embeddings (google.genai)

### Model Overview

**text-embedding-004** features:

- **768-dimensional vectors** (standard)
- **Task-type optimization**: RETRIEVAL_QUERY vs RETRIEVAL_DOCUMENT
- **Async API** via `genai.Client()`

### Basic Usage

```python
from google import genai

# Create client
client = genai.Client()

# Embed a document (for indexing)
response = await client.aio.models.embed_content(
    model="text-embedding-004",
    contents="Ethiopian Yirgacheffe coffee with floral notes"
)

# Access vector
embedding_vector = list(response.embeddings[0].values)  # list[float] of length 768
```

### Batch Embeddings

Embed multiple texts efficiently:

```python
# Embed multiple documents
texts = [
    "Ethiopian Yirgacheffe - bright and floral",
    "Colombian Supremo - balanced and smooth",
    "Brazilian Santos - nutty and chocolatey"
]

response = await client.aio.models.embed_content(
    model="text-embedding-004",
    contents=texts
)

# Process results
embeddings = [list(emb.values) for emb in response.embeddings]
```

**Batch Size Guidelines**:

- Recommended: 5-20 texts per request (rate limiting)
- Use delays between batches for large datasets

### Integration with Oracle

Store embeddings in Oracle VECTOR columns:

```python
from google import genai

# Get embedding
client = genai.Client()
response = await client.aio.models.embed_content(
    model="text-embedding-004",
    contents="Product description"
)
vector_values = list(response.embeddings[0].values)  # list[float]

# Insert into Oracle via SQLSpec
await driver.insert(
    "product",
    {
        "name": "Ethiopian Yirgacheffe",
        "description": "Bright and floral",
        "embedding": vector_values  # SQLSpec handles conversion
    }
)
```

## Content Generation (Gemini)

### Model Selection

**Gemini Model Options**:

| Model              | Use Case          | Context    | Speed  |
| ------------------ | ----------------- | ---------- | ------ |
| `gemini-2.5-pro`   | Complex reasoning | 1M tokens  | Slower |
| `gemini-2.5-flash` | Fast responses    | 32K tokens | Fast   |

**Recommendation**: Use `gemini-2.5-flash` for product recommendations

### Streaming Responses

Stream content for real-time UI updates:

```python
from google import genai

client = genai.Client()

# Stream response
async for chunk in await client.aio.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents=[{"role": "user", "parts": [{"text": "Recommend coffee"}]}],
    config=genai.types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=256
    )
):
    # Extract text from chunk
    if chunk.candidates:
        candidate = chunk.candidates[0]
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if part.text:
                    yield part.text
```

### Generation Configuration

```python
from google import genai

config = genai.types.GenerateContentConfig(
    temperature=0.7,      # 0.0-1.0, higher = more creative
    max_output_tokens=256  # Limit response length
)

async for chunk in await client.aio.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents=messages,
    config=config
):
    # Process chunks
    ...
```

**Parameter Guidelines**:

- **temperature**:
  - `0.0-0.3`: Factual, deterministic
  - `0.4-0.7`: Balanced (recommended)
  - `0.8-1.0`: Creative, varied

## Google ADK Integration

### ADK Architecture

This application uses **Google ADK Runner** for sophisticated agent orchestration:

```python
from google.adk import Runner
from google.adk.agents import LlmAgent
from sqlspec.extensions.adk import SQLSpecSessionService
from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore

# Create ADK store for Oracle persistence
store = OracleAsyncADKStore(config=db_config)
session_service = SQLSpecSessionService(store)

# Create ADK runner
runner = Runner(
    agent=CoffeeAssistantAgent,  # LlmAgent subclass
    app_name="coffee-assistant",
    session_service=session_service
)

# Run agent
events = runner.run_async(
    user_id="user123",
    session_id="session456",
    new_message=types.Content(
        role="user",
        parts=[types.Part(text="I want bold coffee")]
    )
)
```

### ADK Session Persistence

ADK sessions and events are persisted to Oracle via SQLSpec:

**Database Tables** (created by SQLSpec ADK extension):

- `adk_sessions`: Session metadata and state
- `adk_events`: Event history for each session

```python
# SQLSpec configuration
db_config = {
    "session_table": "adk_sessions",
    "events_table": "adk_events"
}

store = OracleAsyncADKStore(config=db)
session_service = SQLSpecSessionService(store)
```

### Agent Tools

Tools are Python functions exposed to ADK agents:

```python
from google.adk.tools import FunctionTool

async def search_products_by_vector(
    query: str,
    limit: int = 5,
    similarity_threshold: float = 0.7
) -> list[dict]:
    """Search products by vector similarity.

    Args:
        query: Search query text
        limit: Maximum number of results
        similarity_threshold: Minimum similarity score

    Returns:
        List of matching products with similarity scores
    """
    # Generate embedding
    embedding = await vertex_ai_service.get_text_embedding(query)

    # Search Oracle
    products = await driver.select(
        """
        SELECT p.id, p.name, p.description, p.price,
               VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) as distance
        FROM product p
        WHERE p.embedding IS NOT NULL
        ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
        FETCH FIRST :limit ROWS ONLY
        """,
        query_vector=embedding,
        limit=limit
    )

    return products

# Expose to agent
agent_tools = [
    FunctionTool(func=search_products_by_vector)
]
```

## Oracle Integration

### Complete Service Implementation

```python
from google import genai
from google.cloud import aiplatform
from sqlspec.adapters.oracledb.async_driver import OracleAsyncDriver

class VertexAIService:
    """Modern Vertex AI service using google.genai SDK."""

    def __init__(self):
        # Initialize Vertex AI
        aiplatform.init(
            project=settings.PROJECT_ID,
            location=settings.LOCATION
        )
        # Create GenAI client
        self._genai_client = genai.Client()

    async def get_text_embedding(
        self,
        text: str | list[str],
        model: str | None = None
    ) -> list[float] | list[list[float]]:
        """Generate text embedding(s) using modern SDK.

        Args:
            text: Text or list of texts to embed
            model: Optional model override

        Returns:
            Single embedding vector or list of vectors
        """
        model_name = model or settings.EMBEDDING_MODEL

        # Handle batch embeddings
        if isinstance(text, list):
            response = await self._genai_client.aio.models.embed_content(
                model=model_name,
                contents=text
            )
            return [list(emb.values) for emb in response.embeddings]

        # Single text embedding
        response = await self._genai_client.aio.models.embed_content(
            model=model_name,
            contents=text
        )
        return list(response.embeddings[0].values)

    async def generate_chat_response_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024
    ):
        """Generate streaming chat response."""
        model_name = model or settings.CHAT_MODEL

        # Convert messages to GenAI format
        formatted_messages = []
        for message in messages:
            role = "user" if message["role"] == "user" else "model"
            formatted_messages.append({
                "role": role,
                "parts": [{"text": message["content"]}]
            })

        # Generate streaming response
        async for chunk in await self._genai_client.aio.models.generate_content_stream(
            model=model_name,
            contents=formatted_messages,
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )
        ):
            # Extract text from chunk
            if chunk.candidates:
                candidate = chunk.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.text:
                            yield part.text

class OracleVectorSearchService:
    """Oracle vector search with Vertex AI embeddings."""

    def __init__(
        self,
        driver: OracleAsyncDriver,
        vertex_ai_service: VertexAIService
    ):
        self.driver = driver
        self.vertex_ai = vertex_ai_service

    async def similarity_search(
        self,
        query: str,
        k: int = 5
    ) -> tuple[list[dict], dict]:
        """Perform vector similarity search.

        Returns:
            - list of products
            - timing data dict
        """
        import time
        start_time = time.time()

        # Create query embedding
        embedding_start = time.time()
        query_vector = await self.vertex_ai.get_text_embedding(query)
        embedding_time = (time.time() - embedding_start) * 1000

        # Search Oracle (SQLSpec handles vector conversion)
        oracle_start = time.time()
        products = await self.driver.select(
            """
            SELECT
                p.id,
                p.name,
                p.description,
                p.price,
                VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) as distance
            FROM product p
            WHERE p.embedding IS NOT NULL
            ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
            FETCH FIRST :limit ROWS ONLY
            """,
            query_vector=query_vector,
            limit=k
        )
        oracle_time = (time.time() - oracle_start) * 1000

        total_time = (time.time() - start_time) * 1000
        timing = {
            "embedding_ms": embedding_time,
            "oracle_ms": oracle_time,
            "total_ms": total_time
        }

        return products, timing
```

## Caching Strategies

### Embedding Cache

Cache embeddings to reduce API calls:

```python
class CacheService:
    """Oracle-backed embedding cache."""

    async def get_cached_embedding(
        self,
        text: str,
        model: str
    ) -> dict | None:
        """Get cached embedding if available."""
        text_hash = hashlib.md5(text.encode()).hexdigest()

        cached = await self.driver.select_one(
            """
            SELECT embedding, created_at
            FROM embedding_cache
            WHERE text_hash = :hash AND model = :model
            """,
            hash=text_hash,
            model=model
        )

        if cached:
            return {
                "embedding": cached["embedding"],
                "cached_at": cached["created_at"]
            }
        return None

    async def set_cached_embedding(
        self,
        text: str,
        embedding: list[float],
        model: str
    ):
        """Store embedding in cache."""
        text_hash = hashlib.md5(text.encode()).hexdigest()

        await self.driver.insert(
            "embedding_cache",
            {
                "text_hash": text_hash,
                "embedding": embedding,
                "model": model
            }
        )
```

**Cache Table Schema**:

```sql
CREATE TABLE embedding_cache (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    text_hash VARCHAR2(255) NOT NULL,
    embedding VECTOR(768, FLOAT32) NOT NULL,
    model VARCHAR2(100) NOT NULL,
    hit_count NUMBER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT SYSTIMESTAMP,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    CONSTRAINT embedding_cache_uk UNIQUE (text_hash, model)
);
```

## Error Handling

### Robust Error Handling Pattern

```python
from google.genai import errors

class VertexAIServiceRobust:
    """Vertex AI service with comprehensive error handling."""

    async def get_text_embedding_safe(
        self,
        text: str
    ) -> tuple[list[float], bool]:
        """Get embedding with error handling.

        Returns:
            - embedding vector
            - success boolean
        """
        try:
            embedding = await self.get_text_embedding(text)
            return embedding, True

        except errors.ClientError as e:
            logger.error("embedding_client_error", error=str(e))
            return [0.0] * 768, False

        except errors.ServerError as e:
            logger.error("embedding_server_error", error=str(e))
            # Retry with backoff
            await asyncio.sleep(1)
            try:
                embedding = await self.get_text_embedding(text)
                return embedding, True
            except Exception:
                return [0.0] * 768, False

        except Exception as e:
            logger.error("embedding_unknown_error", error=str(e))
            return [0.0] * 768, False
```

## Performance Optimization

### Batch Processing

Process multiple embeddings efficiently:

```python
async def batch_embed_products(
    products: list[dict],
    batch_size: int = 5
) -> list[tuple[int, list[float]]]:
    """Batch embed product descriptions."""
    results = []

    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        texts = [p["description"] for p in batch]

        # Batch embedding
        embeddings = await vertex_ai_service.get_text_embedding(texts)

        # Collect results
        for j, embedding in enumerate(embeddings):
            product_id = batch[j]["id"]
            results.append((product_id, embedding))

        # Rate limit protection
        await asyncio.sleep(1)

    return results
```

## Troubleshooting

### Issue: Authentication Failed

**Symptom**:

```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

**Solution**:

```bash
# Set up Application Default Credentials
gcloud auth application-default login

# OR set service account key
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

### Issue: Rate Limit Errors

**Symptom**:

```
google.genai.errors.ServerError: 503 Service Unavailable
```

**Solutions**:

1. Implement exponential backoff retry
2. Reduce batch size (use 5 instead of 20)
3. Add delays between requests
4. Use caching to reduce API calls

### Issue: Slow Embedding Generation

**Symptom**: Embeddings taking >500ms per request

**Solutions**:

1. **Use batch embeddings** (5-20 texts per request)
2. **Enable caching** for repeated queries
3. **Choose correct region** (minimize latency)

## See Also

- [ADK Agent Patterns](adk-agent-patterns.md) - Google ADK orchestration
- [Oracle Vector Search Guide](oracle-vector-search.md) - Vector storage and search
- [SQLSpec Patterns](sqlspec-patterns.md) - Database service patterns
- [Architecture Overview](architecture.md) - System design

## Resources

- Google GenAI SDK: https://github.com/googleapis/python-genai
- Google ADK: https://github.com/googleapis/python-aiplatform
- SQLSpec ADK Extension: https://github.com/litestar-org/sqlspec
- Vertex AI documentation: https://cloud.google.com/vertex-ai/docs

## Changelog

### 2025-10-10

- Updated to reflect modern `google.genai` SDK (NOT `google-generativeai`)
- Added Google ADK Runner architecture
- Added OracleAsyncADKStore for session persistence
- Updated all code examples to use `genai.Client()` async patterns
- Added ADK tables documentation (adk_sessions, adk_events)
- Removed legacy `TextEmbeddingModel` patterns
- Updated method names: `get_text_embedding()`, `generate_content_stream()`

### 2025-01-15

- Initial version with Vertex AI SDK patterns
