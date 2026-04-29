# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar import Litestar
    from litestar.testing import AsyncTestClient

from app.lib import settings as app_settings

if TYPE_CHECKING:
    from pytest import MonkeyPatch


pytestmark = pytest.mark.anyio
pytest_plugins = [
    "pytest_databases.docker",
    "pytest_databases.docker.oracle",
]


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
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

VITE_HOST=localhost
VITE_PORT=51746
VITE_HOT_RELOAD=False
VITE_DEV_MODE=False
""")

    settings = app_settings.Settings.from_env(str(test_env))

    def get_settings(dotenv_filename: str = ".env.testing") -> app_settings.Settings:
        return settings

    monkeypatch.setattr(app_settings, "get_settings", get_settings)


@pytest.fixture
def app() -> Litestar:
    """Create test app instance."""
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

    Phase 4 chat partials and Phase 5 explore partials branch on
    ``request.htmx``; this fixture exercises that branch end-to-end.

    Yields:
        AsyncTestClient that always sends ``HX-Request: true``.
    """
    from litestar.testing import AsyncTestClient

    async with AsyncTestClient(app=app, raise_server_exceptions=False) as test_client:
        test_client.headers["HX-Request"] = "true"
        yield test_client
