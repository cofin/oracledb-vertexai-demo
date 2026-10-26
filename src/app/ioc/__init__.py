# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka container configuration package for Litestar and CLI."""

from dishka import AsyncContainer, Provider, make_async_container
from litestar_queues import QueuePlugin
from sqlspec.adapters.oracledb import OracleAsyncConfig

from app.ioc._ai import AIProvider
from app.ioc._config import ConfigProvider
from app.ioc._database import DBProvider
from app.ioc._domain import DomainServiceProvider

__all__ = (
    "PROVIDERS",
    "AIProvider",
    "ConfigProvider",
    "DBProvider",
    "DomainServiceProvider",
    "create_container",
    "get_providers",
)

PROVIDERS: tuple[type[Provider], ...] = (ConfigProvider, DBProvider, AIProvider, DomainServiceProvider)


def get_providers(
    *,
    db_config: OracleAsyncConfig | None = None,
    queue_config: OracleAsyncConfig | None = None,
    queue_plugin: QueuePlugin | None = None,
) -> tuple[Provider, ...]:
    """Instantiate the standard Dishka provider set."""
    return (
        ConfigProvider(),
        DBProvider(db_config=db_config, queue_config=queue_config, queue_plugin=queue_plugin),
        AIProvider(),
        DomainServiceProvider(),
    )


def create_container(
    *extra_providers: Provider,
    db_config: OracleAsyncConfig | None = None,
    queue_config: OracleAsyncConfig | None = None,
    queue_plugin: QueuePlugin | None = None,
) -> AsyncContainer:
    """Build the Dishka container with the application providers plus any extras."""
    return make_async_container(
        *extra_providers, *get_providers(db_config=db_config, queue_config=queue_config, queue_plugin=queue_plugin)
    )
