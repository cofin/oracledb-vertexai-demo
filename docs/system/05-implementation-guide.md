# 🛠️ Implementation Guide: Build Your Own AI System

## Prerequisites Checklist

Before we begin, ensure you have:
- [ ] Python 3.11+ installed
- [ ] Docker Desktop running
- [ ] Google Cloud account (or free credits)
- [ ] Basic SQL knowledge
- [ ] 2-4 hours of time

## Phase 1: Environment Setup (30 minutes)

### Step 1.1: Clone and Initialize

```bash
# Clone the repository
git clone https://github.com/your-org/oracledb-vertexai-demo.git
cd oracledb-vertexai-demo

# Install uv (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync
```

### Step 1.2: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit with your favorite editor
nano .env  # or vim, code, etc.
```

Required configuration:
```env
# Oracle Database (auto-configured with Docker)
DATABASE_URL=oracle+oracledb://coffee_user:secure_password@localhost:1521/FREEPDB1

# Google Cloud / Vertex AI
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Optional: Specific model selection
GEMINI_MODEL=gemini-2.5-flash
```

### Step 1.3: Start Oracle Database

```bash
# Start Oracle 23AI Free (includes AI features!)
docker-compose up -d oracle-free

# Monitor startup (takes 2-3 minutes first time)
docker-compose logs -f oracle-free

# Look for: "DATABASE IS READY TO USE!"
```

### Step 1.4: Verify Setup

```bash
# Check Python environment
python --version  # Should be 3.11+

# Check dependencies
uv pip list | grep -E "(litestar|oracledb|vertexai)"

# Check Docker
docker ps  # Should show oracle-free running

# Check database connection
uv run app database check-connection
```

## Phase 2: Database Initialization (20 minutes)

### Step 2.1: Initialize Database Schema

```bash
# Run the database initialization script
docker exec -i oracledb-vertexai-demo-oracle-free-1 sqlplus sys/secure_password@localhost:1521/FREE as sysdba < tools/deploy/oracle/db_init.sql

# This creates:
# - products table with VECTOR column
# - intent_exemplar table for cached embeddings
# - user_sessions with JSON storage
# - response_cache with TTL
# - search_metrics for analytics
# - All necessary sequences and triggers
# - Proper indexes including HNSW vector index
```

**Note:** The project now uses raw SQL scripts for schema management. All tables are created with proper Oracle 23AI features including:

- VECTOR data type with HNSW indexing
- In-memory tables for hot data
- Native JSON support
- Automatic timestamp triggers

### Step 2.2: Load Sample Data

```bash
# Load coffee products, shops, and inventory
uv run app load-fixtures

# If you need to reset data:
uv run app truncate-tables --force
uv run app load-fixtures

# For selective reset:
uv run app truncate-tables --skip-cache  # Keep embeddings
uv run app truncate-tables --skip-session  # Keep user sessions
```

### Step 2.3: Generate Embeddings

```bash
# Generate embeddings for all products (recommended for demo)
uv run app load-vectors
# This creates embeddings from product name + description
# e.g., "Cymbal Dark Roast: A bold, full-bodied coffee with chocolate notes"

# Alternative: For production with many products, use batch processing
uv run app bulk-embed

# For incremental updates (up to 200 products at a time):
uv run app embed-new --limit 200

# Initialize intent router cache (happens automatically on first run)
# The system will populate intent_exemplar table with pre-computed embeddings
# stored in Oracle In-Memory tables for ultra-fast intent detection
```

## Phase 3: Core Services Implementation (60 minutes)

### Step 3.1: Understanding the Service Architecture

```python
# app/services/__init__.py structure
services/
├── intent_router.py        # Understands user intent
├── intent_exemplar.py      # Manages cached embeddings (raw SQL)
├── vertex_ai.py           # Google AI integration
├── recommendation.py      # Main business logic
├── user_session.py       # Session management (raw SQL)
├── chat_conversation.py  # Chat history (raw SQL)
├── response_cache.py     # Response caching (raw SQL)
├── search_metrics.py     # Performance tracking (raw SQL)
├── product.py           # Product management (raw SQL)
├── shop.py             # Shop management (raw SQL)
├── company.py          # Company management (raw SQL)
├── inventory.py        # Inventory tracking (raw SQL)
└── bulk_embedding.py   # Batch AI processing
```

### Step 3.2: Intent Router Deep Dive

The IntentRouter uses semantic similarity to understand queries:

```python
# app/services/intent_router.py
class IntentRouter:
    """Routes queries to appropriate handlers using AI"""
    
    INTENT_EXEMPLARS = {
        "PRODUCT_RAG": [
            "What coffee do you recommend?",
            "I want something smooth",
            "Tell me about espresso"
        ],
        "LOCATION_RAG": [
            "Where are your shops?",
            "Find store near me",
            "What are your hours?"
        ]
    }
    
    async def route_intent(self, query: str) -> tuple[str, float, str]:
        """Returns (intent_type, confidence, matched_example)"""
        # Uses cached embeddings from database for 75% faster performance!
```

### Step 3.3: Vertex AI Service Configuration

```python
# app/services/vertex_ai.py
class VertexAIService:
    """Native Google AI integration with fallbacks"""
    
    def __init__(self):
        # Smart initialization with fallback
        try:
            self.model = GenerativeModel("gemini-2.5-flash")
            logger.info("✅ Using Gemini 2.5 Flash")
        except Exception:
            self.model = GenerativeModel("gemini-1.5-flash-001")
            logger.info("⚠️ Using fallback model")
```

### Step 3.4: Raw SQL Service Pattern

All services now use raw Oracle SQL for clarity and performance:

```python
# app/services/product.py
class ProductService:
    """Product management using raw SQL"""
    
    def __init__(self, connection: oracledb.AsyncConnection):
        self.connection = connection
    
    async def get_by_id(self, product_id: int) -> dict | None:
        cursor = self.connection.cursor()
        try:
            await cursor.execute("""
                SELECT id, name, description, current_price, size
                FROM product 
                WHERE id = :id
            """, {"id": product_id})
            
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "current_price": row[3],
                    "size": row[4]
                }
            return None
        finally:
            cursor.close()
```

## Phase 4: API Endpoints (30 minutes)

### Step 4.1: Main Controller Structure

```python
# app/controllers.py
from litestar import Controller, post, get
from litestar.response import Template, Stream

@Controller(path="/api/v1")
class CoffeeController:
    """Main API endpoints"""
    
    @post("/chat")
    async def chat(
        self, 
        data: ChatMessage,
        recommendation_service: RecommendationService
    ) -> ChatResponse:
        """Process user query and return recommendation"""
        
    @get("/stream/{query_id}")
    async def stream_response(self, query_id: str) -> Stream:
        """Stream AI response in real-time"""
```

### Step 4.2: HTMX Integration

```python
# app/controllers.py
@Controller(path="/coffee", include_in_schema=False)
class HTMXController:
    """HTMX-specific endpoints for real-time UI"""
    
    @post("/chat/send")
    async def send_message(self, data: dict) -> Template:
        # Return partial HTML for HTMX
        return Template(
            "partials/chat_response.html",
            context={"response": ai_response}
        )
```

## Phase 5: Frontend Implementation (30 minutes)

### Step 5.1: Base Template

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div class="container mx-auto p-4">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

### Step 5.2: Chat Interface

```html
<!-- templates/coffee_chat.html -->
{% extends "base.html" %}
{% block content %}
<div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold mb-8">AI Coffee Assistant</h1>
    
    <div id="chat-container" class="bg-gray-100 rounded-lg p-4 h-96 overflow-y-auto">
        <div id="chat-messages">
            <!-- Messages appear here -->
        </div>
    </div>
    
    <form hx-post="/coffee/chat/send" 
          hx-target="#chat-messages" 
          hx-swap="beforeend"
          class="mt-4">
        <input type="text" 
               name="message" 
               placeholder="Ask me about coffee..."
               class="w-full p-3 rounded-lg border">
        <button type="submit" 
                class="mt-2 bg-blue-500 text-white px-6 py-2 rounded-lg">
            Send ☕
        </button>
    </form>
</div>
{% endblock %}
```

### Step 5.3: Response Partials

```html
<!-- templates/partials/chat_response.html -->
<div class="mb-4">
    <div class="font-semibold">You:</div>
    <div class="bg-white p-3 rounded">{{ user_message }}</div>
</div>

<div class="mb-4" 
     hx-ext="sse" 
     sse-connect="/coffee/stream/{{ query_id }}">
    <div class="font-semibold">AI Assistant:</div>
    <div class="bg-blue-100 p-3 rounded" sse-swap="message">
        <span class="loading">Thinking...</span>
    </div>
</div>

{% if products %}
<div class="grid grid-cols-2 gap-4 mt-4">
    {% for product in products %}
    <div class="bg-white p-4 rounded shadow">
        <h3 class="font-bold">{{ product.name }}</h3>
        <p class="text-sm">{{ product.description }}</p>
        <p class="text-green-600 font-bold">${{ product.price }}</p>
    </div>
    {% endfor %}
</div>
{% endif %}
```

## Phase 6: Testing & Validation (30 minutes)

### Step 6.1: Unit Tests

```python
# tests/unit/test_intent_router.py
import pytest
from app.services.intent_router import IntentRouter

@pytest.mark.anyio
async def test_product_intent_detection():
    router = IntentRouter(mock_vertex_ai)
    
    intent, confidence, _ = await router.route_intent(
        "I want something smooth and chocolatey"
    )
    
    assert intent == "PRODUCT_RAG"
    assert confidence > 0.8
```

### Step 6.2: Integration Tests

```python
# tests/integration/test_recommendation_flow.py
@pytest.mark.anyio
async def test_full_recommendation_flow(client, db_session):
    response = await client.post(
        "/api/v1/chat",
        json={"message": "recommend a morning coffee"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) > 0
    assert data["intent"] == "PRODUCT_RAG"
```

### Step 6.3: Performance Testing

```bash
# Run performance benchmarks
uv run app test performance

# Expected results:
# - Intent detection: <2ms (with cached embeddings)
# - Embedding generation: <15ms
# - Vector search: <18ms
# - Total response: <45ms
```

## Phase 7: Production Deployment (60 minutes)

### Step 7.1: Environment Preparation

```bash
# Production .env
DATABASE_URL=oracle+oracledb://prod_user:${DB_PASSWORD}@oracle-prod:1521/PRODPDB
GEMINI_MODEL=gemini-2.5-flash
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Step 7.2: Docker Build

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install Oracle client
RUN apt-get update && apt-get install -y \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install uv && uv pip install .

# Copy application
COPY . .

# Run application
CMD ["uv", "run", "app", "run", "--host", "0.0.0.0"]
```

### Step 7.3: Production Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    ports:
      - "80:8000"
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
```

## Phase 8: Monitoring & Optimization (30 minutes)

### Step 8.1: Metrics Dashboard

```python
# app/monitoring.py
@get("/metrics")
async def metrics_dashboard() -> Template:
    stats = await db.fetch_one("""
        SELECT 
            COUNT(*) as total_queries,
            AVG(search_time_ms) as avg_search_time,
            AVG(similarity_score) as avg_relevance,
            COUNT(DISTINCT user_id) as unique_users
        FROM search_metrics
        WHERE created_at > SYSTIMESTAMP - INTERVAL '24' HOUR
    """)
    
    return Template("metrics.html", context={"stats": stats})
```

### Step 8.2: Performance Monitoring

```bash
# Set up monitoring
uv run app monitoring enable

# View real-time metrics
uv run app monitoring dashboard

# Export metrics for analysis
uv run app monitoring export --format=csv
```

## Common Issues & Solutions

### Issue: Slow vector search
```sql
-- Solution: Create optimized index
CREATE INDEX idx_product_embedding 
ON products (embedding) 
INDEXTYPE IS VECTOR 
PARAMETERS ('TYPE=HNSW, NEIGHBORS=32');
```

### Issue: High API costs
```python
# Solution: Implement caching
if cached_response := await cache.get(query_hash):
    return cached_response
```

### Issue: Intent detection errors
```python
# Solution: Add more exemplars and update cache
INTENT_EXEMPLARS["PRODUCT_RAG"].extend([
    "What's your best seller?",
    "Popular coffee choices",
    "Customer favorites"
])

# Repopulate the cache with new exemplars
uv run app database populate-intent-cache
```

## Next Steps

Congratulations! You've built an AI-powered system. Here's what's next:

1. **Customize for your business**: Replace coffee with your products
2. **Add features**: Voice input, image search, personalization
3. **Scale up**: Add more products, handle more users
4. **Monitor and improve**: Use metrics to optimize

## Additional Resources

- [Operations Manual](07-operations-manual.md) - Running in production
- [Performance Guide](09-performance-metrics.md) - Optimization tips
- [Demo Scenarios](08-demo-scenarios.md) - Show off your system

---

*"Building AI systems doesn't have to be complex. With the right architecture and tools, you can create magic in hours, not months."* - Happy Developer