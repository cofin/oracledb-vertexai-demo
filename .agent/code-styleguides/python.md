# Python Style Guide

Modern Python development standards with async-first patterns.

## Core Rules

### Type Annotations

```python
# Use PEP 604 union syntax
def get_user(id: int) -> User | None:
    ...

# Never use Optional or TYPE_CHECKING imports
# Bad: from typing import Optional
# Bad: from __future__ import annotations

# Use generic syntax for collections
items: list[str] = []
mapping: dict[str, int] = {}
```

### Async by Default

```python
# All I/O operations should be async
async def fetch_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

# Use AsyncIterable for generators with cleanup
async def provide_session() -> AsyncIterable[AsyncSession]:
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()
```

### Docstrings

```python
def calculate_total(items: list[Item], tax_rate: float) -> Decimal:
    """Calculate the total price including tax.

    Args:
        items: List of items to calculate.
        tax_rate: Tax rate as a decimal (e.g., 0.08 for 8%).

    Returns:
        Total price with tax applied.

    Raises:
        ValueError: If tax_rate is negative.
    """
```

## Naming Conventions

| Concept     | Convention             | Example                 |
| :---------- | :--------------------- | :---------------------- |
| Modules     | `snake_case`           | `user_service.py`       |
| Classes     | `PascalCase`           | `UserService`           |
| Functions   | `snake_case`           | `get_user_by_id`        |
| Variables   | `snake_case`           | `current_user`          |
| Constants   | `SCREAMING_SNAKE_CASE` | `MAX_RETRIES`           |
| Private     | `_leading_underscore`  | `_internal_cache`       |

## Data Classes and Models

```python
from dataclasses import dataclass
from uuid import UUID

@dataclass
class UserCreate:
    """Data for creating a new user."""
    email: str
    name: str | None = None

@dataclass
class User:
    """User entity."""
    id: UUID
    email: str
    name: str | None
    is_active: bool = True
```

## Exception Handling

```python
# Create specific exceptions
class UserNotFoundError(Exception):
    """Raised when a user cannot be found."""
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")

# Catch specific exceptions, never bare except
try:
    user = await get_user(user_id)
except UserNotFoundError:
    raise HTTPException(status_code=404)
```

## Dependency Injection Pattern

```python
from dishka import Provider, Scope, provide

class ServiceProvider(Provider):
    """Provider for domain services."""

    @provide(scope=Scope.REQUEST)
    def provide_user_service(
        self,
        driver: AsyncDriverAdapterBase,
    ) -> UserService:
        return UserService(driver)
```

## Service Pattern

```python
class UserService:
    """Service for user operations."""

    def __init__(self, driver: AsyncDriverAdapterBase) -> None:
        self.driver = driver

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        return await self.driver.get_one_or_none(
            User,
            id=user_id,
        )

    async def create(self, data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            id=uuid4(),
            email=data.email,
            name=data.name,
        )
        return await self.driver.add(user)
```

## Import Organization

```python
# Standard library
from collections.abc import AsyncIterable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

# Third-party
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.domain.users.models import User
from app.domain.users.service import UserService
```

## Testing

```python
import pytest

# Function-based tests (not class-based)
def test_user_creation():
    user = User(id=uuid4(), email="test@example.com", name=None)
    assert user.is_active is True

# Parametrized tests
@pytest.mark.parametrize("email,valid", [
    ("test@example.com", True),
    ("invalid", False),
    ("", False),
])
def test_email_validation(email: str, valid: bool):
    assert validate_email(email) == valid

# Async tests
@pytest.mark.anyio
async def test_fetch_user(client: AsyncClient):
    response = await client.get("/api/users/1")
    assert response.status_code == 200
```

## Tooling

- **Quality & Typing**: See `python-quality` skill (Ruff, Pyright).
- **Emerging**: See `ty` skill (if installed).
- **Test runner**: `pytest`

## Build System

- **Backend**: `hatchling` (see `python-build` skill)
- **Manager**: `uv` (see `python-uv` skill)

## Performance Optimizations

For performance-critical paths:

- **MyPyC**: Compile native classes (see `python-mypyc` skill).
- **Cython**: Use typed memoryviews (see `python-cython` skill).

## Anti-Patterns to Avoid

```python
# Bad: Using Optional
from typing import Optional
def bad(x: Optional[str]) -> Optional[int]: ...

# Good: Use union syntax
def good(x: str | None) -> int | None: ...

# Bad: Mutable default arguments
def bad(items: list = []): ...

# Good: Use None and create inside
def good(items: list | None = None):
    items = items or []

# Bad: Bare except
try:
    something()
except:
    pass

# Good: Specific exception
try:
    something()
except ValueError as e:
    logger.error("Validation failed", exc_info=e)
    raise
```

## Scripting Best Practices

For Python scripts (CLI tools, automation, etc.), apply these additional patterns.

### Environment Management

```bash
# Use uv for project management
uv sync
uv run python your_script.py

# Single-file scripts with dependencies (PEP 723)
# /// script
# dependencies = ["requests", "rich"]
# ///
uv run script.py
```

### Script Structure

```python
#!/usr/bin/env python3
"""Brief description of what the script does.

Usage:
    python script.py [options] <arguments>
"""
import argparse
import sys

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Input file path")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    try:
        # Main logic here
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### Code Formatting

```bash
# Use ruff for formatting and linting
ruff format .
ruff check . --fix
```

### Testing with pytest

```python
# tests/test_example.py
import pytest

def test_function_success():
    """Test the happy path."""
    result = my_function(valid_input)
    assert result == expected_output

def test_function_error():
    """Test error handling."""
    with pytest.raises(ValueError, match="Invalid input"):
        my_function(invalid_input)

@pytest.fixture
def sample_data():
    """Fixture providing test data."""
    return {"key": "value"}
```

### Script Anti-Patterns

```python
# Bad: Global mutable state
config = {}  # Modified by multiple functions

# Good: Pass configuration explicitly
def process(data: dict, config: Config) -> Result:
    ...

# Bad: Hardcoded configuration
DATABASE_URL = "postgres://localhost/db"

# Good: Environment variables or config files
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://localhost/db")

# Bad: Swallowing errors silently
try:
    risky_operation()
except Exception:
    pass  # Silent failure

# Good: Log and handle appropriately
try:
    risky_operation()
except SpecificError as e:
    logger.error("Operation failed: %s", e)
    raise
```
