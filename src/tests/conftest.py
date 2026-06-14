# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from sqlspec.driver._async import AsyncDriverAdapterBase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from litestar import Litestar
    from litestar.testing import AsyncTestClient

from app.lib import settings as app_settings

if TYPE_CHECKING:
    from pytest import MonkeyPatch


pytestmark = pytest.mark.anyio

# Tests connect to the repo-managed Oracle database. Start it with
# `make start-infra` and apply migrations with
# `uv run python manage.py database upgrade --no-prompt`; pytest owns per-test state only.


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def test_settings(monkeypatch: MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> Iterator[app_settings.Settings]:
    """Patch the settings with test configuration.

    Creates a temporary test .env file with safe test values.
    """
    # Create temporary .env for testing
    test_dir = tmp_path_factory.mktemp("test_env")
    test_env = test_dir / ".env.testing"
    test_env.write_text("""# Test Configuration
DATABASE_USER=test_app
DATABASE_PASSWORD=test-secret
DATABASE_HOST=localhost
DATABASE_PORT=1521
DATABASE_SERVICE_NAME=freepdb1

GOOGLE_CLOUD_PROJECT=test-project
GOOGLE_API_KEY=test-api-key

LITESTAR_DEBUG=true
LITESTAR_HOST=127.0.0.1
LITESTAR_PORT=5007
LITESTAR_GRANIAN_IN_SUBPROCESS=false
LITESTAR_GRANIAN_USE_LITESTAR_LOGGER=true
SECRET_KEY=test-secret-key-32-characters-12

VITE_DEV_MODE=False
""")

    settings = app_settings.Settings.from_env(str(test_env))

    def get_settings(dotenv_filename: str = ".env.testing") -> app_settings.Settings:
        return settings

    monkeypatch.setattr(app_settings, "get_settings", get_settings)
    app_settings.Settings.from_env.cache_clear()
    from app import config as app_config

    app_config._reset()
    try:
        yield settings
    finally:
        app_settings.Settings.from_env.cache_clear()
        app_config._reset()


@pytest.fixture
def app(test_settings: app_settings.Settings) -> Litestar:
    """Create test app instance."""
    del test_settings
    from app.server.asgi import create_app

    return create_app()


@pytest.fixture
async def client(app: Litestar) -> AsyncIterator[AsyncTestClient]:
    """Create test client.

    Enters the AsyncTestClient as a context manager so the Litestar lifespan
    runs — this is what closes the Dishka container and Oracle pool between
    tests. Without it, container.close() is never invoked and subsequent
    tests fail with 500 errors from leaked pool handles.

    Yields:
        AsyncTestClient bound to ``app`` with the lifespan entered.
    """
    from litestar.testing import AsyncTestClient

    async with AsyncTestClient(app=app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
async def htmx_client(app: Litestar) -> AsyncIterator[AsyncTestClient]:
    """Test client that masquerades as HTMX (sends ``HX-Request: true``).

    Yields:
        AsyncTestClient that always sends ``HX-Request: true``.
    """
    from litestar.testing import AsyncTestClient

    async with AsyncTestClient(app=app, raise_server_exceptions=False) as test_client:
        test_client.headers["HX-Request"] = "true"
        yield test_client


class MockOracleAsyncDriver(AsyncDriverAdapterBase):
    """Mock driver that bypasses compiled type checks in SQLSpecServices.

    Delegates all attribute access to an internal MagicMock instance, except
    for class-level fields or parameters required by the compiled base.
    """

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
    """Fixture returning a mock driver that passes type checks."""
    return MockOracleAsyncDriver()
