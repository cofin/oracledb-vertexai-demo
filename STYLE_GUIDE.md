# 📖 Oracle + Vertex AI Coffee Demo Style Guide

This guide provides comprehensive patterns and standards for the Oracle Database + Vertex AI Coffee Demo project. It incorporates Advanced Alchemy patterns, Oracle 23AI features, and conference-ready implementation standards.

## 🎯 Project Overview

This is an **Oracle + Vertex AI Coffee Recommendation System** - a conference-ready demo showcasing:

- Oracle 23AI vector search capabilities
- Native Google Vertex AI integration (no LangChain)
- Advanced Alchemy patterns with SQLAlchemy 2.0
- Real-time HTMX interface without build complexity
- Conference demo features with personas and fallbacks

## 🚀 Key Commands

### Development Setup

```bash
# Fresh installation with uv
make install                    # Uses uv for package management
cp .env.example .env           # Configure API keys and Oracle connection
make start-infra               # Start Oracle 23AI + Valkey containers
uv run app database upgrade    # Run Alembic migrations
uv run app database load-fixtures  # Load coffee data
uv run app run                 # Start Litestar server
```

### Common Development Tasks

```bash
# Database Operations
uv run app database upgrade         # Apply migrations
uv run alembic revision --autogenerate -m "Description"  # Create migration
uv run app database reset          # Fresh start

# Testing & Quality
uv run pytest                      # Run tests
make lint                          # Pre-commit checks
make test-all                      # Full test suite

# Demo Operations
uv run app demo reset              # Reset for presentation
uv run app demo set-mode presentation  # Conference mode
```

## 🏗️ Architecture

### Tech Stack

- **Backend**: Litestar + SQLAlchemy 2.0 + Advanced Alchemy + Oracle 23AI
- **Frontend**: HTMX + Tailwind CSS (CDN) - no build system
- **AI**: Native Google Vertex AI (Gemini 2.0 Flash)
- **Database**: Oracle 23AI as complete data platform (vectors, sessions, cache)
- **Cache**: Oracle tables with TTL (no Redis needed)

### Project Structure

```sh
app/                              # Main application
├── db/
│   ├── models.py                # SQLAlchemy models with Advanced Alchemy
│   └── migrations/              # Alembic migrations
├── domain/coffee/
│   ├── controllers.py           # Litestar controllers
│   ├── schemas.py               # msgspec.Struct DTOs (mandatory)
│   ├── services/
│   │   ├── __init__.py         # Existing services
│   │   ├── oracle_services.py  # Oracle-specific services
│   │   ├── vertex_ai.py        # Native Vertex AI service
│   │   ├── recommendation.py   # AI recommendation service
│   │   ├── demo_service.py     # Conference demo controls
│   │   └── fallback_service.py # Offline fallbacks
│   └── templates/
│       ├── ocw.html.j2         # Main chat interface
│       └── partials/           # HTMX components
└── server/
    ├── core.py                 # App configuration
    └── deps.py                 # Dependency injection
```

## 🧪 Testing Standards (Mandatory)

### Test Structure

Follow litestar-fullstack testing patterns with unit/integration separation:

```
tests/
├── conftest.py                    # Main test configuration with anyio
├── unit/
│   ├── conftest.py               # Mock-based fixtures for unit tests
│   └── test_*_unit.py            # Fast unit tests with mocks
├── integration/
│   ├── conftest.py               # Database fixtures for integration tests
│   └── test_*_integration.py     # Full database integration tests
└── .env.testing                  # Test environment configuration
```

### Unit Tests Pattern

```python
"""Unit tests for CompanyService."""
from unittest.mock import AsyncMock
import pytest

from app.services.company import CompanyService
from app.db import models as m


@pytest.mark.anyio
class TestCompanyService:
    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def company_service(self, mock_session: AsyncMock) -> CompanyService:
        return CompanyService(session=mock_session)

    async def test_get_by_name_success(self, company_service: CompanyService) -> None:
        # Mock the service method
        expected_company = m.Company(id=1, name="Test Company")
        company_service.get_one_or_none = AsyncMock(return_value=expected_company)

        result = await company_service.get_by_name("Test Company")

        assert result == expected_company
        company_service.get_one_or_none.assert_called_once_with(name="Test Company")
```

### Integration Tests Pattern

```python
"""Integration tests for CompanyService with real database."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.company import CompanyService
from app.db import models as m


@pytest.mark.anyio
class TestCompanyServiceIntegration:
    async def test_create_company(self, session: AsyncSession) -> None:
        service = CompanyService(session=session)

        company_data = {"name": "Test Coffee Co."}
        company = await service.create(data=company_data)

        assert company.name == "Test Coffee Co."
        assert company.id is not None
```

### Test Configuration

**pytest.ini_options in pyproject.toml:**

```toml
[tool.pytest.ini_options]
addopts = ["-ra", "--ignore", "app/db/migrations"]
filterwarnings = [
    "ignore::DeprecationWarning:pkg_resources",
    "ignore::DeprecationWarning:google.*",
    "ignore::PendingDeprecationWarning",
]
testpaths = ["tests"]
```

**Test Dependencies:**

```toml
test = [
    "pytest", "pytest-asyncio", "pytest-cov", "pytest-mock",
    "pytest-databases[valkey,oracle]", "pytest-sugar", "pytest-xdist"
]
```

### Testing Commands

```bash
# Run unit tests (fast, no database)
uv run pytest tests/unit/ -v

# Run integration tests (with Oracle database)
uv run pytest tests/integration/ -v --oracle

# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=app --cov-report=html
```

## 🎯 Import Patterns (Mandatory)

### Models Import Pattern

Always import models using the `m` alias:

```python
from app.db import models as m

# Usage in services
class CompanyService(SQLAlchemyAsyncRepositoryService[m.Company]):
    class Repo(SQLAlchemyAsyncRepository[m.Company]):
        model_type = m.Company

# Usage in relationships
user: Mapped[m.User] = relationship(back_populates="sessions")
```

### Schema Import Pattern

Import schemas directly and use dot notation:

```python
from app.domain.coffee import schemas

# Usage in controllers
async def create_company(self, data: schemas.CompanyCreate) -> schemas.Company:
    # Implementation
```

### Service Import Pattern

Import services directly for dependency injection:

```python
from app.services.company import CompanyService
from app.services.vertex_ai import VertexAIService
```

## 🔗 Dependency Injection (Mandatory)

### Service Provider Pattern

Use `create_service_provider` for consistent service injection:

```python
# In deps.py
from app.lib.deps import create_service_provider
from app.services.company import CompanyService
from app.db import models as m

provide_company_service = create_service_provider(
    CompanyService,
    load=[
        selectinload(m.Company.products),
    ],
    error_messages={
        "duplicate_key": "Company already exists.",
        "integrity": "Company operation failed."
    },
)
```

### Controller Dependencies

Use inline dependency declarations with `deps` naming:

```python
from litestar import Controller, get, post
from litestar.di import Provide

from app.domain.coffee import deps, schemas


class CompanyController(Controller):
    """Company management controller."""

    dependencies = {
        "company_service": Provide(deps.provide_company_service),
    }

    @get("/companies")
    async def list_companies(
        self,
        company_service: CompanyService,
    ) -> list[schemas.Company]:
        """List all companies."""
        companies = await company_service.list()
        return [schemas.Company.from_orm(company) for company in companies]

    @post("/companies")
    async def create_company(
        self,
        data: schemas.CompanyCreate,
        company_service: CompanyService,
    ) -> schemas.Company:
        """Create new company."""
        company = await company_service.create(data.dict())
        return schemas.Company.from_orm(company)
```

### Dependencies File Structure

Each domain should have a `deps.py` file:

```python
# app/domain/coffee/deps.py
"""Coffee domain dependency providers."""

from app.lib.deps import create_service_provider
from app.services.company import CompanyService
from app.services.product import ProductService
from app.db import models as m

provide_company_service = create_service_provider(CompanyService)
provide_product_service = create_service_provider(
    ProductService,
    load=[selectinload(m.Product.company)],
)
```

## 🔑 Critical Patterns

### Backend Service Layer (Mandatory)

All services MUST follow the Advanced Alchemy pattern with inner `Repo` class:

```python
from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService
from app.db import models as m

class UserSessionService(SQLAlchemyAsyncRepositoryService[m.UserSession]):
    """Oracle session management with Advanced Alchemy."""

    class Repo(SQLAlchemyAsyncRepository[m.UserSession]):
        """Session repository."""
        model_type = m.UserSession

    repository_type = Repo
    match_fields = ["session_id"]  # Fields for get_or_create

    async def create_session(self, user_id: str, ttl_hours: int = 24) -> m.UserSession:
        """Create new session with automatic expiry."""
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        return await self.create({
            "session_id": session_id,
            "user_id": user_id,
            "data": {},
            "expires_at": expires_at
        })

    async def get_active_session(self, session_id: str) -> m.UserSession | None:
        """Get session if not expired."""
        session = await self.get_one_or_none(session_id=session_id)
        if session and session.expires_at > datetime.now(timezone.utc):
            return session
        return None
```

**Service Pattern Rules:**

- Use inner `Repo` class for repository definition
- Repository types: `SQLAlchemyAsyncRepository` or `SQLAlchemyAsyncSlugRepository`
- Implement business logic in service methods, not repository
- Use `match_fields` for get_or_create operations
- Always handle None cases gracefully

### API DTOs with msgspec.Struct (Mandatory)

All API request/response bodies MUST use `msgspec.Struct`:

```python
import msgspec
from typing import TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from uuid import UUID

class CoffeeChatMessage(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Chat message input DTO."""
    message: str

class UserSessionRead(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Session response payload."""
    id: UUID
    session_id: str
    user_id: str
    data: dict
    expires_at: datetime
    created_at: datetime

class SearchMetricsCreate(msgspec.Struct, gc=False, array_like=True, omit_defaults=True):
    """Metrics creation payload."""
    query_id: str
    user_id: str | None = None
    search_time_ms: float
    embedding_time_ms: float
    oracle_time_ms: float
    similarity_score: float | None = None
    result_count: int
```

**msgspec.Struct Rules:**

- Naming: Suffix with `Create`, `Read`, `Update`, `Payload`
- Options: Always use `gc=False`, `array_like=True`, `omit_defaults=True`
- NEVER use raw dicts or Pydantic for API DTOs
- NEVER use `@dataclass` with msgspec.Struct
- Use TYPE_CHECKING for forward references

### Database Models (SQLAlchemy 2.0)

All models MUST use SQLAlchemy 2.0 patterns:

```python
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import String, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from advanced_alchemy.base import UUIDAuditBase, BigIntAuditBase

class UserSession(UUIDAuditBase):
    """Oracle-native session storage with JSON data."""

    __tablename__ = "user_session"

    session_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    conversations: Mapped[list["ChatConversation"]] = relationship(
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_session_expires", "expires_at"),
        Index("ix_session_user_expires", "user_id", "expires_at"),
    )

class Product(BigIntAuditBase):
    """Product with Oracle vector embeddings."""

    # Existing fields...
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000))

    # Add Oracle 23AI vector field
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(768), nullable=True  # Oracle native vector type
    )
```

**Database Model Rules:**

- Base Classes: Use `UUIDAuditBase` for UUID PKs, `BigIntAuditBase` for integers
- Type Annotations: Always use `Mapped[type]` for all columns
- Relationships: Use `lazy="selectin"` for frequently accessed
- Indexes: Add for foreign keys and query-heavy columns
- JSON Storage: Use Oracle's native JSON type for flexible data

### Oracle 23AI Integration

Leverage Oracle as complete data platform:

```python
class OracleVectorStore:
    """Oracle 23AI vector search integration."""

    async def similarity_search_with_metadata(self, query_vector: list[float], k: int = 5):
        """Combine vector search with relational data in one query."""
        results = await self.db.fetch_all(
            """SELECT p.id, p.name, p.description, p.price,
                      c.name as company_name,
                      VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) as similarity
               FROM products p
               JOIN companies c ON p.company_id = c.id
               WHERE VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) < 0.8
               ORDER BY similarity
               FETCH FIRST :k ROWS ONLY""",
            {"query_vector": query_vector, "k": k}
        )
        return results

class ResponseCacheService(service.SQLAlchemyAsyncRepositoryService[m.ResponseCache]):
    """Oracle response caching with TTL."""

    async def cache_response(self, query: str, response: dict, ttl_minutes: int = 5):
        """Cache with Oracle TTL."""
        cache_key = self._generate_cache_key(query)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

        # Use MERGE for upsert
        await self.db.execute(
            """MERGE INTO response_cache USING dual ON (cache_key = :key)
               WHEN MATCHED THEN
                   UPDATE SET response = :resp, expires_at = :expires
               WHEN NOT MATCHED THEN
                   INSERT (cache_key, response, expires_at)
                   VALUES (:key, :resp, :expires)""",
            {"key": cache_key, "resp": json.dumps(response), "expires": expires_at}
        )
```

### Native Vertex AI Service

Replace LangChain with native implementation:

```python
import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud import aiplatform

class NativeVertexAIService:
    """Native Vertex AI service without LangChain."""

    def __init__(self):
        settings = get_settings()
        vertexai.init(
            project=settings.app.GCP_PROJECT_ID,
            location=settings.app.GCP_LOCATION or "us-central1"
        )

        self.model = GenerativeModel("gemini-2.0-flash-exp")
        self.embedding_model = "text-embedding-004"

    async def generate_content(self, prompt: str, use_cache: bool = True) -> str:
        """Generate content with Oracle caching."""
        if use_cache and self.cache_service:
            cached = await self.cache_service.get_cached_response(prompt)
            if cached:
                return cached.get("content", "")

        response = await self.model.generate_content_async(prompt)
        content = response.text

        if use_cache and self.cache_service:
            await self.cache_service.cache_response(prompt, {"content": content})

        return content
```

### HTMX Controllers

Real-time interface without build complexity:

```python
from litestar import Controller, get, post
from litestar.response import Template, Stream

from app import schemas

@Controller(path="/coffee")
class CoffeeController:
    """Coffee recommendation controller with HTMX."""

    @post("/chat/send")
    async def send_message(
        self,
        data: schemas.CoffeeChatMessage,
        recommendation_service: NativeRecommendationService,
    ) -> Template:
        """Send chat message with Oracle session tracking."""
        response = await recommendation_service.get_recommendation(
            data.message, user_id="demo_user"
        )

        return Template(
            "partials/chat_response.html.j2",
            context={
                "user_message": data.message,
                "ai_response": response.answer,
                "points_of_interest": response.points_of_interest,
                "query_id": response.query_id,
                "metrics": response.search_metrics
            }
        )

    @get("/chat/stream/{query_id:str}")
    async def stream_response(self, query_id: str) -> Stream:
        """Stream AI response using Server-Sent Events."""
        async def generate():
            # Stream response chunks
            async for chunk in self.ai_service.stream_content(prompt):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

        return Stream(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"}
        )
```

### Conference Demo Features

Built-in demo controls and personas:

```python
class DemoControlService:
    """Conference demo control and management."""

    def __init__(self):
        self.demo_personas = {
            "coffee_novice": {
                "name": "Sarah - Coffee Novice",
                "preferences": {"strength": "mild", "complexity": "simple"},
                "sample_queries": [
                    "I want something not too strong",
                    "What's a good beginner coffee?"
                ]
            },
            "coffee_expert": {
                "name": "Dr. Elena - Coffee Expert",
                "preferences": {"strength": "varies", "complexity": "detailed"},
                "sample_queries": [
                    "Natural process Ethiopian with fruit notes",
                    "High altitude Arabica, light roast"
                ]
            }
        }

    async def reset_demo(self) -> dict:
        """Reset all demo data for fresh start."""
        await asyncio.gather(
            self.sessions.cleanup_expired(),
            self.conversations.repository.session.execute(
                delete(m.ChatConversation).where(
                    m.ChatConversation.created_at < datetime.now(timezone.utc)
                )
            ),
            self.cache.cleanup_expired()
        )
        return {"status": "reset_complete"}
```

## 🎨 Frontend Patterns

### HTMX Templates

Simple, server-rendered UI with real-time updates:

```html
<!-- Main template with HTMX -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
<script src="https://unpkg.com/htmx.org/dist/ext/sse.js"></script>

<div id="chat-container" class="chat-container">
  <div id="chat-history">
    <!-- Messages appear here -->
  </div>

  <form
    hx-post="/coffee/chat/send"
    hx-target="#chat-history"
    hx-swap="beforeend"
  >
    <input name="message" required />
    <button type="submit">Send ☕</button>
  </form>
</div>

<!-- Partial templates -->
<!-- partials/chat_response.html.j2 -->
<div class="message user">{{ user_message }}</div>
<div
  class="message assistant"
  hx-ext="sse"
  sse-connect="/coffee/chat/stream/{{ query_id }}"
>
  <div class="content" sse-swap="message">
    <span class="typing-indicator">AI is thinking...</span>
  </div>
</div>
```

## 📋 Critical Workflow Requirements

### Database Migrations

- **Generate**: `uv run alembic revision --autogenerate -m "Description"`
- **Apply**: `uv run alembic upgrade head`
- **Never**: Edit migrations manually or use raw SQL for schema changes

### Testing Standards

- **Always**: Test new Oracle services with proper mocking
- **Always**: Verify vector search performance < 500ms
- **Always**: Test fallback modes for conference reliability
- **Never**: Skip integration tests for demo features

### Code Quality

- **Always**: Run `make lint` before committing
- **Always**: Use type annotations with `Mapped[type]`
- **Always**: Handle None cases in services
- **Never**: Use raw dicts for API responses

## 🔒 Security & Performance

### Oracle Connection Pooling

```python
oracle_config = OraclePoolConfig(
    min_connections=5,
    max_connections=20,
    increment=2,
    connection_timeout=30,
    homogeneous=True
)
```

### Rate Limiting

```python
from litestar.middleware.rate_limit import RateLimitConfig

RateLimitConfig(
    rate_limit=("rate_limit", 100),  # 100 requests/min
    rate_limit_policy="user_id"
).middleware
```

### Error Handling

```python
try:
    response = await recommendation_service.get_recommendation(query)
except VertexAIError:
    # Fallback to cached responses
    response = await fallback_service.get_fallback_response(query)
except OracleError:
    # Use offline mode
    response = await fallback_service.get_offline_response(query)
```

## 🚨 Conference-Specific Requirements

### Demo Modes

- **normal**: Standard operation with 5-minute cache
- **presentation**: Extended cache, slight delays for effect
- **showcase**: Highlight Oracle features, show metrics
- **offline**: Use fallback responses only

### Performance Targets

- Vector search: < 50ms
- AI response start: < 500ms
- Total round trip: < 2s
- Cache hit rate: > 80%

### Fallback Priority

1. Try Vertex AI with Oracle cache
2. Fall back to cached embeddings
3. Use pre-generated responses
4. Show offline demo mode

## 📝 Naming Conventions

### Files

- Services: `{domain}_service.py` (e.g., `oracle_services.py`)
- Controllers: Feature-based naming
- Templates: `{feature}.html.j2`, partials in `partials/`

### Classes

- Services: `{Model}Service` with inner `Repo`
- DTOs: `{Model}{Action}` (e.g., `UserSessionCreate`)
- Controllers: `{Feature}Controller`

### Database

- Tables: Snake_case singular (e.g., `user_session`)
- Indexes: `ix_{table}_{columns}`
- Foreign keys: `{table}_id`

## 🎯 Implementation Checklist

When implementing new features:

- [ ] Create SQLAlchemy model with proper base class
- [ ] Generate and apply migration
- [ ] Create msgspec.Struct DTOs for API
- [ ] Implement service with inner Repo pattern
- [ ] Add controller endpoints with HTMX
- [ ] Create partial templates for UI updates
- [ ] Add to dependency injection
- [ ] Write integration tests
- [ ] Test fallback scenarios
- [ ] Document in implementation guide

---

**This style guide ensures consistent, conference-ready code that showcases Oracle 23AI + Vertex AI capabilities while following Advanced Alchemy best practices.**
