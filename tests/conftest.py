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
from redis.asyncio import Redis

from app.config import base

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from pytest import MonkeyPatch


pytestmark = pytest.mark.anyio
pytest_plugins = [
    "tests.data_fixtures",
    "pytest_databases.docker",
    "pytest_databases.docker.oracle",
    "pytest_databases.docker.redis",
]


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: MonkeyPatch) -> None:
    """Path the settings."""

    settings = base.Settings.from_env(".env.testing")

    def get_settings(dotenv_filename: str = ".env.testing") -> base.Settings:
        return settings

    monkeypatch.setattr(base, "get_settings", get_settings)


@pytest.fixture(name="redis", autouse=True)
async def fx_redis(redis_docker_ip: str, redis_service: None, redis_port: int) -> AsyncGenerator[Redis, None]:
    """Redis instance for testing.

    Returns:
        Redis client instance, function scoped.
    """
    yield Redis(host=redis_docker_ip, port=redis_port)
