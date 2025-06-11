from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from advanced_alchemy.base import BigIntAuditBase, UUIDAuditBase
from litestar.testing import AsyncTestClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Company, Inventory, Product, Shop

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar import Litestar
    from pytest import MonkeyPatch


@pytest.fixture(scope="session")
async def engine(oracle_service: Any) -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine with Oracle database."""
    engine = create_async_engine(
        oracle_service.get_connection_string(),
        echo=False,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async sessionmaker."""
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _seed_db(  # noqa: PLR0915
    engine: AsyncEngine,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[None, None]:
    """Seed database with test data."""

    # Drop and recreate all tables
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(UUIDAuditBase.metadata.drop_all)
        await conn.run_sync(BigIntAuditBase.metadata.drop_all)
        # Create all tables
        await conn.run_sync(BigIntAuditBase.metadata.create_all)
        await conn.run_sync(UUIDAuditBase.metadata.create_all)

    # Seed with fixture data
    async with sessionmaker() as session:
        # Load fixture data
        fixtures_dir = Path(__file__).parent.parent.parent / "app" / "db" / "fixtures"

        # Create companies
        companies_data = []
        if (fixtures_dir / "company.json").exists():
            import json

            import anyio

            content = await anyio.Path(fixtures_dir / "company.json").read_text()
            companies_data = json.loads(content)

        companies = []
        for company_data in companies_data:
            company = Company(**company_data)
            session.add(company)
            companies.append(company)

        await session.flush()

        # Create shops
        shops_data = []
        if (fixtures_dir / "shop.json").exists():
            import json

            import anyio

            content = await anyio.Path(fixtures_dir / "shop.json").read_text()
            shops_data = json.loads(content)

        shops = []
        for shop_data in shops_data:
            shop = Shop(**shop_data)
            session.add(shop)
            shops.append(shop)

        await session.flush()

        # Create products
        products_data = []
        if (fixtures_dir / "product.json").exists():
            import json

            import anyio

            content = await anyio.Path(fixtures_dir / "product.json").read_text()
            products_data = json.loads(content)

        products = []
        for product_data in products_data:
            # Find company by name
            if companies:
                product_data["company_id"] = companies[0].id
            product = Product(**product_data)
            session.add(product)
            products.append(product)

        await session.flush()

        # Create inventory
        inventory_data = []
        if (fixtures_dir / "inventory.json").exists():
            import json

            import anyio

            content = await anyio.Path(fixtures_dir / "inventory.json").read_text()
            inventory_data = json.loads(content)

        for inv_data in inventory_data:
            if shops and products:
                inv_data["shop_id"] = shops[0].id
                inv_data["product_id"] = products[0].id
                inventory = Inventory(**inv_data)
                session.add(inventory)

        await session.commit()

    yield

    # Cleanup after tests
    async with engine.begin() as conn:
        await conn.run_sync(UUIDAuditBase.metadata.drop_all)
        await conn.run_sync(BigIntAuditBase.metadata.drop_all)


@pytest.fixture(autouse=True)
async def _patch_db(
    sessionmaker: async_sessionmaker[AsyncSession],
    engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    """Patch database configuration for tests."""
    # Mock database functions in the app
    monkeypatch.setattr("app.db.utils.create_session", lambda: sessionmaker())
    monkeypatch.setattr("app.db.utils.get_engine", lambda: engine)


@pytest.fixture
async def client(app: Litestar) -> AsyncGenerator[AsyncTestClient, None]:
    """Create test client."""
    async with AsyncTestClient(app=app) as c:
        yield c


@pytest.fixture
async def session(sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async with sessionmaker() as session:
        yield session


@pytest.fixture
def app() -> Litestar:
    """Create test app instance."""
    from app.asgi import create_app

    return create_app()
