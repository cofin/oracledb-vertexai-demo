# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Root pytest configuration, fixtures, and mock Oracle driver."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from litestar.testing import AsyncTestClient
from sqlspec.driver._async import AsyncDriverAdapterBase

os.environ.setdefault("QUEUE_BACKEND", "memory")

from app import config as app_config
from app.lib import settings as app_settings
from app.server.asgi import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from litestar import Litestar
    from pytest import MonkeyPatch

pytest_plugins = ["tests.fixtures.slides"]

pytestmark = pytest.mark.anyio


def pytest_configure(config: pytest.Config) -> None:
    """Configure test defaults so unit tests use the in-memory queue backend."""
    del config
    os.environ.setdefault("QUEUE_BACKEND", "memory")


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Return the AnyIO backend name for async test execution."""
    return "asyncio"


@pytest.fixture
def test_settings(
    monkeypatch: MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[app_settings.Settings]:
    """Patch settings with a temporary test `.env.testing` configuration."""
    test_dir = tmp_path_factory.mktemp("test_env")
    test_env = test_dir / ".env.testing"
    env_defaults = {
        "DATABASE_USER": "test_app",
        "DATABASE_PASSWORD": "test-secret",
        "DATABASE_HOST": "localhost",
        "DATABASE_PORT": "1521",
        "DATABASE_SERVICE_NAME": "freepdb1",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_API_KEY": "test-api-key",
        "LITESTAR_DEBUG": "true",
        "LITESTAR_HOST": "127.0.0.1",
        "LITESTAR_PORT": "5007",
        "SECRET_KEY": "test-secret-key-32-characters-12",
        "QUEUE_BACKEND": "memory",
        "VITE_DEV_MODE": "False",
    }
    for unset_key in ("DATABASE_URL", "DATABASE_DSN", "WALLET_LOCATION", "WALLET_PASSWORD", "TNS_ADMIN"):
        monkeypatch.delenv(unset_key, raising=False)
    for key, value in env_defaults.items():
        monkeypatch.setenv(key, value)
    test_env.write_text("\n".join(f"{k}={v}" for k, v in env_defaults.items()) + "\n", encoding="utf-8")

    app_settings.Settings.from_env.cache_clear()
    settings = app_settings.Settings.from_env(str(test_env))

    def get_settings(dotenv_filename: str = ".env.testing") -> app_settings.Settings:
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


@pytest.fixture
def app(test_settings: app_settings.Settings) -> Litestar:
    """Create a Litestar test application instance."""
    del test_settings
    return create_app()


@pytest.fixture
async def client(app: Litestar) -> AsyncIterator[AsyncTestClient]:
    """Yield an AsyncTestClient with the Litestar lifespan entered."""
    async with AsyncTestClient(app=app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
async def htmx_client(app: Litestar) -> AsyncIterator[AsyncTestClient]:
    """Yield an AsyncTestClient that sends `HX-Request: true`."""
    async with AsyncTestClient(app=app, raise_server_exceptions=False) as test_client:
        test_client.headers["HX-Request"] = "true"
        yield test_client


class MockOracleAsyncDriver(AsyncDriverAdapterBase):
    """Mock driver that bypasses compiled type checks in SQLSpec services."""

    def __init__(self) -> None:
        self.__dict__["_mock"] = MagicMock()

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("__") or name in {"_session", "session", "driver", "__dict__", "_mock"}:
            return super().__getattribute__(name)
        mock = super().__getattribute__("_mock")
        return getattr(mock, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_mock":
            super().__setattr__(name, value)
        else:
            setattr(self._mock, name, value)


@pytest.fixture
def mock_driver() -> MockOracleAsyncDriver:
    """Return a mock Oracle async driver that passes compiled type checks."""
    return MockOracleAsyncDriver()  # type: ignore[abstract]
