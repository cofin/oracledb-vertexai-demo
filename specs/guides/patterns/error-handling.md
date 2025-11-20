# Error Handling Pattern

## Overview

This project uses a **custom exception hierarchy** with structured logging for error handling. The base `ApplicationError` class provides consistent error detail formatting across the application.

## Structure

**File**: `/home/cody/code/g/oracledb-vertexai-demo/app/lib/exceptions.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import Any

class ApplicationError(Exception):
    """Base exception type for the lib's custom exception types."""

    detail: str

    def __init__(self, *args: Any, detail: str = "") -> None:
        """Initialize ApplicationError.

        Args:
            *args: args are converted to str before passing to Exception
            detail: detail of the exception.
        """
        str_args = [str(arg) for arg in args if arg]
        if not detail:
            if str_args:
                detail, *str_args = str_args
            elif hasattr(self, "detail"):
                detail = self.detail
        self.detail = detail
        super().__init__(*str_args)

    def __repr__(self) -> str:
        if self.detail:
            return f"{self.__class__.__name__} - {self.detail}"
        return self.__class__.__name__

    def __str__(self) -> str:
        return " ".join((*self.args, self.detail)).strip()
```

## Usage Patterns

### Raising Custom Errors

```python
from app.lib.exceptions import ApplicationError

class ProductService:
    async def get_by_id(self, product_id: int) -> Product:
        """Get product by ID."""
        result = await self.driver.select_one_or_none(...)

        if result is None:
            raise ApplicationError(
                detail=f"Product {product_id} not found"
            )

        return result
```

### Service Layer Error Handling

```python
import structlog

logger = structlog.get_logger()

class VertexAIService:
    async def get_text_embedding(self, text: str) -> list[float]:
        """Generate embedding with error handling."""
        try:
            embedding = await self._get_embedding_async(text, model_name)
            return embedding

        except Exception as e:
            logger.exception(
                "Failed to generate embedding",
                text=text[:50],
                model=model_name,
                error=str(e),
            )
            msg = f"Failed to generate embedding: {e}"
            raise ValueError(msg) from e
```

### Controller Error Handling

```python
from litestar import get
from litestar.exceptions import NotFoundException
from app.lib.exceptions import ApplicationError

@get("/products/{product_id:int}")
async def get_product(
    product_id: int,
    service: Inject[ProductService],
) -> Product:
    """Get product with error handling."""
    try:
        product = await service.get_by_id(product_id)
        if product is None:
            raise NotFoundException(detail=f"Product {product_id} not found")
        return product

    except ApplicationError as e:
        # Application errors converted to HTTP responses
        raise NotFoundException(detail=e.detail) from e

    except Exception as e:
        # Unexpected errors logged and converted
        logger.exception("Unexpected error fetching product", product_id=product_id)
        raise InternalServerException(detail="Internal server error") from e
```

## Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Good: Structured context
logger.info(
    "Vector search completed",
    query=query[:50],
    result_count=len(results),
    cache_hit=cache_hit,
    timing_ms=timing_data["total_ms"],
)

# Good: Exception with context
logger.exception(
    "Database query failed",
    table="product",
    query_id=query_id,
    error=str(e),
)

# Bad: Unstructured string
logger.info(f"Vector search for '{query}' found {len(results)} results")
```

## Best Practices

1. **Use ApplicationError** for application-specific errors
2. **Log exceptions** with structured context before re-raising
3. **Convert to HTTP exceptions** at controller boundary
4. **Include error details** for debugging
5. **Don't expose internals** in error messages to users
6. **Use exception chaining** with `raise ... from e`

## Common Patterns

### Validation Errors

```python
class ProductService:
    async def create_product(self, data: dict) -> Product:
        """Create product with validation."""
        if not data.get("name"):
            raise ValueError("Product name is required")

        if data.get("price", 0) <= 0:
            raise ValueError("Product price must be positive")

        return await self.driver.execute(...)
```

### Database Errors

```python
async def update_embedding(self, product_id: int, embedding: list[float]) -> bool:
    """Update embedding with error handling."""
    try:
        result = await self.driver.execute(
            "UPDATE product SET embedding = :emb WHERE id = :id",
            emb=embedding,
            id=product_id,
        )
        return bool(result.rows_affected > 0)

    except Exception as e:
        logger.exception(
            "Failed to update embedding",
            product_id=product_id,
            error=str(e),
        )
        raise ApplicationError(
            detail=f"Failed to update product {product_id} embedding"
        ) from e
```

### External API Errors

```python
class VertexAIService:
    async def get_text_embedding(self, text: str) -> list[float]:
        """Generate embedding with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await self._get_embedding_async(text, model)

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(
                        "Vertex AI embedding failed after retries",
                        attempts=max_retries,
                        error=str(e),
                    )
                    raise

                logger.warning(
                    "Vertex AI embedding retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## Common Gotchas

1. **Don't swallow exceptions**
   ```python
   # BAD
   try:
       result = await api_call()
   except Exception:
       return None  # Silent failure!

   # GOOD
   try:
       result = await api_call()
   except Exception as e:
       logger.exception("API call failed")
       raise ApplicationError("API unavailable") from e
   ```

2. **Log before raising**
   ```python
   # GOOD
   except Exception as e:
       logger.exception("Operation failed", context=data)
       raise ApplicationError("Failed") from e
   ```

3. **Use exception chaining**
   ```python
   # GOOD: Preserves stack trace
   except ValueError as e:
       raise ApplicationError("Invalid data") from e

   # BAD: Loses original exception
   except ValueError:
       raise ApplicationError("Invalid data")
   ```
