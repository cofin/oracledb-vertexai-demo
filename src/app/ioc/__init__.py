# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka container configuration package for Litestar and CLI."""

from dishka import AsyncContainer, Provider, make_async_container

from app.ioc._ai import AIProvider, IntegrationsProvider
from app.ioc._config import ConfigProvider
from app.ioc._database import DBProvider, LitestarPersistenceProvider
from app.ioc._domain import DomainServiceProvider
from app.lib.settings import get_settings

__all__ = (
    "PROVIDERS",
    "AIProvider",
    "ConfigProvider",
    "DBProvider",
    "DomainServiceProvider",
    "IntegrationsProvider",
    "LitestarPersistenceProvider",
    "create_container",
    "get_providers",
    "get_settings",
    "make_container",
)

PROVIDERS: tuple[type[Provider], ...] = (
    ConfigProvider,
    DBProvider,
    AIProvider,
    DomainServiceProvider,
)


def get_providers() -> tuple[Provider, ...]:
    """Instantiate the standard Dishka provider set."""
    return tuple(provider_cls() for provider_cls in PROVIDERS)


def create_container(*extra_providers: Provider) -> AsyncContainer:
    """Build the Dishka container with the application providers plus any extras."""
    return make_async_container(*extra_providers, *get_providers())


make_container = create_container
