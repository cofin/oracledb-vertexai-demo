# Architecture Overview

Comprehensive system architecture for the Cymbal Coffee AI-powered search application using Oracle Database 23ai, Vertex AI, and Google ADK.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Technology Stack](#technology-stack)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Deployment Architecture](#deployment-architecture)
- [Security Architecture](#security-architecture)
- [Scalability Patterns](#scalability-patterns)
- [Monitoring and Observability](#monitoring-and-observability)

## System Overview

**Cymbal Coffee** is an AI-powered product search and recommendation system that combines:

- **Oracle Database 23ai**: Native vector search, JSON storage, ACID transactions
- **Vertex AI**: text-embedding-005 for embeddings, Gemini 2.5 for generation
- **Google ADK**: LlmAgent orchestration for agentic interactions
- **Litestar**: High-performance async web framework
- **HTMX**: Server-driven UI with partial page updates

**Core Capabilities**:
1. **Semantic Search**: Natural language product search with vector similarity
2. **AI Chat**: Conversational product recommendations with Gemini
3. **RAG (Retrieval-Augmented Generation)**: Context-aware responses with product data
4. **Performance Monitoring**: Real-time metrics and dashboard
5. **Caching**: Two-level cache (embeddings + responses) for performance

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Browser                            │
│                        (HTMX Client)                             │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/HTMX
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Litestar Web Server                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Controllers (Routing)                         │  │
│  │  • CoffeeChatController  • DashboardController           │  │
│  └───────────┬──────────────────────────┬───────────────────┘  │
│              │                           │                       │
│  ┌───────────▼──────────┐   ┌───────────▼──────────┐          │
│  │ Dependency Injection │   │   HTMX Plugin        │          │
│  │ (provide_* functions)│   │  (HTMXRequest/       │          │
│  └───────────┬──────────┘   │   HTMXTemplate)      │          │
│              │               └──────────────────────┘          │
│              ▼                                                   │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                SQLSpec Plugin                          │   │
│  │  (Session Management + Connection Pooling)             │   │
│  └────────────┬───────────────────────────────────────────┘   │
└───────────────┼─────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Service Layer                              │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ ProductService  │  │ ChatService  │  │ MetricsService   │  │
│  │ (SQLSpecService)│  │              │  │                  │  │
│  └────────┬────────┘  └──────┬───────┘  └────────┬─────────┘  │
│           │                   │                    │             │
│  ┌────────▼────────┐  ┌──────▼───────┐  ┌────────▼─────────┐  │
│  │VertexAIService  │  │ EmbeddingCache│  │ ResponseCache    │  │
│  │ (Embeddings +   │  │ (Oracle-backed)│  │ (Oracle-backed)  │  │
│  │  Generation)    │  └────────────────┘  └──────────────────┘  │
│  └────────┬────────┘                                             │
│           │                                                       │
│  ┌────────▼────────────────────────────────────────────────┐   │
│  │        OracleVectorSearchService                        │   │
│  │  (Vector Similarity Search + RAG)                       │   │
│  └────────┬────────────────────────────────────────────────┘   │
└───────────┼─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Oracle Database 23ai                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    product table                         │  │
│  │  • id, name, description, price                          │  │
│  │  • embedding VECTOR(768, FLOAT32)                        │  │
│  │  • metadata JSON                                         │  │
│  │  • Indexes: HNSW on embedding                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              embedding_cache table                       │  │
│  │  • cache_key, text, embedding_vector                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │             response_cache table                         │  │
│  │  • cache_key, user_id, response_data                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              search_metrics table                        │  │
│  │  • query_id, user_id, search_time_ms, result_count       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
            │
            │ python-oracledb
            │ (async connection pool)
            │
┌───────────▼─────────────────────────────────────────────────────┐
│                     Google Vertex AI                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  text-embedding-005 (768 dimensions)                     │  │
│  │  • RETRIEVAL_QUERY for search queries                    │  │
│  │  • RETRIEVAL_DOCUMENT for product descriptions           │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Gemini 2.5 Flash (Content Generation)                   │  │
│  │  • Fast responses for product recommendations            │  │
│  │  • Conversational AI for chat                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Language** | Python | 3.12+ | Async/await, type hints |
| **Web Framework** | Litestar | 2.0+ | ASGI, routing, DI |
| **Database** | Oracle Database | 23ai | Vector search, JSON, ACID |
| **DB Driver** | python-oracledb | 2.x | Async driver, connection pooling |
| **DB Abstraction** | SQLSpec | Latest | Type-safe queries, parameter binding |
| **AI Platform** | Google Vertex AI | Latest | Embeddings, generation |
| **AI SDK** | Vertex AI Python SDK | 1.101+ | text-embedding-005, Gemini 2.5 |
| **Agent Framework** | Google ADK | 1.0+ | LlmAgent orchestration |
| **Schema Validation** | msgspec | Latest | Fast serialization, validation |
| **Logging** | structlog | Latest | Structured logging |

### Frontend

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Templating** | Jinja2 | HTML template rendering |
| **Interactivity** | HTMX | Server-driven partial updates |
| **Styling** | Tailwind CSS | Utility-first CSS |
| **Icons** | Heroicons | SVG icons |

### Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Container Runtime** | Docker | Application containerization |
| **Orchestration** | Docker Compose | Local development |
| **Process Manager** | uv | Python package management |
| **ASGI Server** | Uvicorn | Production ASGI server |

## Component Architecture

### Web Layer (Litestar)

**Controllers**: Handle HTTP requests, route to services
```python
CoffeeChatController
├─ show_homepage() → HTMXTemplate
├─ handle_chat() → HTMXTemplate (partial)
└─ performance_dashboard() → HTMXTemplate
```

**Dependency Injection**: Provide services per-request
```python
provide_product_service() → ProductService
provide_vertex_ai_service() → VertexAIService
provide_chat_service() → ChatService
provide_metrics_service() → MetricsService
```

**Plugins**:
- `SQLSpecPlugin`: Database session management
- `HTMXPlugin`: HTMX request/response handling

### Service Layer

**ProductService** (SQLSpecService):
- CRUD operations for products
- Vector similarity search
- Hybrid search (vector + filters)
- Bulk operations

**VertexAIService**:
- Create embeddings (query vs document)
- Generate content (Gemini)
- Stream responses
- RAG pattern (search + generate)

**OracleVectorSearchService**:
- Coordinate embedding + search
- Track timing metrics
- Cache integration

**CacheService** (Embedding + Response):
- Embedding cache: Reduce API calls
- Response cache: Improve latency
- TTL management
- Cache hit/miss tracking

**MetricsService**:
- Record search metrics
- Dashboard aggregations
- Performance tracking

### Data Layer

**Oracle Database 23ai**:

**product table**:
```sql
CREATE TABLE product (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    description CLOB,
    price NUMBER(10, 2) NOT NULL,
    category VARCHAR2(100),
    in_stock BOOLEAN DEFAULT true,
    embedding VECTOR(768, FLOAT32),
    metadata JSON,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE INDEX idx_product_embedding_hnsw
ON product (embedding)
INDEXTYPE IS HNSW
PARAMETERS ('DISTANCE COSINE, M 16, EF_CONSTRUCTION 64');
```

**embedding_cache table**:
```sql
CREATE TABLE embedding_cache (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cache_key VARCHAR2(64) UNIQUE NOT NULL,
    text VARCHAR2(500),
    embedding_vector VECTOR(768, FLOAT32) NOT NULL,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    accessed_at TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

**response_cache table**:
```sql
CREATE TABLE response_cache (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cache_key VARCHAR2(255) NOT NULL,
    user_id VARCHAR2(100) NOT NULL,
    response_data CLOB NOT NULL,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    CONSTRAINT uk_cache_user UNIQUE (cache_key, user_id)
);
```

**search_metrics table**:
```sql
CREATE TABLE search_metrics (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_id VARCHAR2(100) UNIQUE NOT NULL,
    user_id VARCHAR2(100),
    query_text VARCHAR2(500),
    search_time_ms NUMBER(10, 2),
    embedding_time_ms NUMBER(10, 2),
    oracle_time_ms NUMBER(10, 2),
    result_count INTEGER,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

## Data Flow

### 1. Search Query Flow

```
User types query "light roast coffee"
    ↓
Browser sends HTMX POST /api/chat
    ↓
Litestar routes to CoffeeChatController.handle_chat()
    ↓
Dependencies injected (product_service, vertex_ai_service)
    ↓
OracleVectorSearchService.similarity_search(query)
    ├─ Check embedding_cache for query
    │  ├─ Cache HIT → Use cached embedding
    │  └─ Cache MISS → Call Vertex AI text-embedding-005
    │      └─ Task type: RETRIEVAL_QUERY
    │      └─ Store in embedding_cache
    ↓
    ├─ Convert embedding to array.array('f', vector)
    └─ Execute Oracle SQL:
        SELECT id, name, description,
               1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) as similarity
        FROM product
        WHERE 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) >= 0.7
        ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE)
        FETCH FIRST 5 ROWS ONLY
    ↓
    └─ Returns list[Product] with similarity scores
    ↓
Build context from search results
    ↓
Generate response with Gemini 2.5 Flash
    ├─ Check response_cache
    │  ├─ Cache HIT → Return cached response
    │  └─ Cache MISS → Call Vertex AI Gemini
    │      └─ Prompt: system instruction + context + query
    │      └─ Store in response_cache
    ↓
Record metrics (search_time_ms, result_count)
    ↓
Return HTMXTemplate (partials/chat_response.html)
    ↓
HTMX swaps content into page (no full reload)
    ↓
User sees AI response with product recommendations
```

### 2. Product Indexing Flow

```
Admin adds new product "Ethiopian Yirgacheffe"
    ↓
ProductService.create(data)
    ↓
Insert product into Oracle (without embedding)
    ↓
Background job: Generate embeddings for new products
    ↓
VertexAIService.create_document_embedding(description)
    └─ Task type: RETRIEVAL_DOCUMENT (not RETRIEVAL_QUERY!)
    └─ Returns 768-dim vector
    ↓
Convert to array.array('f', embedding)
    ↓
ProductService.update_embedding(product_id, vector)
    └─ UPDATE product SET embedding = :vec WHERE id = :id
    ↓
HNSW index automatically updated by Oracle
    ↓
Product now searchable via vector similarity
```

## Deployment Architecture

### Local Development

```
Docker Compose
├─ oracle-db (Oracle Database 23ai Free)
│  ├─ Port: 1521
│  ├─ Volume: ./data/oracle
│  └─ Init scripts: ./db/init/
├─ app (Litestar + Uvicorn)
│  ├─ Port: 8000
│  ├─ Hot reload: enabled
│  └─ Env: .env.local
└─ Network: cymbal-network
```

**docker-compose.yml**:
```yaml
services:
  oracle-db:
    image: container-registry.oracle.com/database/free:23.5.0.0
    ports:
      - "1521:1521"
    volumes:
      - oracle-data:/opt/oracle/oradata
      - ./db/init:/docker-entrypoint-initdb.d
    environment:
      ORACLE_PWD: ${ORACLE_PASSWORD}

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - oracle-db
    environment:
      DATABASE_URL: oracle://user:pass@oracle-db:1521/FREEPDB1
      GOOGLE_PROJECT_ID: ${GOOGLE_PROJECT_ID}
      GOOGLE_LOCATION: us-central1
    command: uv run uvicorn app.server.app:app --host 0.0.0.0 --port 8000 --reload

volumes:
  oracle-data:
```

### Production Deployment

**Google Cloud Platform**:
```
Cloud Run (Litestar app)
    ↓ private VPC
Oracle Database 23ai (Compute Engine or Bare Metal)
    ↓
Cloud SQL Proxy (optional, for Cloud SQL)
    ↓
Vertex AI (embeddings + generation)
    ↓
Cloud Logging (structured logs)
    ↓
Cloud Monitoring (metrics + alerts)
```

**Infrastructure as Code** (Terraform):
```hcl
resource "google_cloud_run_service" "app" {
  name     = "cymbal-coffee"
  location = "us-central1"

  template {
    spec {
      containers {
        image = "gcr.io/project/cymbal-coffee:latest"
        env {
          name  = "DATABASE_URL"
          value = "oracle://..."
        }
        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
      }
    }
  }
}
```

## Security Architecture

### Authentication and Authorization

**Application Authentication**:
- Service account for Vertex AI
- IAM roles for Google Cloud resources
- Environment variables for sensitive config

**Database Security**:
- Connection pooling with credentials
- Encrypted connections (TLS)
- Parameter binding (SQL injection prevention)
- Least privilege database users

### Data Protection

**Encryption**:
- At rest: Oracle Transparent Data Encryption (TDE)
- In transit: TLS 1.3 for all connections
- Secrets: Google Secret Manager

**SQL Injection Prevention**:
```python
# ✅ SAFE - Parameter binding
await driver.select(
    "SELECT * FROM product WHERE category = :cat",
    cat=user_input
)

# ❌ UNSAFE - String interpolation
sql = f"SELECT * FROM product WHERE category = '{user_input}'"
```

### Network Security

**Firewall Rules**:
- Allow: Cloud Run → Oracle Database (private IP)
- Allow: Application → Vertex AI (Google APIs)
- Deny: Direct public access to database

**VPC Configuration**:
- Private subnet for Oracle Database
- Serverless VPC connector for Cloud Run
- Cloud NAT for outbound connections

## Scalability Patterns

### Horizontal Scaling

**Litestar App** (Cloud Run):
- Auto-scale: 0-100 instances
- CPU utilization target: 70%
- Request concurrency: 80 per instance

**Oracle Database**:
- RAC (Real Application Clusters) for horizontal scale
- Read replicas for read-heavy workloads
- Sharding for multi-tenant scenarios

### Vertical Scaling

**Oracle Database**:
- Scale up: Increase CPU/memory
- In-Memory column store for hot data
- SPATIAL_VECTOR_ACCELERATION for SIMD

### Caching Strategy

**Two-Level Cache**:
1. **Embedding Cache** (Oracle-backed)
   - TTL: 7 days
   - Hit rate target: >80%
   - Reduces Vertex AI API calls

2. **Response Cache** (Oracle-backed)
   - TTL: 5 minutes
   - Per-user cache keys
   - Reduces generation latency

### Connection Pooling

**python-oracledb**:
```python
pool = oracledb.create_pool(
    min=2,              # Warm connections
    max=10,             # Per-instance limit
    increment=1,        # Add gradually
    timeout=3600,       # Recycle after 1h
    wait_timeout=30000  # Wait 30s max
)
```

**Guidelines**:
- `max = CPUs * 2-4` per instance
- Monitor utilization (60-80% ideal)
- Adjust based on query complexity

## Monitoring and Observability

### Structured Logging

**structlog Configuration**:
```python
import structlog

logger = structlog.get_logger()

# Log structured events
logger.info(
    "vector_search_complete",
    query_id=query_id,
    result_count=len(results),
    search_time_ms=search_time,
    embedding_cache_hit=cache_hit
)
```

### Metrics

**Application Metrics**:
- Request latency (p50, p95, p99)
- Error rate (5xx responses)
- Cache hit rate (embedding + response)
- Vector search time distribution

**Database Metrics**:
- Connection pool utilization
- Query execution time
- Index effectiveness
- Buffer cache hit ratio

### Tracing

**OpenTelemetry Integration**:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("vector_search")
async def vector_search(query: str):
    with tracer.start_as_current_span("create_embedding"):
        embedding = await create_embedding(query)

    with tracer.start_as_current_span("oracle_query"):
        results = await oracle_search(embedding)

    return results
```

### Dashboards

**Performance Dashboard** (Litestar endpoint):
- Search latency trends
- Cache performance
- Error rates
- Top queries

**Oracle Enterprise Manager**:
- Database performance
- SQL tuning advisor
- Vector index statistics
- Memory utilization

## See Also

- [Vertex AI Integration](vertex-ai-integration.md) - AI components
- [Oracle Vector Search](oracle-vector-search.md) - Vector operations
- [Oracle Performance](oracle-performance.md) - Optimization
- [Litestar Framework](litestar-framework.md) - Web layer
- [SQLSpec Patterns](sqlspec-patterns.md) - Data layer

## Resources

- Oracle Database 23ai: https://www.oracle.com/database/23ai/
- Google Vertex AI: https://cloud.google.com/vertex-ai
- Google ADK: https://github.com/google/adk-python
- Litestar: https://docs.litestar.dev/
