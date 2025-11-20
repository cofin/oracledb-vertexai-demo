# Adapter Pattern

## Overview

The Adapter Pattern in this project is implemented through **SQLSpec's AsyncDriverAdapterBase**, which provides a unified async interface to Oracle Database. The adapter handles connection pooling, transaction management, and automatic type conversion (including Oracle VECTOR types).

## Structure

```
SQLSpec Architecture:
┌─────────────────────────────────────┐
│  Application Services               │
│  (ProductService, CacheService)     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  AsyncDriverAdapterBase             │
│  (Abstract interface)               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  OracleAsyncDriver                  │
│  (Oracle-specific implementation)   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  python-oracledb                    │
│  (Oracle database driver)           │
└─────────────────────────────────────┘
```

## AsyncDriverAdapterBase Interface

**From**: `sqlspec.driver.AsyncDriverAdapterBase`

```python
from sqlspec.driver import AsyncDriverAdapterBase
from typing import Any

class AsyncDriverAdapterBase:
    """Abstract base adapter for async database operations."""

    # Query operations
    async def select(
        self,
        statement: str,
        *,
        schema_type: type[SchemaT] | None = None,
        **params: Any,
    ) -> list[SchemaT] | list[dict[str, Any]]:
        """Execute SELECT and return all rows."""
        ...

    async def select_one_or_none(
        self,
        statement: str,
        *,
        schema_type: type[SchemaT] | None = None,
        **params: Any,
    ) -> SchemaT | dict[str, Any] | None:
        """Execute SELECT and return one row or None."""
        ...

    async def select_one(
        self,
        statement: str,
        *,
        schema_type: type[SchemaT] | None = None,
        **params: Any,
    ) -> SchemaT | dict[str, Any]:
        """Execute SELECT and return exactly one row."""
        ...

    async def select_value(
        self,
        statement: str,
        **params: Any,
    ) -> Any:
        """Execute SELECT and return single scalar value."""
        ...

    async def select_with_total(
        self,
        statement: str,
        *,
        schema_type: type[SchemaT] | None = None,
        **params: Any,
    ) -> tuple[list[SchemaT], int]:
        """Execute SELECT with total count for pagination."""
        ...

    # Mutation operations
    async def execute(
        self,
        statement: str,
        **params: Any,
    ) -> ExecutionResult:
        """Execute INSERT, UPDATE, DELETE, or DDL."""
        ...

    # Transaction management
    async def begin(self) -> None:
        """Begin transaction."""
        ...

    async def commit(self) -> None:
        """Commit transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback transaction."""
        ...
```

## Oracle-Specific Adapter

**File**: `/home/cody/code/g/oracledb-vertexai-demo/app/config.py`

```python
from sqlspec.adapters.oracledb import OracleAsyncConfig
from sqlspec.base import SQLSpec

# Create SQLSpec manager (singleton)
db_manager = SQLSpec()

# Create Oracle configuration
db = _settings.db.create_config()

# Register configuration with manager
db_manager.add_config(db)

# Load SQL files for named queries (optional)
db_manager.load_sql_files(BASE_DIR / "db" / "sql")
```

### Oracle Configuration

**File**: `/home/cody/code/g/oracledb-vertexai-demo/app/lib/settings.py`

```python
from sqlspec.adapters.oracledb import OracleAsyncConfig

class DatabaseSettings:
    """Oracle Database connection settings."""

    USER: str = "app"
    PASSWORD: str = "super-secret"
    HOST: str = "localhost"
    PORT: str = "1521"
    SERVICE_NAME: str = "FREEPDB1"
    DSN: str = f"{HOST}:{PORT}/{SERVICE_NAME}"
    POOL_MIN_SIZE: int = 5
    POOL_MAX_SIZE: int = 20
    POOL_TIMEOUT: int = 30
    POOL_RECYCLE: int = 300

    def create_config(self) -> OracleAsyncConfig:
        """Create Oracle database configuration."""
        pool_config = {
            "user": self.USER,
            "password": self.PASSWORD,
            "dsn": self.DSN,
            "min": self.POOL_MIN_SIZE,
            "max": self.POOL_MAX_SIZE,
        }

        return OracleAsyncConfig(
            pool_config=pool_config,
            migration_config={
                "version_table_name": "migrations",
                "script_location": self.MIGRATION_PATH,
                "project_root": BASE_DIR,
                "include_extensions": ["adk", "litestar"],
            },
            extension_config={
                "adk": {
                    "session_table": "adk_sessions",
                    "events_table": "adk_events",
                },
                "litestar": {
                    "session_table": "app_session",
                },
            },
        )
```

## Dependency Injection Provider

**File**: `/home/cody/code/g/oracledb-vertexai-demo/app/server/providers.py`

```python
from collections.abc import AsyncIterable
from dishka import Provider, Scope, provide
from sqlspec.adapters.oracledb import OracleAsyncConfig
from sqlspec.base import SQLSpec
from sqlspec.driver import AsyncDriverAdapterBase

class SQLSpecProvider(Provider):
    """Provides SQLSpec database sessions with proper lifecycle."""

    @provide(scope=Scope.APP)
    def get_sqlspec_manager(self) -> SQLSpec:
        """Provide SQLSpec manager singleton."""
        return db_manager

    @provide(scope=Scope.APP)
    def get_database_config(self) -> OracleAsyncConfig:
        """Provide database configuration singleton."""
        return db

    @provide(scope=Scope.REQUEST)
    async def get_db_session(
        self,
        manager: SQLSpec,
        config: OracleAsyncConfig,
    ) -> AsyncIterable[AsyncDriverAdapterBase]:
        """Provide SQLSpec async database session.

        Each HTTP request gets its own session which is automatically
        returned to the pool when the request completes.
        """
        async with manager.provide_session(config) as session:
            yield session
```

## Using the Adapter

### In Service Classes

```python
from sqlspec.driver import AsyncDriverAdapterBase
from app.schemas import Product

class ProductService:
    """Service using the adapter."""

    def __init__(self, driver: AsyncDriverAdapterBase) -> None:
        """Initialize with adapter."""
        self.driver = driver

    async def get_by_id(self, product_id: int) -> Product | None:
        """Get product using adapter."""
        return await self.driver.select_one_or_none(
            "SELECT * FROM product WHERE id = :id",
            id=product_id,
            schema_type=Product,
        )
```

### In Controller Handlers

```python
from litestar import get
from litestar.response import Response
from sqlspec.driver import AsyncDriverAdapterBase
from app.lib.di import Inject, inject

@get("/health/db")
@inject(signature_types=(AsyncDriverAdapterBase,))
async def db_health_check(
    driver: Inject[AsyncDriverAdapterBase],
) -> Response:
    """Check database connectivity using adapter."""
    result = await driver.select_value("SELECT 1 FROM dual")
    return Response({"status": "healthy", "result": result})
```

## When to Use

### Use AsyncDriverAdapterBase When:

1. **Type Hints**: You need generic typing that works with any SQLSpec driver
2. **Testing**: You want to mock the database layer
3. **Portability**: Code might need to work with different database adapters
4. **Service Base Classes**: Abstract services that don't care about specific DB

### Use OracleAsyncDriver When:

1. **Oracle-Specific Features**: You need Oracle-specific functionality
2. **Type Safety**: You want strict typing for Oracle operations
3. **Controller Handlers**: Direct database access in controllers

### Don't Use the Adapter Directly When:

1. **Business Logic**: Use service classes instead
2. **Simple Queries**: Use ORM/schema classes if appropriate
3. **External APIs**: Wrong abstraction for non-database operations

## Key Features

### 1. Automatic Type Conversion

```python
# SQLSpec automatically handles:
# - list[float] ↔ Oracle VECTOR type
# - dict ↔ Oracle JSON type
# - datetime ↔ Oracle TIMESTAMP
# - Pydantic models ↔ dict ↔ table rows

# Vector example
embedding: list[float] = [0.1] * 768
await driver.execute(
    "UPDATE product SET embedding = :emb WHERE id = :id",
    emb=embedding,  # Automatically converted to VECTOR
    id=1,
)

# Retrieve vector
result = await driver.select_one_or_none(
    "SELECT embedding FROM product WHERE id = :id",
    id=1,
)
embedding: list[float] = result["embedding"]  # Automatically list[float]
```

### 2. Connection Pooling

```python
# Automatic pool management - no manual connection handling needed

# Each request gets a session from the pool
async with manager.provide_session(config) as session:
    # Session is from pool
    await session.select("SELECT * FROM product")
    # Session auto-returned to pool after context exit

# Pool configuration
pool_config = {
    "min": 5,        # Minimum connections
    "max": 20,       # Maximum connections
    "timeout": 30,   # Connection timeout (seconds)
}
```

### 3. Transaction Management

```python
# Automatic transaction handling
async with driver.begin_transaction():
    await driver.execute("INSERT INTO product ...")
    await driver.execute("UPDATE metrics ...")
    # Auto-commits on success, auto-rollbacks on exception

# Manual transaction control
await driver.begin()
try:
    await driver.execute("INSERT ...")
    await driver.commit()
except Exception:
    await driver.rollback()
    raise
```

### 4. Parameter Binding

```python
# Named parameters (Oracle style)
await driver.select(
    "SELECT * FROM product WHERE category = :cat AND price > :min_price",
    cat="Coffee",
    min_price=10.0,
)

# Dict parameters
params = {"cat": "Coffee", "min_price": 10.0}
await driver.select(
    "SELECT * FROM product WHERE category = :cat AND price > :min_price",
    **params,
)
```

## Best Practices

1. **Inject the adapter** via Dishka DI, don't create instances manually
2. **Use in services** not directly in controllers
3. **Leverage type hints** with `AsyncDriverAdapterBase` for generics
4. **Let SQLSpec handle types** - don't manual convert vectors, JSON, etc.
5. **Use context managers** for transactions
6. **Don't hold connections** - let the pool manage lifecycle

## Common Patterns

### Service with Adapter

```python
from sqlspec.driver import AsyncDriverAdapterBase

class MyService:
    def __init__(self, driver: AsyncDriverAdapterBase) -> None:
        self.driver = driver

    async def my_operation(self) -> Result:
        return await self.driver.select_one(
            "SELECT * FROM my_table WHERE id = :id",
            id=123,
            schema_type=MySchema,
        )
```

### Controller with Adapter

```python
from litestar import post
from sqlspec.driver import AsyncDriverAdapterBase
from app.lib.di import Inject, inject

@post("/direct-query")
@inject(signature_types=(AsyncDriverAdapterBase,))
async def direct_query(
    driver: Inject[AsyncDriverAdapterBase],
    data: QueryRequest,
) -> QueryResponse:
    """Direct database access in controller (use sparingly)."""
    result = await driver.select_value(
        "SELECT COUNT(*) FROM product WHERE category = :cat",
        cat=data.category,
    )
    return QueryResponse(count=result)
```

### Testing with Mock Adapter

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_driver() -> AsyncMock:
    """Mock adapter for testing."""
    driver = AsyncMock(spec=AsyncDriverAdapterBase)
    driver.select_one_or_none.return_value = {"id": 1, "name": "Test"}
    return driver

async def test_service_with_mock(mock_driver):
    """Test service with mocked adapter."""
    service = MyService(mock_driver)
    result = await service.get_by_id(1)

    mock_driver.select_one_or_none.assert_called_once()
    assert result["name"] == "Test"
```

## Common Gotchas

1. **Don't create drivers manually**: Use DI injection
   ```python
   # BAD
   driver = OracleAsyncDriver(config)

   # GOOD
   def __init__(self, driver: Inject[AsyncDriverAdapterBase]) -> None:
       self.driver = driver
   ```

2. **Oracle case sensitivity**: Use quoted identifiers
   ```python
   # BAD: Returns "ID", "NAME" (uppercase)
   SELECT id, name FROM product

   # GOOD: Returns "id", "name" (lowercase as expected)
   SELECT id AS "id", name AS "name" FROM product
   ```

3. **Connection lifecycle**: Don't store driver references across requests
   ```python
   # BAD: Driver tied to request scope
   class GlobalService:
       driver = None  # Don't do this!

   # GOOD: Inject per-request
   class MyService:
       def __init__(self, driver: AsyncDriverAdapterBase) -> None:
           self.driver = driver  # Fresh driver per request
   ```

4. **Transaction nesting**: Don't nest transactions
   ```python
   # BAD: Nested transactions not supported
   await driver.begin()
   await driver.begin()  # Error!

   # GOOD: One transaction at a time
   async with driver.begin_transaction():
       await operation1()
       await operation2()
   ```
