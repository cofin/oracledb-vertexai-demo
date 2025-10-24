# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
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
    from app.asgi import create_app

    return create_app()


@pytest.fixture
def client(app: Litestar) -> AsyncTestClient:
    """Create test client."""
    from litestar.testing import AsyncTestClient

    return AsyncTestClient(app=app, raise_server_exceptions=False)
