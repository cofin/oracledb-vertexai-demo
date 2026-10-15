# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Integration test configuration, Oracle container lifecycle, and seed fixtures."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import socket
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from litestar.testing import AsyncTestClient
from tools.oracle.container import ContainerRuntime
from tools.oracle.database import DatabaseConfig, OracleDatabase

from app import config as app_config
from app.db.utils import COFFEE_SHOP_TABLES, _reset_sequences
from app.domain.products.services import ProductService
from app.domain.system.services import CacheService
from app.lib import settings as app_settings
from app.server.asgi import create_app
from app.utils.fixtures import FixtureLoader

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator

    from litestar import Litestar
    from sqlspec.adapters.oracledb import OracleAsyncDriver


_ORACLE_SCHEMA_READY = False
_ORACLE_SEED_DATA_READY = False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Pin every integration test to a single xdist worker to avoid pool and TRUNCATE races."""
    del config
    marker = pytest.mark.xdist_group(name="oracle_integration")
    for item in items:
        item.add_marker(marker)


def find_free_port() -> int:
    """Return an OS-assigned free TCP port on the loopback interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def oracle_test_container() -> Generator[dict[str, str | int], None, None]:
    """Start an ephemeral gvenzl/oracle-free container on a free port for the test session."""
    password = "SuperSecret1"
    reuse_port = os.getenv("ORACLE_TEST_REUSE_PORT")
    if reuse_port:
        yield {
            "host": "localhost",
            "port": int(reuse_port),
            "service_name": "freepdb1",
            "user": "app",
            "password": password,
        }
        return

    suffix = uuid.uuid4().hex[:8]
    port = find_free_port()
    config = DatabaseConfig(
        container_name=f"oracle-test-{suffix}",
        host_port=port,
        app_user="app",
        app_user_password=password,
        data_volume_name=f"oracle-test-data-{suffix}",
    )
    database = OracleDatabase(runtime=ContainerRuntime(), config=config)
    database.start(pull=bool(os.getenv("ORACLE_TEST_PULL")))
    try:
        yield {"host": "localhost", "port": port, "service_name": "freepdb1", "user": "app", "password": password}
    finally:
        with contextlib.suppress(Exception):
            database.remove(volumes=True, force=True)


@pytest.fixture
def test_settings(
    oracle_test_container: dict[str, str | int],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[object, None, None]:
    """Point the app at the ephemeral gvenzl container in local (non-wallet) mode."""
    test_dir = tmp_path_factory.mktemp("integration_env")
    bundle_dir = test_dir / "static"
    asset_dir = bundle_dir / "assets"
    asset_dir.mkdir(parents=True)
    (asset_dir / "styles.css").write_text("/* integration test asset */\n", encoding="utf-8")
    (asset_dir / "main.js").write_text("// integration test asset\n", encoding="utf-8")
    (bundle_dir / "manifest.json").write_text(
        json.dumps({
            "styles.css": {"file": "assets/styles.css", "src": "styles.css", "isEntry": True},
            "main.js": {"file": "assets/main.js", "src": "main.js", "isEntry": True},
        }),
        encoding="utf-8",
    )
    test_env = test_dir / ".env.testing"
    test_env.write_text(
        f"DATABASE_USER={oracle_test_container['user']}\n"
        f"DATABASE_PASSWORD={oracle_test_container['password']}\n"
        f"DATABASE_HOST={oracle_test_container['host']}\n"
        f"DATABASE_PORT={oracle_test_container['port']}\n"
        f"DATABASE_SERVICE_NAME={oracle_test_container['service_name']}\n"
        "GOOGLE_CLOUD_PROJECT=test-project\n"
        "GOOGLE_API_KEY=test-api-key\n"
        "LITESTAR_DEBUG=true\n"
        "LITESTAR_HOST=127.0.0.1\n"
        "LITESTAR_PORT=5007\n"
        "SECRET_KEY=test-secret-key-32-characters-12\n"
        "VITE_DEV_MODE=False\n"
        f"VITE_BUNDLE_DIR={bundle_dir}\n",
        encoding="utf-8",
    )

    for key in (
        "DATABASE_URL",
        "DATABASE_DSN",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_SERVICE_NAME",
        "WALLET_LOCATION",
        "WALLET_PASSWORD",
        "TNS_ADMIN",
        "VITE_BUNDLE_DIR",
        "VITE_DEV_MODE",
    ):
        monkeypatch.delenv(key, raising=False)
    app_settings.Settings.from_env.cache_clear()
    settings = app_settings.Settings.from_env(str(test_env))

    def get_settings(dotenv_filename: str = ".env.testing") -> object:
        del dotenv_filename
        return settings

    monkeypatch.setattr(app_settings, "get_settings", get_settings)
    app_settings.Settings.from_env.cache_clear()
    app_config._reset()
    try:
        yield settings
    finally:
        app_settings.Settings.from_env.cache_clear()
        app_config._reset()


async def _bootstrap_test_schema(session: OracleAsyncDriver) -> None:
    """Ensure integration-test tables and seed data exist."""
    await session.execute(
        """
        BEGIN
            EXECUTE IMMEDIATE '
                CREATE TABLE product (
                    id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY PRIMARY KEY,
                    name VARCHAR2(255) NOT NULL,
                    description VARCHAR2(4000),
                    price NUMBER(10, 2),
                    category VARCHAR2(100),
                    sku VARCHAR2(100) UNIQUE,
                    in_stock BOOLEAN DEFAULT TRUE,
                    metadata JSON,
                    embedding VECTOR(3072, FLOAT32),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT ON NULL FOR INSERT AND UPDATE CURRENT_TIMESTAMP NOT NULL
                )
            ';
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE != -955 THEN
                    RAISE;
                END IF;
        END;
        """
    )
    await session.execute(
        """
        BEGIN
            EXECUTE IMMEDIATE '
                CREATE TABLE response_cache (
                    id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY PRIMARY KEY,
                    cache_key VARCHAR2(255) UNIQUE NOT NULL,
                    response_data JSON NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ';
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE != -955 THEN
                    RAISE;
                END IF;
        END;
        """
    )
    await session.execute(
        """
        BEGIN
            EXECUTE IMMEDIATE '
                CREATE TABLE embedding_cache (
                    id NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY PRIMARY KEY,
                    text_hash VARCHAR2(255) NOT NULL,
                    embedding VECTOR(3072, FLOAT32) NOT NULL,
                    model VARCHAR2(100) NOT NULL,
                    hit_count NUMBER DEFAULT 0,
                    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT embedding_cache_uk UNIQUE (text_hash, model)
                )
            ';
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE != -955 THEN
                    RAISE;
                END IF;
        END;
        """
    )
    await session.commit()


async def _seed_marker_product(session: OracleAsyncDriver) -> None:
    """Insert the deterministic marker product used by integration tests."""
    await session.execute(
        """
        MERGE INTO product p
        USING (SELECT :sku AS sku FROM dual) src
        ON (p.sku = src.sku)
        WHEN NOT MATCHED THEN
            INSERT (name, description, price, category, sku, in_stock)
            VALUES (:name, :description, :price, :category, :sku, TRUE)
        """,
        sku="SEED-SKU-001",
        name="Seed Coffee Product",
        description="Baseline product seeded for integration tests",
        price=9.99,
        category="Coffee",
    )
    await session.commit()


async def _assert_sqlspec_extension_tables(session: OracleAsyncDriver) -> None:
    """Fail fast when SQLSpec migrations did not materialize extension tables."""
    expected = {"APP_SESSION"}
    rows = await session.select(
        """
        SELECT table_name
          FROM user_tables
         WHERE table_name IN ('APP_SESSION')
        """
    )
    present = {str(row["table_name"]).upper() for row in rows}
    missing = sorted(expected - present)
    if missing:
        msg = (
            "SQLSpec migrations did not create required integration-test tables: "
            f"{', '.join(missing)}. Reset the local Oracle schema/container and rerun the tests."
        )
        raise RuntimeError(msg)


async def _ensure_oracle_schema() -> None:
    """Create idempotent Oracle test schema objects once per pytest worker."""
    global _ORACLE_SCHEMA_READY

    if _ORACLE_SCHEMA_READY:
        return

    await app_config.db.migrate_up(echo=False)
    with contextlib.suppress(Exception):
        await app_config.db.close_pool()

    try:
        async with app_config.db_manager.provide_session(app_config.db) as session:
            await _assert_sqlspec_extension_tables(session)
            await _bootstrap_test_schema(session)
    finally:
        with contextlib.suppress(Exception):
            await app_config.db.close_pool()
    _ORACLE_SCHEMA_READY = True


async def _ensure_oracle_seed_data(session: OracleAsyncDriver) -> None:
    """Load deterministic fixture data once per pytest worker."""
    global _ORACLE_SEED_DATA_READY

    if _ORACLE_SEED_DATA_READY:
        return
    await _truncate_fixture_tables(session)
    await _load_app_fixtures(session)
    await _seed_marker_product(session)
    _ORACLE_SEED_DATA_READY = True


@pytest.fixture
async def oracle_schema(test_settings: object) -> None:
    """Ensure SQLSpec migrations have prepared the shared Oracle schema."""
    del test_settings
    await _ensure_oracle_schema()


@pytest.fixture
async def client(app: Litestar, oracle_seed_data: None) -> AsyncGenerator[AsyncTestClient, None]:
    """Create test client."""
    del oracle_seed_data
    async with AsyncTestClient(app=app) as c:
        yield c


@pytest.fixture
async def htmx_client(app: Litestar, oracle_seed_data: None) -> AsyncGenerator[AsyncTestClient, None]:
    """Create an HTMX-flavored test client after schema migration."""
    del oracle_seed_data
    async with AsyncTestClient(app=app) as c:
        c.headers["HX-Request"] = "true"
        yield c


@pytest.fixture
def app(test_settings: object) -> Litestar:
    """Create test app instance."""
    del test_settings
    return create_app()


async def _truncate_fixture_tables(session: OracleAsyncDriver) -> None:
    """Wipe fixture-managed tables so each test session starts from a known state."""
    for table in ("store_product_inventory", "product", "store"):
        with contextlib.suppress(Exception):
            await session.execute(f"TRUNCATE TABLE {table}")
    await session.commit()


async def _load_app_fixtures(session: OracleAsyncDriver) -> None:
    """Load the checked-in `.json.gz` fixtures into the test database via `FixtureLoader`."""
    settings = app_settings.get_settings()
    fixtures_dir = Path(settings.db.FIXTURE_PATH)
    if not await asyncio.to_thread(fixtures_dir.exists):
        return
    loader = FixtureLoader(fixtures_dir=fixtures_dir, driver=session, table_order=COFFEE_SHOP_TABLES)
    await loader.load_all_fixtures()
    await _reset_sequences(session)


@pytest.fixture
def unique_test_id() -> str:
    """Return a stable unique suffix for one integration test."""
    return uuid.uuid4().hex


@pytest.fixture
async def oracle_seed_data(test_settings: object) -> None:
    """Ensure shared Oracle schema and fixture data are ready for this worker."""
    del test_settings
    try:
        await _ensure_oracle_schema()
        async with app_config.db_manager.provide_session(app_config.db) as session:
            await _ensure_oracle_seed_data(session)
    finally:
        with contextlib.suppress(Exception):
            await app_config.db.close_pool()


@pytest.fixture
async def driver(oracle_seed_data: None) -> AsyncGenerator[OracleAsyncDriver, None]:
    """Provide an isolated SQLSpec driver session against shared seeded data."""
    del oracle_seed_data
    with contextlib.suppress(Exception):
        await app_config.db.close_pool()

    try:
        async with app_config.db_manager.provide_session(app_config.db) as session:
            yield session
    finally:
        with contextlib.suppress(Exception):
            await app_config.db.close_pool()


@pytest.fixture
async def tracked_product_skus(driver: OracleAsyncDriver) -> AsyncGenerator[Callable[[str], None], None]:
    """Track product SKUs inserted by a test and delete them afterwards."""
    skus: list[str] = []

    def track(sku: str) -> None:
        skus.append(sku)

    try:
        yield track
    finally:
        for sku in skus:
            with contextlib.suppress(Exception):
                await driver.execute("DELETE FROM product WHERE sku = :sku", sku=sku)
        if skus:
            with contextlib.suppress(Exception):
                await driver.commit()


@pytest.fixture
async def product_service(driver: OracleAsyncDriver) -> ProductService:
    """Provide ProductService for testing."""
    return ProductService(driver)


@pytest.fixture
async def cache_service(driver: OracleAsyncDriver) -> CacheService:
    """Provide CacheService for testing."""
    return CacheService(driver)
