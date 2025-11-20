# Service Pattern

## Overview

The Service Pattern in this project uses **SQLSpec** for type-safe, async database operations with Oracle 23ai. All services inherit from `SQLSpecService` base class, which provides common database operations, transaction management, and filtering capabilities.

## Structure

```
app/services/
├── base.py              # SQLSpecService base class
├── _product.py          # ProductService example
├── _cache.py            # CacheService example
├── _vertex_ai.py        # VertexAIService (non-database service)
└── __init__.py          # Service exports
```

## Base Service Class

**File**: `/home/cody/code/g/oracledb-vertexai-demo/app/services/base.py`

```python
from sqlspec.driver import AsyncDriverAdapterBase
from sqlspec.core.filters import LimitOffsetFilter, OffsetPagination

class SQLSpecService:
    """Base service class for SQLSpec operations."""

    def __init__(self, driver: AsyncDriverAdapterBase) -> None:
        """Initialize the service."""
        self.driver = driver

    async def paginate(
        self,
        statement: Statement | QueryBuilder,
        /,
        *parameters: StatementParameters | StatementFilter,
        schema_type: type[SchemaT],
        statement_config: StatementConfig | None = None,
        **kwargs: Any,
    ) -> OffsetPagination[SchemaT]:
        """Paginate the data."""
        results, total = await self.driver.select_with_total(
            statement,
            *parameters,
            schema_type=schema_type,
            statement_config=statement_config,
            **kwargs,
        )
        limit_offset = self.find_filter(LimitOffsetFilter, parameters)
        offset = limit_offset.offset if limit_offset else 0
        limit = limit_offset.limit if limit_offset else 10
        return OffsetPagination[SchemaT](items=results, limit=limit, offset=offset, total=total)

    async def get_or_404(
        self,
        statement: Statement | QueryBuilder,
        /,
        *parameters: StatementParameters,
        schema_type: type[SchemaT],
        error_message: str | None = None,
        statement_config: StatementConfig | None = None,
        **kwargs: Any,
    ) -> SchemaT:
        """Get a single record or raise 404 error if not found."""
        result = await self.driver.select_one_or_none(
            statement,
            *parameters,
            schema_type=schema_type,
            statement_config=statement_config,
            **kwargs,
        )
        if result is None:
            raise ValueError(error_message or "Record not found")
        return result

    async def exists(
        self,
        statement: Statement | QueryBuilder,
        /,
        *parameters: StatementParameters,
        statement_config: StatementConfig | None = None,
        **kwargs: Any,
    ) -> bool:
        """Check if a record exists."""
        result = await self.driver.select_one_or_none(
            statement,
            *parameters,
            statement_config=statement_config,
            **kwargs,
        )
        return result is not None

    # Transaction management
    async def begin(self) -> None:
        """Begin a database transaction."""
        await self.driver.begin()

    async def commit(self) -> None:
        """Commit the current database transaction."""
        await self.driver.commit()

    async def rollback(self) -> None:
        """Rollback the current database transaction."""
        await self.driver.rollback()

    @asynccontextmanager
    async def begin_transaction(self) -> AsyncIterator[None]:
        """Context manager for database transactions."""
        await self.begin()
        try:
            yield
        except Exception:
            await self.rollback()
            raise
        else:
            await self.commit()
```

## Database Service Example

**File**: `/home/cody/code/g/oracledb-vertexai-demo/app/services/_product.py`

```python
from typing import Any
from app.schemas import Product
from app.services.base import SQLSpecService

class ProductService(SQLSpecService):
    """Handles database operations for products using SQLSpec patterns."""

    async def get_all(self) -> list[Product]:
        """Get all products."""
        results: list[Product] = await self.driver.select(
            """
            SELECT
                id AS "id",
                name AS "name",
                price AS "price",
                DBMS_LOB.SUBSTR(description, 4000, 1) AS "description",
                category AS "category",
                sku AS "sku",
                NVL(in_stock, TRUE) AS "in_stock",
                metadata AS "metadata",
                embedding AS "embedding",
                created_at AS "created_at",
                updated_at AS "updated_at"
            FROM product
            ORDER BY name
            """,
            schema_type=Product,
        )
        return results

    async def get_by_id(self, product_id: int) -> Product | None:
        """Get product by ID."""
        result: Product | None = await self.driver.select_one_or_none(
            """
            SELECT
                id AS "id",
                name AS "name",
                price AS "price",
                DBMS_LOB.SUBSTR(description, 4000, 1) AS "description",
                category AS "category",
                sku AS "sku",
                NVL(in_stock, TRUE) AS "in_stock",
                metadata AS "metadata",
                embedding AS "embedding",
                created_at AS "created_at",
                updated_at AS "updated_at"
            FROM product
            WHERE id = :id
            """,
            id=product_id,
            schema_type=Product,
        )
        return result

    async def search_by_vector(
        self, query_embedding: list[float], limit: int = 10, similarity_threshold: float = 0.5
    ) -> list[dict[str, Any]]:
        """Search products by vector similarity using Oracle 23AI.

        SQLSpec automatically handles vector conversions - no need for array.array().

        Note: Returns dict instead of Product because includes similarity_score field.
        """
        # Oracle 23AI vector similarity search
        results: list[dict[str, Any]] = await self.driver.select(
            """
            SELECT
                id AS "id",
                name AS "name",
                price AS "price",
                DBMS_LOB.SUBSTR(description, 4000, 1) AS "description",
                category AS "category",
                sku AS "sku",
                NVL(in_stock, TRUE) AS "in_stock",
                metadata AS "metadata",
                embedding AS "embedding",
                created_at AS "created_at",
                updated_at AS "updated_at",
                VECTOR_DISTANCE(embedding, :query_embedding, COSINE) AS "similarity_score"
            FROM product
            WHERE embedding IS NOT NULL
            AND VECTOR_DISTANCE(embedding, :query_embedding, COSINE) <= :threshold
            ORDER BY "similarity_score"
            FETCH FIRST :limit ROWS ONLY
            """,
            query_embedding=query_embedding,
            threshold=1 - similarity_threshold,  # Convert similarity to distance
            limit=limit,
        )

        # Convert distance back to similarity score (handle Oracle uppercase column names)
        for result in results:
            score_key = "similarity_score" if "similarity_score" in result else "SIMILARITY_SCORE"
            result[score_key] = 1 - result[score_key]

        return results

    async def update_embedding(self, product_id: int, embedding: list[float]) -> bool:
        """Update product embedding.

        SQLSpec automatically handles vector conversions - no need for array.array().
        """
        result = await self.driver.execute(
            """
            UPDATE product
            SET embedding = :embedding,
                updated_at = SYSTIMESTAMP
            WHERE id = :id
            """,
            id=product_id,
            embedding=embedding,
        )

        return bool(result.rows_affected > 0)

    async def create_product(
        self,
        name: str,
        price: float,
        description: str,
        category: str | None = None,
        sku: str | None = None,
        in_stock: bool = True,
        metadata: dict | None = None,
        embedding: list[float] | None = None,
    ) -> Product | None:
        """Create a new product."""
        # Insert and get the generated ID
        result: dict[str, Any] | None = await self.driver.select_one_or_none(
            """
            INSERT INTO product (
                name, price, description, category, sku, in_stock, metadata, embedding
            ) VALUES (
                :name, :price, :description, :category, :sku, :in_stock, :metadata, :embedding
            )
            RETURNING id
            """,
            name=name,
            price=price,
            description=description,
            category=category,
            sku=sku,
            in_stock=in_stock,
            metadata=metadata,
            embedding=embedding,
        )

        if result:
            # Oracle returns column names in uppercase
            id_value = result.get("id") or result.get("ID")
            if id_value is None:
                return None
            product_id: int = int(id_value)
            # Return the created product
            return await self.get_by_id(product_id)

        return None
```

## Non-Database Service Example

**File**: `/home/cody/code/g/oracledb-vertexai-demo/app/services/_vertex_ai.py`

```python
from app.lib.settings import get_settings
from app.services._cache import CacheService

class VertexAIService:
    """Vertex AI service for embeddings and chat completions.

    Note: Does NOT inherit from SQLSpecService since it doesn't do direct DB operations.
    """

    def __init__(self, cache_service: CacheService | None = None) -> None:
        """Initialize Vertex AI service.

        Args:
            cache_service: Optional cache service for embedding caching
        """
        from google import genai

        self.settings = get_settings()
        self._genai_client: genai.Client | None = None
        self._cache_service: CacheService | None = cache_service

        # Initialize Vertex AI
        if self.settings.vertex_ai.PROJECT_ID:
            self._genai_client = genai.Client()
        else:
            api_key = self.settings.vertex_ai.API_KEY
            if api_key:
                self._genai_client = genai.Client(api_key=api_key)

    async def get_text_embedding(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:
        """Generate text embedding using Vertex AI with caching."""
        if not self._genai_client:
            msg = "Vertex AI not initialized"
            raise RuntimeError(msg)

        model_name = model or self.settings.vertex_ai.EMBEDDING_MODEL

        # Check cache first if available
        if self._cache_service and self.settings.cache.EMBEDDING_CACHE_ENABLED:
            cached = await self._cache_service.get_cached_embedding(text, model_name)
            if cached:
                return cached.embedding

        # Generate new embedding
        embedding = await self._get_embedding_async(text, model_name)

        # Cache the result if cache service is available
        if self._cache_service and self.settings.cache.EMBEDDING_CACHE_ENABLED:
            try:
                await self._cache_service.set_cached_embedding(text, embedding, model_name)
            except Exception as e:
                logger.warning("Failed to cache embedding", error=str(e))

        return embedding
```

## When to Use

### Use SQLSpecService Base Class When:

1. **Database Operations**: Service needs to query or update Oracle database
2. **Transactions**: Service performs multi-step database operations
3. **Filtering/Pagination**: Service needs SQLSpec's built-in filtering
4. **Type Safety**: Service benefits from schema-typed results

### Use Standalone Service When:

1. **External API**: Service calls external APIs (Vertex AI, etc.)
2. **Pure Logic**: Service only processes data without database access
3. **Orchestration**: Service coordinates other services

## Key Patterns

### 1. Oracle-Specific SQL Patterns

```python
# Use :name parameter binding (Oracle-specific)
await self.driver.select(
    "SELECT * FROM product WHERE id = :id",
    id=product_id,
    schema_type=Product,
)

# Handle Oracle uppercase column names
result = await self.driver.select_one_or_none(...)
id_value = result.get("id") or result.get("ID")

# Use Oracle functions
DBMS_LOB.SUBSTR(description, 4000, 1) AS "description"
NVL(in_stock, TRUE) AS "in_stock"
SYSTIMESTAMP  # Current timestamp
```

### 2. Vector Operations

```python
# SQLSpec automatically converts list[float] to Oracle VECTOR type
embedding = [0.1] * 768
await self.driver.execute(
    "UPDATE product SET embedding = :embedding WHERE id = :id",
    embedding=embedding,  # No array.array() needed!
    id=product_id,
)

# Vector similarity search
VECTOR_DISTANCE(embedding, :query_embedding, COSINE) AS "similarity_score"
```

### 3. Transaction Management

```python
# Option 1: Context manager (recommended)
async with service.begin_transaction():
    await service.create_product(...)
    await service.update_embedding(...)
    # Auto-commits on success, auto-rollbacks on error

# Option 2: Manual control
await service.begin()
try:
    await service.create_product(...)
    await service.commit()
except Exception:
    await service.rollback()
    raise
```

### 4. Service Composition

```python
class OracleVectorSearchService:
    """Composite service that uses other services."""

    def __init__(
        self,
        products_service: ProductService,
        vertex_ai_service: VertexAIService,
        embedding_cache: CacheService | None = None,
    ) -> None:
        self.products_service = products_service
        self.vertex_ai_service = vertex_ai_service
        self.embedding_cache = embedding_cache

    async def similarity_search(self, query: str, k: int = 4):
        # Generate embedding
        query_embedding = await self.vertex_ai_service.get_text_embedding(query)

        # Search using product service
        return await self.products_service.search_by_vector(query_embedding, limit=k)
```

## Dependency Injection

Services are provided via Dishka DI container:

**File**: `/home/cody/code/g/oracledb-vertexai-demo/app/server/providers.py`

```python
from dishka import Provider, Scope, provide
from sqlspec.driver import AsyncDriverAdapterBase

class CoreServiceProvider(Provider):
    scope = Scope.REQUEST  # Default scope

    @provide
    def get_product_service(self, driver: AsyncDriverAdapterBase) -> ProductService:
        """Provide ProductService."""
        return ProductService(driver)

    @provide
    def get_cache_service(self, driver: AsyncDriverAdapterBase) -> CacheService:
        """Provide CacheService."""
        return CacheService(driver)

    @provide
    def get_vertex_ai_service(self, cache_service: CacheService) -> VertexAIService:
        """Provide VertexAI service with cache support."""
        return VertexAIService(cache_service=cache_service)

    @provide
    def get_vector_search_service(
        self,
        product_service: ProductService,
        vertex_ai_service: VertexAIService,
        cache_service: CacheService,
    ) -> OracleVectorSearchService:
        """Provide OracleVectorSearchService with auto-wired dependencies."""
        return OracleVectorSearchService(
            products_service=product_service,
            vertex_ai_service=vertex_ai_service,
            embedding_cache=cache_service,
        )
```

## Best Practices

1. **Inherit from SQLSpecService** for all database-backed services
2. **Use schema_type parameter** for type-safe results
3. **Handle Oracle case sensitivity** - use `AS "column_name"` in SQL
4. **Let SQLSpec handle vectors** - pass `list[float]` directly
5. **Use transactions** for multi-step operations
6. **Compose services** rather than duplicating logic
7. **Cache expensive operations** (embeddings, API calls)
8. **Return None** for not-found cases, raise errors for actual failures

## Common Gotchas

1. **Oracle uppercase**: Column names without quotes become uppercase
   ```python
   # BAD: May return None unexpectedly
   result.get("id")

   # GOOD: Handle both cases
   result.get("id") or result.get("ID")

   # BEST: Use quoted identifiers in SQL
   SELECT id AS "id" FROM product
   ```

2. **CLOB columns**: Must use `DBMS_LOB.SUBSTR()` for text retrieval
   ```python
   # GOOD
   DBMS_LOB.SUBSTR(description, 4000, 1) AS "description"
   ```

3. **Vector conversion**: SQLSpec handles it automatically
   ```python
   # NO LONGER NEEDED (old way)
   import array
   embedding=array.array('f', query_embedding)

   # CORRECT (SQLSpec handles it)
   embedding=query_embedding  # Just pass the list!
   ```

4. **Transaction scope**: Remember to commit or use context manager
   ```python
   # BAD: Changes not persisted
   await service.driver.execute("INSERT ...")

   # GOOD: Explicit commit
   await service.driver.execute("INSERT ...")
   await service.driver.commit()

   # BEST: Context manager
   async with service.begin_transaction():
       await service.driver.execute("INSERT ...")
   ```
