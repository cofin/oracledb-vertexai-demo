# Cymbal Coffee Architecture

This guide provides a high-level map of the Cymbal Coffee system architecture, package boundaries, and dependency injection patterns.

## System Shape

Cymbal Coffee is a two-page Litestar web application served by the Granian ASGI server.
- `/` is the primary chat route.
- `/explore` is the vector search and database query explain plan viewer.
- `/api/chat/stream` is the Server-Sent Event stream from the ADK workflow.
- `/api/vector-demo` returns HTMX partials or JSON search results.
- `/api/explain-plan` returns execution plans for the vector query.
- `/api/stores/{store_id}/inventory` returns HTML partials for store inventory.

The application follows a clean request flow:
```text
browser
  -> Litestar controllers
  -> Dishka request scope
  -> domain services
  -> SQLSpec Oracle driver and Google GenAI client
  -> Oracle 26ai, Vertex AI, ADK session store
```

## Package & Source Layout

```text
src/app/
  cli/                  # Click commands and manage.py command modules
  db/
    migrations/         # SQLSpec database schema migrations
    sql/                # Named SQL queries loaded by db_manager
    fixtures/           # Committed compressed fixtures data
  domain/
    chat/               # Chat intent, ADK flow, and streaming session modules
      controllers/
      schemas/
      services/
    products/           # Product search, store inventory, and Vertex AI services
      controllers/
      schemas/
      services/
    system/             # Health check, metrics, and response cache
      controllers/
      schemas/
      services/
    web/                # Web UI templates and controllers
      controllers/
      templates/
  ioc.py                # Dishka container configuration
  config.py             # App instantiation, session settings, and logging configuration
  server/               # Litestar application factory and plugin registry
```

### Domain Boundaries
Behavior belongs within domain packages under `domain/<domain_name>/`.
- Cross-domain integration should happen via public package exports or by injecting request-scoped services.
- **Do not** write deep relative imports into other domains' private subpackages.

## Dependency Injection (Dishka)

We use Dishka for dependency injection. Containers are configured in `src/app/ioc.py`.

### Providers
We register three user providers at application boot:
1. **`LitestarPersistenceProvider`**:
   - Scope: APP -> `OracleAsyncConfig`
   - Scope: REQUEST -> `OracleAsyncDriver`
2. **`IntegrationsProvider`**:
   - Scope: APP -> Google GenAI `Client`
   - Scope: APP -> `OracleAsyncADKStore`
   - Scope: APP -> `SQLSpecSessionService`
   - Scope: APP -> `FlashLiteIntentClassifier`, `PersonaManager`, `ADKRunner`
3. **`DomainServiceProvider`**:
   - Scope: REQUEST -> `ProductService`, `StoreService`, `CacheService`, `MetricsService`, `AgentToolsService`
   - Scope: REQUEST -> `VertexAIService`, `OracleVectorSearchService`

### DI Annotations Rule
Do not use `from __future__ import annotations` in `src/app/ioc.py` or any provider files. Dishka parses type annotations at runtime to resolve dependencies; postponed annotations prevent container construction.

### Dependency Injection Usage
Controllers and services inject their dependencies using the `Inject` type hint:
```python
from app.lib.di import Inject
from app.domain.products.services import ProductService

async def list_products(product_service: Inject[ProductService]) -> Response:
    ...
```

## CLI & Entrypoint Boundaries

We maintain a strict boundary between end-user operations and developer utilities:
- **`coffee`:** The production CLI tool. Exposes application operations: `run`, `upgrade` (applies migrations and loads fixtures), `load-fixtures`, `clear-cache`, `model-info`, `bulk-embed`, and `export-fixtures`.
- **`manage.py`:** Developer utility. Exposes framework/infra commands: database migrations (`database upgrade/downgrade`), frontend assets (`assets install`), and other helper groups.

## Detailed Guides Index
For component-specific details, refer to:
- [Oracle Database & SQLSpec](oracle-database.md)
- [ADK Chat Agent Patterns](adk-agent-patterns.md)
- [Store, Inventory & Maps](store-inventory-maps.md)
- [Frontend & UI Development](frontend-ui.md)
- [Testing & Verification](testing-verification.md)
- [Operations & Packaging](operations-packaging.md)
- [Application Settings](settings.md)
