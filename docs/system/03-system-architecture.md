# 🏗️ Complete System Architecture

## High-Level Architecture

```mermaid
graph TB
    subgraph "User Interface"
        A[Web Browser] --> B[HTMX + Tailwind UI]
        B --> C[Server-Sent Events]
    end

    subgraph "Application Layer"
        D[Litestar Web Framework]
        E[Intent Router]
        F[Recommendation Service]
        G[Session Manager]
        P[Persona Manager]
        Q[Embedding Cache]
    end

    subgraph "AI Layer"
        H[Vertex AI Service]
        I[Gemini 2.5 Flash]
        J[Text Embeddings 004]
    end

    subgraph "Data Layer"
        K[Oracle 23AI Database]
        L[Vector Store<br/>HNSW Index]
        M[Session Cache<br/>JSON + TTL]
        N[Response Cache<br/>In-Memory]
        O[Business Data<br/>Products/Shops]
    end

    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    F --> H
    F --> P
    E --> Q
    F --> Q
    H --> I
    H --> J
    G --> K
    F --> K
    Q --> K
    K --> L
    K --> M
    K --> N
    K --> O
```

## Component Deep Dive

### 1. Frontend Layer (Zero Build Complexity)

**Technology Stack:**

- **HTMX**: Handles all dynamic updates
- **Server-Sent Events**: Real-time streaming responses
- **Jinja2 Templates**: Server-side rendering

**Key Design Decision:** No JavaScript build tools, no npm, no webpack. Just HTML that updates itself.

```html
<!-- Example: Self-updating chat interface -->
<form hx-post="/coffee/chat/send"
      hx-target="#chat-history"
      hx-swap="beforeend">
    <input name="message" placeholder="Ask about coffee..." />
    <button type="submit">Send ☕</button>
</form>

<div id="chat-history"
     hx-ext="sse"
     sse-connect="/coffee/chat/stream/{query_id}">
    <!-- Messages appear here automatically -->
</div>
```

### 2. Application Layer (Python + Litestar)

**Core Framework:**

- **Litestar 2.x**: Modern async Python web framework
- **oracledb**: Python driver for Oracle Database (async support)
- **msgspec**: High-performance serialization for JSON/DTOs
- **Raw SQL**: Direct database access for clarity and performance

**Service Architecture:**

```python
class RecommendationService:
    """Main business logic orchestrator using raw SQL"""

    def __init__(self,
                 vertex_ai_service: VertexAIService,
                 products_service: ProductService,
                 shops_service: ShopService,
                 session_service: UserSessionService,
                 embedding_cache: EmbeddingCache,
                 response_cache: ResponseCacheService):
        self.vertex_ai = vertex_ai_service
        self.products = products_service
        self.shops = shops_service
        self.sessions = session_service
        self.embedding_cache = embedding_cache
        self.response_cache = response_cache
```

### 3. AI Integration Layer

**Intent Detection System with Cached Embeddings:**

```python
class IntentRouter:
    """Semantic understanding of user queries with database-cached embeddings"""

    INTENT_EXEMPLARS = {
        "PRODUCT_RAG": [
            "What coffee do you recommend?",
            "Something smooth and chocolatey",
            "I need a strong espresso"
        ],
        "GENERAL_CONVERSATION": [
            "Hello!",
            "Thanks for the help",
            "Tell me a coffee joke"
        ]
    }

    async def initialize(self):
        """Load cached embeddings from database on startup"""
        if self.exemplar_service:
            # Check for cached embeddings in database
            cached_data = await self.exemplar_service.get_exemplars_with_phrases()
            if cached_data:
                logger.info("Loaded %d cached embeddings from database", len(cached_data))
                self._initialized = True
                return

            # First run - compute and cache embeddings
            logger.info("Populating intent exemplar cache...")
            await self.exemplar_service.populate_cache(
                self.INTENT_EXEMPLARS,
                self.vertex_ai
            )

    async def route_intent(self, query: str) -> tuple[str, float, str]:
        # Returns: (intent_type, confidence_score, matched_exemplar)
```

**Vertex AI Integration:**

```python
class VertexAIService:
    """Native Google AI integration"""

    def __init__(self):
        # Smart model initialization with fallback
        try:
            self.model = GenerativeModel("gemini-2.5-flash")
            logger.info("✅ Using latest Gemini 2.5")
        except Exception:
            self.model = GenerativeModel("gemini-1.5-flash-001")
            logger.info("⚠️ Using stable fallback")
```

### 4. Persona System (Adaptive User Experience)

**PersonaManager Architecture:**

```python
class PersonaManager:
    """Manages different user expertise levels"""

    PERSONAS = {
        "novice": PersonaConfig(
            name="Coffee Novice",
            temperature=0.8,  # More creative
            system_prompt_addon="Use simple language...",
            focus_areas=["basics", "easy recommendations"]
        ),
        "expert": PersonaConfig(
            name="Coffee Expert",
            temperature=0.5,  # More precise
            system_prompt_addon="Use technical terminology...",
            focus_areas=["processing", "terroir", "cupping"]
        )
    }

    @classmethod
    def get_system_prompt(cls, persona: str, base_prompt: str) -> str:
        """Enhance prompts based on user expertise"""
        config = cls.PERSONAS[persona]
        return f"{base_prompt}\n\n{config.system_prompt_addon}"
```

### 5. Data Layer (Oracle 23AI)

**Database Schema:**

```sql
-- Core business data with AI embeddings
CREATE TABLE products (
    id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name VARCHAR2(200) NOT NULL,
    description CLOB,
    embedding VECTOR(768, FLOAT32),  -- AI magic happens here!
    price NUMBER(10,2),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- Intent exemplar caching for fast startup
CREATE TABLE intent_exemplar (
    id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    intent VARCHAR2(50) NOT NULL,
    phrase VARCHAR2(500) NOT NULL,
    embedding VECTOR(768, FLOAT32),  -- Pre-computed embeddings
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    CONSTRAINT uq_intent_phrase UNIQUE (intent, phrase),
    INDEX idx_intent (intent)
);

-- Intelligent session management
CREATE TABLE user_sessions (
    id RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    session_id VARCHAR2(128) UNIQUE NOT NULL,
    user_id VARCHAR2(128) NOT NULL,
    data JSON,  -- Flexible session storage
    expires_at TIMESTAMP NOT NULL,
    INDEX idx_session_expires (expires_at)
);

-- Response caching with automatic expiry
CREATE TABLE response_cache (
    cache_key VARCHAR2(256) PRIMARY KEY,
    query_text VARCHAR2(4000),
    response JSON,
    expires_at TIMESTAMP NOT NULL,
    hit_count NUMBER DEFAULT 0
);

-- Performance metrics tracking
CREATE TABLE search_metrics (
    id RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
    query_id VARCHAR2(128) NOT NULL,
    user_id VARCHAR2(128),
    search_time_ms NUMBER,
    embedding_time_ms NUMBER,
    oracle_time_ms NUMBER,
    similarity_score NUMBER,
    result_count NUMBER,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    INDEX idx_metrics_time (created_at, search_time_ms)
);
```

## Request Flow Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant H as HTMX UI
    participant L as Litestar
    participant I as IntentRouter
    participant V as VertexAI
    participant O as Oracle23AI
    participant S as SSE Stream

    U->>H: "I want smooth coffee"
    H->>L: POST /coffee/chat/send
    L->>I: Detect intent
    I->>V: Create embedding
    V-->>I: Vector[768]
    I-->>L: PRODUCT_RAG (0.94)
    L->>O: Vector similarity search
    O-->>L: Top 5 products
    L->>V: Generate response
    L->>S: Start streaming
    S-->>H: Chunk 1: "Based on..."
    S-->>H: Chunk 2: "I recommend..."
    S-->>H: Done + metrics
    H-->>U: Updated UI
```

## Security Architecture

### API Security

- **Rate Limiting**: 100 requests/minute per user (Litestar Rate Limiting)
- **CSRF Protection**: Built into Litestar
- **CSP Protection: Custom implementation
- **Input Validation**: msgspec with strict schemas
- **SQL Injection**: Parameterized queries only

## Deployment Architecture

### Development Environment

```yaml
# docker-compose.yml
services:
  oracle-free:
    image: gvenzl/oracle-free:23-slim
    environment:
      ORACLE_PASSWORD: ${ORACLE_PASSWORD}
    ports:
      - "1521:1521"
    volumes:
      - oracle-data:/opt/oracle/oradata

```

### Production Architecture

```mermaid
graph LR
    subgraph "Load Balancer"
        LB[Cloud LB]
    end

    subgraph "Application Tier"
        A1[App Instance 1]
        A2[App Instance 2]
        A3[App Instance 3]
    end

    subgraph "Database Tier"
        O1[Oracle Primary]
        O2[Oracle Standby]
    end

    subgraph "External Services"
        V[Vertex AI]
    end

    LB --> A1
    LB --> A2
    LB --> A3
    A1 --> O1
    A2 --> O1
    A3 --> O1
    O1 -.-> O2
    A1 --> V
    A2 --> V
    A3 --> V
```

## Monitoring & Observability

### Key Metrics Dashboard

```python
# Real-time metrics collection
class MetricsCollector:
    async def record_search(self, metrics: SearchMetrics):
        await self.oracle.execute("""
            INSERT INTO search_metrics (
                query_id, user_id,
                search_time_ms, embedding_time_ms,
                oracle_time_ms, similarity_score,
                result_count, created_at
            ) VALUES (
                :query_id, :user_id,
                :search_time, :embed_time,
                :oracle_time, :similarity,
                :count, SYSTIMESTAMP
            )
        """, metrics.dict())
```

### Health Checks

```python
@get("/health")
async def health_check(
    oracle: OracleService,
    vertex_ai: VertexAIService
) -> dict:
    return {
        "status": "healthy",
        "checks": {
            "database": await oracle.ping(),
            "vertex_ai": await vertex_ai.health_check(),
            "vector_search": await oracle.vector_search_test(),
            "cache_hit_rate": await oracle.get_cache_stats()
        },
        "timestamp": datetime.utcnow()
    }
```

## Development Workflow

### Local Development

```bash
# 1. Start infrastructure
make start-infra

# 2. Run
uv run app run
```

### Code Organization

```
app/
├── controllers/      # HTTP endpoints
├── services/        # Business logic
│   ├── intent_router.py
│   ├── vertex_ai.py
│   └── recommendation.py
├── db/
│   ├── fixtures/    # Sample data JSON files
│   └── models.py    # Data models (if needed)
├── schemas.py       # msgspec DTOs
└── config.py        # Settings management
```

## Performance Optimizations

### 1. Intent Exemplar Caching

```python
# Database-cached embeddings eliminate startup delay
class IntentExemplarService:
    """Manages cached intent exemplar embeddings in Oracle"""

    async def populate_cache(self, exemplars: dict, vertex_ai_service):
        """One-time population of exemplar embeddings"""
        count = 0
        for intent, phrases in exemplars.items():
            for phrase in phrases:
                # Check if already cached
                existing = await self.repository.get_one_or_none(
                    intent=intent, phrase=phrase
                )
                if not existing or not existing.embedding:
                    # Generate and cache embedding
                    embedding = await vertex_ai_service.create_embedding(phrase)
                    await self.cache_exemplar(intent, phrase, embedding)
                    count += 1
        logger.info("Populated cache with %d new exemplar embeddings", count)
        return count

# Near-instant startup with cached embeddings
async def initialize_intent_router():
    router = IntentRouter(vertex_ai_service, exemplar_service)
    await router.initialize()  # Loads from cache, no API calls!
    return router
```

### 2. Batch Processing

```python
# Process multiple embeddings in one API call
async def create_embeddings_batch(texts: list[str]) -> list[list[float]]:
    return await vertex_ai.embeddings.create_batch(
        texts,
        batch_size=100,
        model="text-embedding-004"
    )
```

### 3. Query Optimization

```sql
-- Use Oracle hints for performance
SELECT /*+ LEADING(p) USE_NL(i s) INDEX(p embed_idx) */
    p.*, s.*, i.quantity
FROM products p
JOIN inventory i ON p.id = i.product_id
JOIN shops s ON i.shop_id = s.id
WHERE VECTOR_DISTANCE(p.embedding, :vector, COSINE) < 0.8;
```
