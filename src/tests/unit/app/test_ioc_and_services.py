# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for modular domain services, Dishka IOC package, and DI helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.products.services import (
    EmbeddingService,
    InventoryService,
    MapsService,
    OracleVectorSearchService,
    ProductService,
    StoreService,
    VertexAIService,
)
from app.domain.system.services import CacheService, MetricsService, PersonaManager, ResponseCacheService, SystemService
from app.ioc import (
    PROVIDERS,
    AIProvider,
    ConfigProvider,
    DBProvider,
    DomainServiceProvider,
    IntegrationsProvider,
    LitestarPersistenceProvider,
    create_container,
    get_providers,
    make_container,
)
from app.lib.di import Inject, request_container_var, worker_container_var
from app.lib.service import OracleAsyncService


def test_products_services_resolve_from_private_modules() -> None:
    """Verify products domain services originate from focused private _*.py modules."""
    assert ProductService.__module__ == "app.domain.products.services._products"
    assert EmbeddingService.__module__ == "app.domain.products.services._embedding"
    assert VertexAIService is EmbeddingService
    assert OracleVectorSearchService.__module__ == "app.domain.products.services._embedding"
    assert StoreService.__module__ == "app.domain.products.services._stores"
    assert InventoryService.__module__ == "app.domain.products.services._inventory"
    assert issubclass(InventoryService, StoreService)
    assert MapsService.__module__ == "app.domain.products.services._maps"
    assert "google.com/maps/search/" in MapsService.search_url(
        name="Cymbal Coffee",
        address="100 Main St",
        city="Dallas",
        state="TX",
        zip_code="75201",
    )


def test_system_services_resolve_from_private_modules() -> None:
    """Verify system domain services originate from focused private _*.py modules."""
    assert SystemService.__module__ == "app.domain.system.services._health"
    assert MetricsService is SystemService
    assert PersonaManager.__module__ == "app.domain.system.services._health"
    assert ResponseCacheService.__module__ == "app.domain.system.services._cache"
    assert CacheService is ResponseCacheService


def test_ioc_package_modules_exclude_future_annotations() -> None:
    """Verify no file under src/app/ioc/ uses from __future__ import annotations."""
    ioc_dir = Path(__file__).resolve().parents[3] / "app" / "ioc"
    assert ioc_dir.is_dir()
    py_files = sorted(ioc_dir.glob("*.py"))
    assert len(py_files) == 5
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        assert "from __future__ import annotations" not in content, f"{py_file.name} contains future annotations"


@pytest.mark.anyio
async def test_ioc_create_container_and_provider_aliases() -> None:
    """Verify create_container builds an AsyncContainer with all four providers."""
    assert AIProvider is IntegrationsProvider
    assert DBProvider is LitestarPersistenceProvider
    assert (ConfigProvider, DBProvider, AIProvider, DomainServiceProvider) == PROVIDERS
    providers = get_providers()
    assert len(providers) == 4
    container = create_container()
    assert make_container is create_container
    await container.close()


def test_di_exports_container_contextvars() -> None:
    """Verify app.lib.di exports Inject, request_container_var, and worker_container_var."""
    assert Inject is not None
    assert request_container_var.get() is None
    assert worker_container_var.get() is None


@pytest.mark.anyio
async def test_oracle_async_service_execute_many_supports_auto_commit() -> None:
    """Verify OracleAsyncService.execute_many delegates to driver and optionally commits."""
    driver = MagicMock()
    driver.execute_many = AsyncMock(return_value="batch-ok")
    driver.commit = AsyncMock()
    service = OracleAsyncService(driver)

    result = await service.execute_many("INSERT INTO t VALUES (:1)", [{"1": 1}], auto_commit=True)

    assert result == "batch-ok"
    driver.execute_many.assert_awaited_once()
    driver.commit.assert_awaited_once()
