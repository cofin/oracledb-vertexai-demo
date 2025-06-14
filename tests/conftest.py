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
def _patch_settings(monkeypatch: MonkeyPatch) -> None:
    """Path the settings."""

    settings = app_settings.Settings.from_env(".env.testing")

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
