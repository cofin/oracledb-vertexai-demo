# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Dishka IoC providers, container construction, and OracleAsyncService contracts."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from litestar_queues import QueueService
from sqlspec.adapters.oracledb import OracleAsyncConfig
from sqlspec.loader import SQLFileLoader

import app.ioc as ioc_module
from app.domain.ai.runtime import AgentStreamService
from app.ioc import (
    PROVIDERS,
    AIProvider,
    ConfigProvider,
    DBProvider,
    DomainServiceProvider,
    create_container,
    get_providers,
)
from app.lib.di import Inject, LitestarProvider, request_container_var, worker_container_var
from app.lib.service import OracleAsyncService
from app.lib.settings import ChatSettings, QueueSettings, Settings


def _collect_forbidden_ioc_imports(tree: ast.Module) -> list[str]:
    """Return forbidden import or future-annotation descriptions found in an IoC module AST."""
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = {alias.name for alias in node.names}
            if mod == "__future__" and "annotations" in names:
                violations.append("from __future__ import annotations")
            if mod in {"app.config", "app.server"} or mod.startswith(("app.config.", "app.server.")):
                violations.append(f"from {mod} import ...")
            if mod == "app" and ({"config", "server"} & names):
                violations.append(f"from app import {sorted({'config', 'server'} & names)}")
            if "get_settings" in names:
                violations.append(f"from {mod} import get_settings")
        elif isinstance(node, ast.Import):
            violations.extend(
                f"import {alias.name}"
                for alias in node.names
                if alias.name in {"app.config", "app.server"} or alias.name.startswith(("app.config.", "app.server."))
            )
    return violations


def test_ioc_package_modules_exclude_future_annotations_and_config_coupling() -> None:
    """Verify no file under src/app/ioc/ uses future annotations or imports app.config/app.server/get_settings."""
    ioc_dir = Path(__file__).resolve().parents[3] / "app" / "ioc"
    assert ioc_dir.is_dir()
    py_files = sorted(ioc_dir.glob("*.py"))
    assert py_files
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        violations = _collect_forbidden_ioc_imports(tree)
        assert violations == [], f"{py_file.name} violated IoC import boundaries: {violations}"


def test_ioc_public_exports_exclude_legacy_aliases() -> None:
    """Verify app.ioc exports only canonical providers and create_container without legacy aliases."""
    assert set(ioc_module.__all__) == {
        "AIProvider",
        "ConfigProvider",
        "DBProvider",
        "DomainServiceProvider",
        "PROVIDERS",
        "create_container",
        "get_providers",
    }
    assert not hasattr(ioc_module, "IntegrationsProvider")
    assert not hasattr(ioc_module, "LitestarPersistenceProvider")
    assert not hasattr(ioc_module, "make_container")


@pytest.mark.anyio
async def test_ioc_create_container_resolves_app_scoped_singletons(test_settings: Settings) -> None:
    """Verify create_container resolves Settings, SQLFileLoader, OracleAsyncConfig, QueueService, and APP-scoped AgentStreamService."""
    del test_settings
    assert (ConfigProvider, DBProvider, AIProvider, DomainServiceProvider) == PROVIDERS
    providers = get_providers()
    assert len(providers) == 4

    container = create_container(LitestarProvider())
    try:
        resolved_settings = await container.get(Settings)
        resolved_chat = await container.get(ChatSettings)
        resolved_queue = await container.get(QueueSettings)
        resolved_loader = await container.get(SQLFileLoader)
        resolved_db_cfg = await container.get(OracleAsyncConfig)
        stream_first = await container.get(AgentStreamService)
        stream_second = await container.get(AgentStreamService)
        queue_service = await container.get(QueueService)

        assert isinstance(resolved_settings, Settings)
        assert isinstance(resolved_chat, ChatSettings)
        assert isinstance(resolved_queue, QueueSettings)
        assert isinstance(resolved_loader, SQLFileLoader)
        assert isinstance(resolved_db_cfg, OracleAsyncConfig)
        assert isinstance(stream_first, AgentStreamService)
        assert stream_first is stream_second
        assert isinstance(queue_service, QueueService)
    finally:
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
