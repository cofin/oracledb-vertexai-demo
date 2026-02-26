# Litestar Framework Guide

Comprehensive guide to building async web applications with Litestar framework, including dependency injection, HTMX integration, and Oracle Database connectivity patterns.

## Table of Contents

- [Overview](#overview)
- [Quick Reference](#quick-reference)
- [Installation and Setup](#installation-and-setup)
- [Dependency Injection](#dependency-injection)
- [Controllers and Routing](#controllers-and-routing)
- [HTMX Integration](#htmx-integration)
- [Plugin System](#plugin-system)
- [Request Validation](#request-validation)
- [Response Types](#response-types)
- [Exception Handling](#exception-handling)
- [ASGI Lifecycle](#asgi-lifecycle)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

**Litestar** is a powerful, flexible ASGI framework for building high-performance Python web applications.

**Key Features**:

- **Async-first**: Built on modern async/await patterns
- **Type-safe**: Full type annotation support with runtime validation
- **Dependency Injection**: Powerful DI system with async generators
- **Plugin System**: Extensible architecture (SQLSpec, HTMX, OpenAPI)
- **Performance**: One of the fastest Python web frameworks
- **Developer Experience**: Excellent IDE support and error messages

**This Application Stack**:

```
Browser (HTMX)
    ↓
Litestar (Controllers + DI)
    ↓
SQLSpec Plugin (Session Management)
    ↓
Oracle Database 23ai
```

## Quick Reference

| Feature             | Pattern                        | Example                                                |
| ------------------- | ------------------------------ | ------------------------------------------------------ |
| Controller          | Class with `@get/@post`        | `class ProductController(Controller)`                  |
| Dependency          | Async generator with `yield`   | `async def provide_service() -> AsyncGenerator`        |
| Register dependency | `Provide()` in controller      | `dependencies = {"service": Provide(provide_service)}` |
| Route parameter     | Function parameter             | `async def get_product(product_id: int)`               |
| Request body        | `Annotated[Schema, Body(...)]` | Validated request data                                 |
| HTMX request        | `HTMXRequest` parameter        | Access HTMX headers                                    |
| HTMX response       | `HTMXTemplate` return          | Render partial or full page                            |
| Error handling      | Raise `HTTPException`          | Custom error responses                                 |
| Startup hook        | `on_startup=[func]`            | Initialize resources                                   |

## Installation and Setup

### Installation

```bash
# Install Litestar with all features
pip install "litestar[standard]>=2.0"

# Install HTMX plugin
pip install "litestar-htmx>=0.1"

# Install SQLSpec plugin
pip install "litestar-sqlspec>=0.1"
```

### Basic App Structure

```python
from litestar import Litestar, get

@get("/")
async def index() -> dict[str, str]:
    return {"message": "Hello, World!"}

app = Litestar(route_handlers=[index])
```

### Application Factory Pattern

**Location**: `app/server/app.py`

```python
from litestar import Litestar
from litestar.logging import LoggingConfig
from litestar.plugins.htmx import HTMXPlugin
from litestar.plugins.sqlspec import SQLSpecPlugin
from litestar.static_files import create_static_files_router

from app.config import db, sqlspec
from app.server.controllers import CoffeeChatController
from app.lib.settings import get_settings

def create_app() -> Litestar:
    """Create and configure the Litestar application."""
    settings = get_settings()

    # Static files router
    static_router = create_static_files_router(
        path="/static",
        directories=["app/server/static"],
    )

    return Litestar(
        route_handlers=[
            CoffeeChatController,
            static_router,
        ],
        plugins=[
            sqlspec,  # SQLSpec for database
            HTMXPlugin(),  # HTMX support
        ],
        debug=settings.app.DEBUG,
        logging_config=LoggingConfig(
            loggers={
                "app": {
                    "level": "INFO",
                    "handlers": ["queue_listener"],
                }
            }
        ),
        on_startup=[on_startup],
        on_shutdown=[on_shutdown],
    )

async def on_startup() -> None:
    """Application startup tasks."""
    logger.info("application_startup")

async def on_shutdown() -> None:
    """Application shutdown tasks."""
    logger.info("application_shutdown")
```

## Dependency Injection

Litestar's DI system uses **async generators** for automatic resource management.

### Service Provider Pattern

**Location**: `app/server/deps.py`

```python
from typing import AsyncGenerator, TypeVar, Callable
from app.config import db, sqlspec
from app.services.products import ProductService

T = TypeVar("T")

def create_service_provider(service_cls: type[T]) -> Callable[..., AsyncGenerator[T, None]]:
    """Create generic service provider with database session."""

    async def provider() -> AsyncGenerator[T, None]:
        async with sqlspec.provide_session(db) as session:
            yield service_cls(session)

    return provider

# Create providers
provide_product_service = create_service_provider(ProductService)
provide_chat_service = create_service_provider(ChatService)
provide_metrics_service = create_service_provider(MetricsService)
```

**How it works**:

1. Request arrives
2. Litestar calls `provider()` function
3. Session is created via `sqlspec.provide_session(db)`
4. Service instance is yielded
5. Request handler executes
6. Control returns to provider
7. Session is automatically closed

### Custom Provider with Multiple Dependencies

```python
from app.services.vertex_ai import VertexAIService
from app.services.cache import CacheService

async def provide_vertex_ai_service() -> AsyncGenerator[VertexAIService, None]:
    """Provide Vertex AI service with cache support."""
    async with sqlspec.provide_session(db) as session:
        cache_service = CacheService(session)
        vertex_service = VertexAIService()
        vertex_service.set_cache(cache_service)
        yield vertex_service
```

### Stateless Provider (No Database)

```python
async def provide_adk_orchestrator() -> AsyncGenerator[ADKOrchestrator, None]:
    """Provide ADK orchestrator (manages own sessions)."""
    from app.services.adk.orchestrator import ADKOrchestrator

    orchestrator = ADKOrchestrator()
    try:
        yield orchestrator
    finally:
        await orchestrator.cleanup()  # Optional cleanup
```

### Using Dependencies in Routes

```python
from litestar import post
from app.services.products import ProductService

@post("/api/search")
async def search_products(
    data: SearchRequest,
    product_service: ProductService,  # Automatically injected
) -> list[Product]:
    """Search products with injected service."""
    return await product_service.search(data.query)
```

## Controllers and Routing

### Controller Pattern

**Location**: `app/server/controllers.py`

```python
from litestar import Controller, get, post
from litestar.di import Provide
from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
from typing import Annotated
from litestar.params import Body
from litestar.enums import RequestEncodingType

from app.server import deps
from app.services.products import ProductService
from app import schemas as s

class CoffeeChatController(Controller):
    """Main application controller."""

    path = "/"  # Base path for all routes

    # Register dependencies at controller level
    dependencies = {
        "product_service": Provide(deps.provide_product_service),
        "vertex_ai_service": Provide(deps.provide_vertex_ai_service),
        "chat_service": Provide(deps.provide_chat_service),
    }

    @get("/")
    async def show_homepage(self) -> HTMXTemplate:
        """Serve homepage."""
        return HTMXTemplate(
            template_name="index.html",
            context={"title": "Cymbal Coffee"}
        )

    @post("/api/chat")
    async def handle_chat(
        self,
        data: Annotated[
            s.ChatMessageRequest,
            Body(media_type=RequestEncodingType.URL_ENCODED)
        ],
        product_service: ProductService,
        request: HTMXRequest,
    ) -> HTMXTemplate:
        """Handle chat message with HTMX."""
        # Process chat...
        response = await process_chat(data.message, product_service)

        return HTMXTemplate(
            template_name="partials/chat_response.html",
            context={"response": response},
            trigger_event="chat:complete",
        )

    @get("/dashboard")
    async def performance_dashboard(
        self,
        metrics_service: MetricsService,
    ) -> HTMXTemplate:
        """Display performance metrics."""
        metrics = await metrics_service.get_dashboard_data()
        return HTMXTemplate(
            template_name="dashboard.html",
            context={"metrics": metrics}
        )
```

### Route Decorators

```python
# GET with path parameter
@get("/products/{product_id:int}")
async def get_product(self, product_id: int, product_service: ProductService) -> Product:
    """Get product by ID."""
    return await product_service.get_by_id(product_id)

# POST with validated body
@post("/products")
async def create_product(
    self,
    data: Annotated[ProductCreate, Body()],
    product_service: ProductService,
) -> Product:
    """Create new product."""
    return await product_service.create(data)

# DELETE
@delete("/products/{product_id:int}")
async def delete_product(self, product_id: int, product_service: ProductService) -> None:
    """Delete product."""
    await product_service.delete(product_id)

# PUT/PATCH
@patch("/products/{product_id:int}")
async def update_product(
    self,
    product_id: int,
    data: Annotated[ProductUpdate, Body()],
    product_service: ProductService,
) -> Product:
    """Update product."""
    return await product_service.update(product_id, data)
```

### Query Parameters

```python
from typing import Annotated
from litestar.params import Parameter

@get("/products")
async def list_products(
    category: Annotated[str | None, Parameter()] = None,
    min_price: Annotated[float | None, Parameter()] = None,
    limit: Annotated[int, Parameter(gt=0, le=100)] = 10,
    product_service: ProductService = None,
) -> list[Product]:
    """List products with optional filters."""
    return await product_service.list(
        category=category,
        min_price=min_price,
        limit=limit
    )
```

## HTMX Integration

### HTMX Request Detection

```python
from litestar.plugins.htmx import HTMXRequest

@get("/products")
async def list_products(request: HTMXRequest) -> HTMXTemplate:
    """Handle both full page and HTMX requests."""

    if request.htmx:
        # HTMX request - return partial
        template = "partials/product_list.html"
    else:
        # Regular request - return full page
        template = "products.html"

    return HTMXTemplate(template_name=template, context={...})
```

### HTMX Response

```python
from litestar.plugins.htmx import HTMXTemplate

@post("/api/add-to-cart")
async def add_to_cart(data: AddToCartRequest) -> HTMXTemplate:
    """Add product to cart with HTMX response."""

    # Process request...

    return HTMXTemplate(
        template_name="partials/cart_badge.html",
        context={"cart_count": cart_count},

        # HTMX-specific options
        push_url="/cart",  # Update browser URL
        trigger_event="cart:updated",  # Trigger custom event
        params={"product_id": product_id},  # Event parameters
        retarget="#cart-badge",  # Target different element
        reswap="outerHTML",  # Change swap strategy
        after="settle",  # Timing (settle, swap, none)
    )
```

### HTMX Headers

```python
@get("/status")
async def check_status(request: HTMXRequest) -> dict:
    """Access HTMX headers."""

    # Check if HTMX request
    if request.htmx:
        target = request.htmx.target  # HX-Target
        trigger = request.htmx.trigger  # HX-Trigger
        current_url = request.htmx.current_url  # HX-Current-URL

    return {"status": "ok"}
```

## Plugin System

### SQLSpec Plugin

```python
from litestar.plugins.sqlspec import SQLSpecPlugin
from app.config import DatabaseConfig

# Create database config
db = DatabaseConfig(url="oracle://user:pass@host:1521/service")

# Create SQLSpec plugin
sqlspec = SQLSpecPlugin(db_config=db)

# Register in app
app = Litestar(plugins=[sqlspec])
```

### HTMX Plugin

```python
from litestar.plugins.htmx import HTMXPlugin

app = Litestar(plugins=[HTMXPlugin()])
```

### Custom Plugin

```python
from litestar.plugins import InitPluginProtocol
from litestar.config.app import AppConfig

class CustomPlugin(InitPluginProtocol):
    """Custom application plugin."""

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Called when app is initialized."""
        # Modify app_config
        return app_config

app = Litestar(plugins=[CustomPlugin()])
```

## Request Validation

### Request Body with msgspec

```python
from msgspec import Struct
from typing import Annotated
from litestar.params import Body

class ChatMessageRequest(Struct):
    """Chat message request schema."""
    message: str
    persona: str = "enthusiast"
    use_cache: bool = True

@post("/chat")
async def handle_chat(
    data: Annotated[ChatMessageRequest, Body()],
) -> dict:
    """Type-safe request handling."""
    # data.message is guaranteed to be str
    # data.persona has default value
    return {"received": data.message}
```

### Form Data (URL Encoded)

```python
from litestar.enums import RequestEncodingType

@post("/form")
async def handle_form(
    data: Annotated[
        FormData,
        Body(media_type=RequestEncodingType.URL_ENCODED)
    ],
) -> HTMXTemplate:
    """Handle HTML form submission."""
    return HTMXTemplate(...)
```

### JSON Body

```python
@post("/api/products")
async def create_product(
    data: Annotated[
        ProductCreate,
        Body(media_type=RequestEncodingType.JSON)
    ],
) -> Product:
    """JSON API endpoint."""
    return await product_service.create(data)
```

## Response Types

### Template Response

```python
from litestar.plugins.htmx import HTMXTemplate

@get("/")
async def index() -> HTMXTemplate:
    return HTMXTemplate(
        template_name="index.html",
        context={"title": "Home"}
    )
```

### JSON Response (Automatic)

```python
from msgspec import Struct

class ProductResponse(Struct):
    id: int
    name: str
    price: float

@get("/api/products/{product_id:int}")
async def get_product(product_id: int) -> ProductResponse:
    """Returns JSON automatically."""
    return ProductResponse(id=product_id, name="Coffee", price=24.99)
```

### File Response

```python
from litestar.response import File

@get("/download")
async def download_report() -> File:
    return File(
        path="reports/data.csv",
        filename="report.csv",
        headers={"Cache-Control": "no-cache"}
    )
```

### Streaming Response

```python
from litestar.response import Stream

@get("/stream")
async def stream_data() -> Stream:
    async def generate():
        for i in range(10):
            yield f"data: {i}\n\n"
            await asyncio.sleep(0.1)

    return Stream(
        iterator=generate(),
        media_type="text/event-stream"
    )
```

### Redirect Response

```python
from litestar.response import Redirect

@get("/old-url")
async def redirect_old() -> Redirect:
    return Redirect(path="/new-url")
```

## Exception Handling

### HTTP Exceptions

```python
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_404_NOT_FOUND

@get("/products/{product_id:int}")
async def get_product(product_id: int, product_service: ProductService) -> Product:
    product = await product_service.get_by_id(product_id)

    if not product:
        raise HTTPException(
            detail=f"Product {product_id} not found",
            status_code=HTTP_404_NOT_FOUND
        )

    return product
```

### Custom Exception Handler

```python
from litestar import Request, Response
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
import structlog

logger = structlog.get_logger()

def handle_database_error(request: Request, exc: DatabaseError) -> Response:
    """Handle database errors gracefully."""
    logger.error("database_error", error=str(exc), path=request.url.path)

    return Response(
        content={"error": "Database error occurred", "detail": str(exc)},
        status_code=HTTP_500_INTERNAL_SERVER_ERROR
    )

# Register in app
app = Litestar(
    exception_handlers={
        DatabaseError: handle_database_error,
    }
)
```

### Validation Error Handler

```python
from litestar.exceptions import ValidationException

def handle_validation_error(request: Request, exc: ValidationException) -> Response:
    """Handle validation errors with details."""
    return Response(
        content={
            "error": "Validation failed",
            "details": exc.extra
        },
        status_code=400
    )

app = Litestar(
    exception_handlers={
        ValidationException: handle_validation_error
    }
)
```

## ASGI Lifecycle

### Startup and Shutdown Hooks

```python
from litestar import Litestar
import structlog

logger = structlog.get_logger()

async def on_startup() -> None:
    """Initialize resources on startup."""
    logger.info("application_startup")
    # Initialize connections
    # Warm caches
    # Start background tasks

async def on_shutdown() -> None:
    """Cleanup resources on shutdown."""
    logger.info("application_shutdown")
    # Close connections
    # Cancel background tasks
    # Flush logs

app = Litestar(
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
    route_handlers=[...],
)
```

### Lifespan State

```python
from litestar.datastructures import State
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: Litestar):
    """Manage application lifespan with context manager."""
    # Startup
    app.state.shared_resource = await initialize_resource()

    yield

    # Shutdown
    await app.state.shared_resource.close()

app = Litestar(
    lifespan=[lifespan],
    route_handlers=[...],
)

# Access state in routes
@get("/status")
async def status(state: State) -> dict:
    resource = state.shared_resource
    return {"status": "ok"}
```

## Best Practices

### 1. Always Use Async

```python
# ✅ GOOD
@get("/")
async def index() -> dict:
    return {"status": "ok"}

# ❌ BAD (blocks event loop)
@get("/")
def index() -> dict:
    return {"status": "ok"}
```

### 2. Use Dependency Injection

```python
# ✅ GOOD
@get("/products")
async def list_products(product_service: ProductService) -> list[Product]:
    return await product_service.list()

# ❌ BAD (manual instantiation)
@get("/products")
async def list_products() -> list[Product]:
    service = ProductService(session)  # How do you get session?
    return await service.list()
```

### 3. Use Type Annotations

```python
# ✅ GOOD (type-safe)
@post("/products")
async def create_product(
    data: Annotated[ProductCreate, Body()],
    product_service: ProductService,
) -> Product:
    return await product_service.create(data)

# ❌ BAD (no validation)
@post("/products")
async def create_product(data: dict) -> dict:
    return await product_service.create(data)
```

### 4. Handle Errors Gracefully

```python
# ✅ GOOD
@get("/products/{product_id:int}")
async def get_product(product_id: int, product_service: ProductService) -> Product:
    product = await product_service.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# ❌ BAD (generic error)
@get("/products/{product_id:int}")
async def get_product(product_id: int, product_service: ProductService) -> Product:
    return await product_service.get_by_id(product_id)  # May return None
```

### 5. Use Controllers for Organization

```python
# ✅ GOOD
class ProductController(Controller):
    path = "/products"
    dependencies = {"service": Provide(provide_product_service)}

    @get("/")
    async def list_products(self, service: ProductService) -> list[Product]:
        return await service.list()

    @post("/")
    async def create_product(self, data: ProductCreate, service: ProductService) -> Product:
        return await service.create(data)

# ❌ BAD (flat route handlers)
@get("/products")
async def list_products() -> list[Product]: ...

@post("/products")
async def create_product() -> Product: ...
```

## Troubleshooting

### Issue: Dependency Not Injected

**Symptom**: `TypeError: missing required argument: 'product_service'`

**Solution**:

```python
# Register dependency in controller
class MyController(Controller):
    dependencies = {
        "product_service": Provide(deps.provide_product_service)
    }

    @get("/")
    async def handler(self, product_service: ProductService):
        pass
```

### Issue: Session Not Closing

**Symptom**: Database connections not released

**Solution**: Always use async context manager:

```python
async def provide_service() -> AsyncGenerator[Service, None]:
    async with sqlspec.provide_session(db) as session:
        yield Service(session)  # Session auto-closes when generator exits
```

### Issue: HTMX Response Not Swapping

**Symptom**: HTMX doesn't update page

**Solution**: Ensure template path is correct:

```python
return HTMXTemplate(
    template_name="partials/response.html",  # Check file exists
    context={...}
)
```

## See Also

- [SQLSpec Patterns](sqlspec-patterns.md) - Database service patterns
- [Architecture Overview](architecture.md) - System design
- [Oracle Performance](oracle-performance.md) - Connection pooling

## Resources

- Litestar Documentation: https://docs.litestar.dev/
- HTMX Plugin: https://docs.litestar.dev/latest/reference/plugins/htmx.html
- SQLSpec Plugin: https://docs.litestar.dev/latest/reference/plugins/sqlspec.html
