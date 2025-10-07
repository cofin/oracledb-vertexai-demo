# Vertex AI Integration Guide (2025 Patterns)

Comprehensive guide to integrating Google Vertex AI with Oracle Database 23ai for embeddings, generation, and AI-powered search using the latest 2025 SDK patterns.

## Table of Contents

- [Overview](#overview)
- [Quick Reference](#quick-reference)
- [SDK Setup](#sdk-setup)
- [Text Embeddings (text-embedding-005)](#text-embeddings-text-embedding-005)
- [Content Generation (Gemini)](#content-generation-gemini)
- [Oracle Integration](#oracle-integration)
- [Caching Strategies](#caching-strategies)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [Migration from Legacy Patterns](#migration-from-legacy-patterns)
- [Troubleshooting](#troubleshooting)

## Overview

Google Vertex AI provides state-of-the-art AI capabilities for this application:

**Key Components**:
- **text-embedding-005**: Latest embedding model with task-type optimization
- **Gemini 2.5 Pro**: Advanced language model for generation
- **Vertex AI SDK**: Official Python SDK for Vertex AI services
- **Oracle Vector Search**: Native VECTOR type for storing embeddings

**Architecture Flow**:
```
User Query
    ↓
Vertex AI (text-embedding-005)
    ↓ [768-dim vector]
Oracle Vector Search (COSINE similarity)
    ↓ [Top-K products]
Vertex AI (Gemini 2.5)
    ↓ [Personalized response]
User
```

**This Guide Uses 2025 Patterns**:
- ✅ Vertex AI SDK (not google-generativeai)
- ✅ text-embedding-005 (not text-embedding-004)
- ✅ Task type specification (RETRIEVAL_QUERY vs RETRIEVAL_DOCUMENT)
- ✅ Modern authentication patterns
- ✅ Production-ready error handling

## Quick Reference

| Operation | Code | Task Type |
|-----------|------|-----------|
| Initialize SDK | `vertexai.init(project=PROJECT_ID, location=LOCATION)` | - |
| Get embedding model | `TextEmbeddingModel.from_pretrained("text-embedding-005")` | - |
| Embed document | `model.get_embeddings(texts=[doc], task_type="RETRIEVAL_DOCUMENT")` | RETRIEVAL_DOCUMENT |
| Embed query | `model.get_embeddings(texts=[query], task_type="RETRIEVAL_QUERY")` | RETRIEVAL_QUERY |
| Generate content | `GenerativeModel("gemini-2.5-pro").generate_content(prompt)` | - |
| Stream content | `model.generate_content(prompt, stream=True)` | - |
| Get vector | `embeddings[0].values` | - |

## SDK Setup

### Installation

```bash
# Install Vertex AI SDK with all features
pip install "google-cloud-aiplatform[all]>=1.101.0"
```

**Package includes**:
- Vertex AI core SDK
- Generative models (Gemini)
- Language models (embeddings)
- Agent Development Kit (ADK) components

### Initialization

```python
import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel

# Initialize Vertex AI
vertexai.init(
    project="your-project-id",
    location="us-central1"  # Choose appropriate region
)
```

**Location Options**:
- `us-central1`: US (Iowa)
- `us-east4`: US (Virginia)
- `europe-west4`: Europe (Netherlands)
- `asia-southeast1`: Asia (Singapore)

**Best Practice**: Store configuration in settings:
```python
# app/lib/settings.py
class GoogleSettings:
    GOOGLE_PROJECT_ID: str = "your-project"
    GOOGLE_LOCATION: str = "us-central1"

# app/services/vertex_ai/config.py
import vertexai
from app.lib.settings import get_settings

def init_vertex_ai():
    """Initialize Vertex AI SDK."""
    settings = get_settings()
    vertexai.init(
        project=settings.google.GOOGLE_PROJECT_ID,
        location=settings.google.GOOGLE_LOCATION
    )
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

vertexai.init(project=PROJECT_ID, location=LOCATION)
```

**Option 3: Explicit Credentials**

```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    "/path/to/service-account-key.json"
)

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    credentials=credentials
)
```

## Text Embeddings (text-embedding-005)

### Model Overview

**text-embedding-005** features:
- **768-dimensional vectors** (default, efficient)
- **3072-dimensional vectors** (optional, higher quality)
- **Task-type optimization**: Different embeddings for queries vs documents
- **Better performance** than text-embedding-004
- **Based on Gecko research**: State-of-the-art retrieval

### Task Types

**Critical**: Use correct task type for optimal results!

| Task Type | Use Case | Example |
|-----------|----------|---------|
| `RETRIEVAL_QUERY` | User search queries | "light roast coffee from Ethiopia" |
| `RETRIEVAL_DOCUMENT` | Documents to index | Product descriptions, articles |
| `SEMANTIC_SIMILARITY` | Similarity comparison | Duplicate detection |
| `CLASSIFICATION` | Text classification | Category assignment |
| `CLUSTERING` | Document grouping | Topic clustering |
| `QUESTION_ANSWERING` | Q&A optimization | FAQ systems |
| `FACT_VERIFICATION` | Fact checking | Claim validation |
| `CODE_RETRIEVAL_QUERY` | Code search | Function search queries |

### Basic Usage

```python
from vertexai.language_models import TextEmbeddingModel

# Get model
model = TextEmbeddingModel.from_pretrained("text-embedding-005")

# Embed a document (for indexing)
doc_embeddings = model.get_embeddings(
    texts=["Ethiopian Yirgacheffe coffee with floral notes"],
    task_type="RETRIEVAL_DOCUMENT",
    output_dimensionality=768  # Optional: 768 or 3072
)

# Access vector
doc_vector = doc_embeddings[0].values  # list[float] of length 768
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

embeddings = model.get_embeddings(
    texts=texts,
    task_type="RETRIEVAL_DOCUMENT"
)

# Process results
for i, embedding in enumerate(embeddings):
    print(f"Text {i}: {len(embedding.values)} dimensions")
    vector = embedding.values  # list[float]
```

**Batch Size Guidelines**:
- Maximum: 250 texts per request
- Recommended: 20-50 texts per request
- Larger batches: Use async processing

### Query vs Document Embeddings

**IMPORTANT**: Always use `RETRIEVAL_QUERY` for search queries and `RETRIEVAL_DOCUMENT` for indexed content!

```python
class EmbeddingService:
    def __init__(self):
        self.model = TextEmbeddingModel.from_pretrained("text-embedding-005")

    def embed_document(self, text: str) -> list[float]:
        """Embed document for indexing (RETRIEVAL_DOCUMENT)."""
        embeddings = self.model.get_embeddings(
            texts=[text],
            task_type="RETRIEVAL_DOCUMENT"
        )
        return embeddings[0].values

    def embed_query(self, query: str) -> list[float]:
        """Embed user query for search (RETRIEVAL_QUERY)."""
        embeddings = self.model.get_embeddings(
            texts=[query],
            task_type="RETRIEVAL_QUERY"
        )
        return embeddings[0].values
```

**Usage**:
```python
service = EmbeddingService()

# Index products (use RETRIEVAL_DOCUMENT)
product_vector = service.embed_document(
    "Ethiopian Yirgacheffe: bright floral notes with citrus"
)

# Search (use RETRIEVAL_QUERY)
query_vector = service.embed_query(
    "light roast coffee from Ethiopia"
)
```

### Output Dimensionality

Choose dimension based on use case:

```python
# 768 dimensions (default, balanced)
embeddings_768 = model.get_embeddings(
    texts=["text"],
    task_type="RETRIEVAL_DOCUMENT",
    output_dimensionality=768  # Faster, smaller storage
)

# 3072 dimensions (higher quality)
embeddings_3072 = model.get_embeddings(
    texts=["text"],
    task_type="RETRIEVAL_DOCUMENT",
    output_dimensionality=3072  # Better accuracy, larger storage
)
```

**Trade-offs**:
- **768 dimensions**: Faster, less storage, good for most use cases
- **3072 dimensions**: Better accuracy, more storage, slower queries

**Recommendation for this app**: Use 768 dimensions (sufficient for product search)

### Integration with Oracle

Store embeddings in Oracle VECTOR columns:

```python
import array
import oracledb
from vertexai.language_models import TextEmbeddingModel

# Get embedding
model = TextEmbeddingModel.from_pretrained("text-embedding-005")
embeddings = model.get_embeddings(
    texts=["Product description"],
    task_type="RETRIEVAL_DOCUMENT"
)
vector_values = embeddings[0].values  # list[float]

# Convert to Oracle VECTOR format
vector_array = array.array('f', vector_values)  # float32

# Insert into Oracle
cursor.execute(
    """
    INSERT INTO products (name, description, embedding)
    VALUES (:name, :description, :embedding)
    """,
    {
        "name": "Ethiopian Yirgacheffe",
        "description": "Bright and floral",
        "embedding": vector_array
    }
)
```

## Content Generation (Gemini)

### Model Selection

**Gemini Model Options**:

| Model | Use Case | Context | Speed |
|-------|----------|---------|-------|
| `gemini-2.5-pro` | Complex reasoning, long context | 1M tokens | Slower |
| `gemini-2.5-flash` | Fast responses, cost-effective | 32K tokens | Fast |
| `gemini-2.0-flash` | Real-time applications | 32K tokens | Very fast |

**Recommendation**: Use `gemini-2.5-flash` for product recommendations (sufficient quality, fast)

### Basic Generation

```python
from vertexai.generative_models import GenerativeModel

# Initialize model
model = GenerativeModel("gemini-2.5-flash")

# Generate content
response = model.generate_content("Why is sky blue?")
print(response.text)
```

### Structured Prompts

```python
# Prompt with system instructions
model = GenerativeModel(
    "gemini-2.5-flash",
    system_instruction="""You are a friendly coffee expert for Cymbal Coffee.
    Provide short, helpful recommendations (1-3 sentences).
    Focus on practical advice for coffee selection."""
)

response = model.generate_content(
    "What's a good light roast for beginners?"
)
```

### Generation Configuration

Control generation parameters:

```python
from vertexai.generative_models import GenerationConfig

model = GenerativeModel("gemini-2.5-flash")

response = model.generate_content(
    "Recommend a coffee",
    generation_config=GenerationConfig(
        temperature=0.7,      # 0.0-1.0, higher = more creative
        top_p=0.95,           # Nucleus sampling
        top_k=40,             # Top-K sampling
        max_output_tokens=256  # Limit response length
    )
)
```

**Parameter Guidelines**:
- **temperature**:
  - `0.0-0.3`: Factual, deterministic
  - `0.4-0.7`: Balanced (recommended)
  - `0.8-1.0`: Creative, varied
- **max_output_tokens**:
  - Short responses: 128-256
  - Medium responses: 512-1024
  - Long responses: 2048-4096

### Streaming Responses

Stream content for real-time UI updates:

```python
model = GenerativeModel("gemini-2.5-flash")

# Stream response
stream = model.generate_content(
    "Recommend 3 coffee products",
    stream=True
)

# Process chunks
for chunk in stream:
    print(chunk.text, end="", flush=True)
```

**Async Streaming** (for async applications):
```python
async def stream_response(prompt: str):
    model = GenerativeModel("gemini-2.5-flash")

    # Async streaming
    async for chunk in model.generate_content_async(
        prompt,
        stream=True
    ):
        yield chunk.text
```

### Chat with Context

Multi-turn conversations:

```python
model = GenerativeModel("gemini-2.5-flash")

# Start chat
chat = model.start_chat()

# Send messages
response1 = chat.send_message("What's a good light roast?")
print(response1.text)

response2 = chat.send_message("What about medium roast?")
print(response2.text)

# Chat maintains conversation history
```

### RAG Pattern (Retrieval-Augmented Generation)

Combine vector search with generation:

```python
async def rag_query(user_query: str) -> str:
    """RAG pattern: Search → Generate."""

    # 1. Create query embedding
    embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    query_embeddings = embedding_model.get_embeddings(
        texts=[user_query],
        task_type="RETRIEVAL_QUERY"
    )
    query_vector = query_embeddings[0].values

    # 2. Search Oracle with vector similarity
    results = await search_products(query_vector, k=5)

    # 3. Build context from results
    context = "\n".join([
        f"- {r['name']}: {r['description']}"
        for r in results
    ])

    # 4. Generate response with context
    gen_model = GenerativeModel(
        "gemini-2.5-flash",
        system_instruction="You are a coffee expert. Use the context to answer."
    )

    prompt = f"""
    Context (relevant products):
    {context}

    User query: {user_query}

    Provide a helpful recommendation based on the products above.
    """

    response = gen_model.generate_content(prompt)
    return response.text
```

## Oracle Integration

### Complete Service Implementation

```python
import array
import time
from typing import Any

import oracledb
import structlog
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel, GenerationConfig

logger = structlog.get_logger()


class VertexAIService:
    """Vertex AI service with text-embedding-005 and Gemini 2.5."""

    def __init__(self):
        # Initialize models
        self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
        self.gen_model = GenerativeModel("gemini-2.5-flash")

    def create_document_embedding(self, text: str) -> list[float]:
        """Create embedding for document indexing."""
        try:
            embeddings = self.embedding_model.get_embeddings(
                texts=[text],
                task_type="RETRIEVAL_DOCUMENT"
            )
            return embeddings[0].values
        except Exception as e:
            logger.error("embedding_error", error=str(e))
            # Fallback to zero vector
            return [0.0] * 768

    def create_query_embedding(self, query: str) -> list[float]:
        """Create embedding for search query."""
        try:
            embeddings = self.embedding_model.get_embeddings(
                texts=[query],
                task_type="RETRIEVAL_QUERY"
            )
            return embeddings[0].values
        except Exception as e:
            logger.error("embedding_error", error=str(e))
            return [0.0] * 768

    async def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 256
    ) -> str:
        """Generate content with Gemini."""
        try:
            response = await self.gen_model.generate_content_async(
                contents=prompt,
                generation_config=GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )
            return response.text
        except Exception as e:
            logger.error("generation_error", error=str(e))
            return f"Error generating response: {str(e)}"


class OracleVectorSearchService:
    """Oracle vector search with Vertex AI embeddings."""

    def __init__(
        self,
        products_service: Any,
        vertex_ai_service: VertexAIService
    ):
        self.products_service = products_service
        self.vertex_ai = vertex_ai_service

    async def similarity_search(
        self,
        query: str,
        k: int = 5
    ) -> tuple[list[dict], dict]:
        """
        Perform vector similarity search.

        Returns:
            - list of products
            - timing data dict
        """
        start_time = time.time()

        # Create query embedding
        embedding_start = time.time()
        query_vector = self.vertex_ai.create_query_embedding(query)
        embedding_time = (time.time() - embedding_start) * 1000

        # Search Oracle
        oracle_start = time.time()
        vector_array = array.array('f', query_vector)

        async with self.products_service.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.description,
                    1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) as similarity
                FROM product p
                WHERE p.embedding IS NOT NULL
                ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
                FETCH FIRST :limit ROWS ONLY
                """,
                {
                    "query_vector": vector_array,
                    "limit": k
                }
            )

            oracle_time = (time.time() - oracle_start) * 1000

            products = [
                {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "similarity": float(row[3])
                }
                async for row in cursor
            ]

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
from typing import Optional
import hashlib
import oracledb


class EmbeddingCache:
    """Oracle-backed embedding cache."""

    def __init__(self, connection_pool):
        self.pool = connection_pool

    async def get_embedding(
        self,
        text: str,
        vertex_ai_service: VertexAIService
    ) -> tuple[list[float], bool]:
        """
        Get embedding from cache or generate new.

        Returns:
            - embedding vector
            - cache_hit boolean
        """
        # Create cache key
        cache_key = hashlib.sha256(text.encode()).hexdigest()

        # Try cache
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT embedding_vector
                    FROM embedding_cache
                    WHERE cache_key = :key
                        AND created_at > SYSTIMESTAMP - INTERVAL '7' DAY
                    """,
                    key=cache_key
                )
                row = await cursor.fetchone()

                if row:
                    # Cache hit
                    vector_bytes = row[0]
                    vector = array.array('f', vector_bytes).tolist()
                    return vector, True

        # Cache miss - generate new embedding
        vector = vertex_ai_service.create_query_embedding(text)

        # Store in cache
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                vector_array = array.array('f', vector)
                await cursor.execute(
                    """
                    INSERT INTO embedding_cache (cache_key, text, embedding_vector)
                    VALUES (:key, :text, :vector)
                    """,
                    key=cache_key,
                    text=text[:500],  # Truncate for storage
                    vector=vector_array
                )
                await conn.commit()

        return vector, False
```

**Cache Table Schema**:
```sql
CREATE TABLE embedding_cache (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cache_key VARCHAR2(64) UNIQUE NOT NULL,
    text VARCHAR2(500),
    embedding_vector VECTOR(768, FLOAT32) NOT NULL,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    accessed_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE INDEX idx_cache_key ON embedding_cache(cache_key);
CREATE INDEX idx_cache_created ON embedding_cache(created_at);
```

### Response Cache

Cache generated responses:

```python
import json
from datetime import datetime, timedelta


class ResponseCache:
    """Cache for generated responses."""

    def __init__(self, connection_pool):
        self.pool = connection_pool

    async def get_cached_response(
        self,
        cache_key: str,
        user_id: str
    ) -> Optional[dict]:
        """Get cached response if available."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT response_data, created_at
                    FROM response_cache
                    WHERE cache_key = :key
                        AND user_id = :user_id
                        AND created_at > SYSTIMESTAMP - INTERVAL '5' MINUTE
                    """,
                    key=cache_key,
                    user_id=user_id
                )
                row = await cursor.fetchone()

                if row:
                    response_data = json.loads(row[0])
                    return response_data

        return None

    async def cache_response(
        self,
        cache_key: str,
        response_data: dict,
        user_id: str,
        ttl_minutes: int = 5
    ):
        """Store response in cache."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    MERGE INTO response_cache rc
                    USING (SELECT :key as cache_key, :user_id as user_id FROM dual) src
                    ON (rc.cache_key = src.cache_key AND rc.user_id = src.user_id)
                    WHEN MATCHED THEN
                        UPDATE SET
                            response_data = :data,
                            created_at = SYSTIMESTAMP
                    WHEN NOT MATCHED THEN
                        INSERT (cache_key, user_id, response_data)
                        VALUES (:key, :user_id, :data)
                    """,
                    key=cache_key,
                    user_id=user_id,
                    data=json.dumps(response_data)
                )
                await conn.commit()
```

## Error Handling

### Robust Error Handling Pattern

```python
from google.api_core import exceptions as google_exceptions
from google.api_core import retry
import time


class VertexAIServiceRobust:
    """Vertex AI service with comprehensive error handling."""

    def __init__(self):
        self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
        self.gen_model = GenerativeModel("gemini-2.5-flash")

    @retry.Retry(
        initial=1.0,
        maximum=10.0,
        multiplier=2.0,
        predicate=retry.if_exception_type(
            google_exceptions.ResourceExhausted,  # Rate limit
            google_exceptions.ServiceUnavailable,  # Service down
            google_exceptions.DeadlineExceeded    # Timeout
        )
    )
    def create_embedding_with_retry(self, text: str, task_type: str) -> list[float]:
        """Create embedding with automatic retry."""
        try:
            embeddings = self.embedding_model.get_embeddings(
                texts=[text],
                task_type=task_type
            )
            return embeddings[0].values

        except google_exceptions.InvalidArgument as e:
            # Bad request - don't retry
            logger.error("invalid_embedding_request", error=str(e), text=text[:50])
            return [0.0] * 768

        except google_exceptions.PermissionDenied as e:
            # Auth error - don't retry
            logger.error("embedding_auth_error", error=str(e))
            return [0.0] * 768

        except google_exceptions.ResourceExhausted as e:
            # Rate limit - retry with backoff
            logger.warning("rate_limit_hit", error=str(e))
            raise  # Retry decorator will handle

        except Exception as e:
            # Unknown error
            logger.error("embedding_unknown_error", error=str(e))
            return [0.0] * 768

    async def generate_content_safe(
        self,
        prompt: str,
        temperature: float = 0.7
    ) -> tuple[str, bool]:
        """
        Generate content with error handling.

        Returns:
            - response text
            - success boolean
        """
        try:
            response = await self.gen_model.generate_content_async(
                contents=prompt,
                generation_config=GenerationConfig(temperature=temperature)
            )
            return response.text, True

        except google_exceptions.InvalidArgument as e:
            logger.error("invalid_generation_request", error=str(e))
            return "Invalid request. Please try a different query.", False

        except google_exceptions.ResourceExhausted as e:
            logger.warning("rate_limit_generation", error=str(e))
            time.sleep(2)  # Brief pause
            # Retry once
            try:
                response = await self.gen_model.generate_content_async(
                    contents=prompt,
                    generation_config=GenerationConfig(temperature=temperature)
                )
                return response.text, True
            except Exception:
                return "Service temporarily unavailable. Please try again.", False

        except Exception as e:
            logger.error("generation_error", error=str(e))
            return "An error occurred. Please try again.", False
```

### Rate Limit Handling

```python
import asyncio
from asyncio import Semaphore


class RateLimitedEmbedder:
    """Rate-limited embedding service."""

    def __init__(self, max_concurrent: int = 5):
        self.model = TextEmbeddingModel.from_pretrained("text-embedding-005")
        self.semaphore = Semaphore(max_concurrent)

    async def embed_batch(
        self,
        texts: list[str],
        task_type: str
    ) -> list[list[float]]:
        """Embed texts with rate limiting."""
        async with self.semaphore:
            try:
                embeddings = self.model.get_embeddings(
                    texts=texts,
                    task_type=task_type
                )
                return [e.values for e in embeddings]
            except google_exceptions.ResourceExhausted:
                # Rate limit hit - wait and retry
                await asyncio.sleep(2)
                embeddings = self.model.get_embeddings(
                    texts=texts,
                    task_type=task_type
                )
                return [e.values for e in embeddings]
```

## Performance Optimization

### Batch Processing

Process multiple embeddings efficiently:

```python
async def batch_embed_products(
    products: list[dict],
    batch_size: int = 20
) -> list[tuple[int, list[float]]]:
    """Batch embed product descriptions."""
    model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    results = []

    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        texts = [p["description"] for p in batch]

        # Batch embedding
        embeddings = model.get_embeddings(
            texts=texts,
            task_type="RETRIEVAL_DOCUMENT"
        )

        # Collect results
        for j, embedding in enumerate(embeddings):
            product_id = batch[j]["id"]
            vector = embedding.values
            results.append((product_id, vector))

        # Rate limit protection
        await asyncio.sleep(0.1)

    return results
```

### Parallel Generation

Generate multiple responses concurrently:

```python
async def parallel_generate(
    prompts: list[str],
    temperature: float = 0.7
) -> list[str]:
    """Generate responses in parallel."""
    model = GenerativeModel("gemini-2.5-flash")

    tasks = [
        model.generate_content_async(
            prompt,
            generation_config=GenerationConfig(temperature=temperature)
        )
        for prompt in prompts
    ]

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for response in responses:
        if isinstance(response, Exception):
            results.append(f"Error: {str(response)}")
        else:
            results.append(response.text)

    return results
```

### Monitoring Performance

```python
import time
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    embedding_time_ms: float
    oracle_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    cache_hits: int
    cache_misses: int


class MonitoredVertexAIService:
    """Vertex AI service with performance monitoring."""

    def __init__(self):
        self.model = TextEmbeddingModel.from_pretrained("text-embedding-005")
        self.metrics: list[PerformanceMetrics] = []

    def create_query_embedding(self, query: str) -> tuple[list[float], float]:
        """Create embedding and return timing."""
        start = time.time()
        embeddings = self.model.get_embeddings(
            texts=[query],
            task_type="RETRIEVAL_QUERY"
        )
        elapsed = (time.time() - start) * 1000  # ms
        return embeddings[0].values, elapsed

    def get_performance_stats(self) -> dict:
        """Get aggregated performance statistics."""
        if not self.metrics:
            return {}

        return {
            "avg_embedding_ms": sum(m.embedding_time_ms for m in self.metrics) / len(self.metrics),
            "avg_oracle_ms": sum(m.oracle_time_ms for m in self.metrics) / len(self.metrics),
            "avg_generation_ms": sum(m.generation_time_ms for m in self.metrics) / len(self.metrics),
            "cache_hit_rate": sum(m.cache_hits for m in self.metrics) / (
                sum(m.cache_hits + m.cache_misses for m in self.metrics) or 1
            )
        }
```

## Migration from Legacy Patterns

### Current Code (Legacy)

```python
# OLD: google-generativeai
import google.generativeai as genai

genai.configure(api_key=settings.app.GOOGLE_PROJECT_ID)
model = genai.GenerativeModel("gemini-pro")

# OLD: text-embedding-004 without task types
response = await genai.embed_content_async(
    model="text-embedding-004",
    content=text,
    task_type="retrieval_document"  # Wrong format
)
embedding = response["embedding"]
```

### New Code (2025 Pattern)

```python
# NEW: Vertex AI SDK
import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel

# Initialize
vertexai.init(project=PROJECT_ID, location=LOCATION)

# NEW: text-embedding-005 with proper task types
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
embeddings = embedding_model.get_embeddings(
    texts=[text],
    task_type="RETRIEVAL_DOCUMENT"  # Correct enum
)
vector = embeddings[0].values

# Generation
gen_model = GenerativeModel("gemini-2.5-flash")
response = await gen_model.generate_content_async(prompt)
```

### Migration Checklist

- [ ] Replace `google.generativeai` with `vertexai`
- [ ] Update to `text-embedding-005`
- [ ] Add task type specification (`RETRIEVAL_QUERY` vs `RETRIEVAL_DOCUMENT`)
- [ ] Update model names (`gemini-2.5-flash`, `gemini-2.5-pro`)
- [ ] Add `output_dimensionality` parameter (optional)
- [ ] Update authentication to use `vertexai.init()`
- [ ] Update error handling for new SDK exceptions
- [ ] Test embedding cache compatibility
- [ ] Update integration tests

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
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```

**Solutions**:
1. Implement exponential backoff retry
2. Reduce batch size
3. Add delays between requests
4. Use caching to reduce API calls
5. Request quota increase from Google Cloud

### Issue: Slow Embedding Generation

**Symptom**: Embeddings taking >500ms per request

**Solutions**:
1. **Use batch embeddings** (20-50 texts per request)
2. **Enable caching** for repeated queries
3. **Choose correct region** (minimize latency)
4. **Use 768 dimensions** instead of 3072

### Issue: Incorrect Vector Similarity

**Symptom**: Search returns irrelevant results

**Solutions**:
1. **Check task type**: Use `RETRIEVAL_QUERY` for queries, `RETRIEVAL_DOCUMENT` for documents
2. **Verify normalization**: Vectors should be normalized for COSINE distance
3. **Check index type**: HNSW for better accuracy, IVFFlat for faster queries
4. **Rebuild index**: `ALTER INDEX idx_embedding REBUILD ONLINE;`

## See Also

- [Oracle Vector Search Guide](oracle-vector-search.md) - Vector storage and search
- [ADK Agent Patterns](adk-agent-patterns.md) - Agent orchestration with ADK
- [Oracle Performance Guide](oracle-performance.md) - Performance optimization
- [Architecture Overview](architecture.md) - System design

## Resources

- Vertex AI Python SDK: https://github.com/googleapis/python-aiplatform
- text-embedding-005 docs: https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings
- Gemini models: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models
- Google Cloud authentication: https://cloud.google.com/docs/authentication/application-default-credentials
