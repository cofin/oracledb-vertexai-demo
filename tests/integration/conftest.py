from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from litestar.testing import AsyncTestClient

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    import oracledb
    from litestar import Litestar


@pytest.fixture(scope="session")
async def oracle_connection(oracle_service: Any) -> AsyncGenerator[oracledb.AsyncConnection, None]:
    """Create direct Oracle connection for tests."""
    import oracledb

    # Create connection using connect string
    dsn = f"{oracle_service.host}:{oracle_service.port}/{oracle_service.service_name}"
    conn = await oracledb.connect_async(
        user=oracle_service.user,
        password=oracle_service.password,
        dsn=dsn,
    )

    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture(autouse=True)
async def _setup_test_db(oracle_connection: oracledb.AsyncConnection) -> AsyncGenerator[None, None]:
    """Setup test database with schema and sample data."""
    cursor = oracle_connection.cursor()

    try:
        yield

    finally:
        cursor.close()


@pytest.fixture
async def client(app: Litestar) -> AsyncGenerator[AsyncTestClient, None]:
    """Create test client."""
    async with AsyncTestClient(app=app) as c:
        yield c


@pytest.fixture
def app() -> Litestar:
    """Create test app instance."""
    from app.asgi import create_app

    return create_app()
