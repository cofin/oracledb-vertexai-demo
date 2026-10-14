# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Oracle 26ai QueueSettings and LOB-isolated queue database config."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest
from litestar_queues import QueueConfig, QueuePlugin, QueueService
from litestar_queues.backends.sqlspec import SQLSpecBackendConfig
from litestar_queues.backends.sqlspec.stores.factory import create_queue_store

from app import config
from app.ioc import make_container
from app.lib.settings import DatabaseSettings, QueueSettings, Settings
from app.server import plugins

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_get_queue_config_isolates_oracle_lob_features_from_main_db_config(monkeypatch: MonkeyPatch) -> None:
    """Ensure get_queue_config returns a dedicated OracleAsyncConfig so main db retains AutoLob."""
    for key in ("DATABASE_URL", "WALLET_PASSWORD", "WALLET_LOCATION", "TNS_ADMIN"):
        monkeypatch.delenv(key, raising=False)

    db_settings = DatabaseSettings()
    main_config = db_settings.get_config()
    queue_config = db_settings.get_queue_config()

    assert main_config is not queue_config
    assert main_config.driver_features.get("enable_AutoLob") is True
    assert queue_config.connection_config["min"] == 1
    assert queue_config.connection_config["max"] == 4
    litestar_ext = cast("dict[str, Any]", queue_config.extension_config["litestar"])
    assert litestar_ext["session_key"] == "queue_db_session"

    backend_cfg = SQLSpecBackendConfig(sqlspec_config=queue_config)
    assert backend_cfg.sqlspec_config is queue_config

    queue_config_mutated = dict(queue_config.driver_features)
    queue_config_mutated["fetch_lobs"] = True
    queue_config.driver_features["fetch_lobs"] = True
    create_queue_store(queue_config)

    assert queue_config.driver_features.get("fetch_lobs") is False
    assert main_config.driver_features.get("enable_AutoLob") is True


def test_queue_settings_builds_sqlspec_and_memory_configs(monkeypatch: MonkeyPatch) -> None:
    """Verify QueueSettings builds valid QueueConfig in both sqlspec and memory modes."""
    for key in (
        "QUEUE_ENABLED",
        "QUEUE_BACKEND",
        "QUEUE_EXECUTION_BACKEND",
        "QUEUE_WAKEUP_MODE",
        "QUEUE_CONCURRENCY",
        "QUEUE_POLL_INTERVAL",
        "QUEUE_MANAGE_SCHEMA",
        "ORACLE_QUEUE_IN_MEMORY",
    ):
        monkeypatch.delenv(key, raising=False)

    db_settings = DatabaseSettings()
    queue_db = db_settings.get_queue_config()

    default_queue = QueueSettings()
    assert default_queue.enabled is True
    assert default_queue.backend == "sqlspec"
    assert default_queue.execution_backend == "asgi"
    assert default_queue.wakeup_mode == "polling"
    assert default_queue.concurrency == 4
    assert default_queue.poll_interval == 2.0
    assert default_queue.manage_schema is True
    assert default_queue.in_memory is False

    sqlspec_qcfg = default_queue.get_config(queue_db)
    assert isinstance(sqlspec_qcfg, QueueConfig)
    assert isinstance(sqlspec_qcfg.queue_backend, SQLSpecBackendConfig)
    assert sqlspec_qcfg.queue_backend.sqlspec_config is queue_db
    assert sqlspec_qcfg.worker.placement == "asgi"
    assert sqlspec_qcfg.worker.max_concurrency == 4
    assert sqlspec_qcfg.worker.poll_interval == 2.0
    assert sqlspec_qcfg.queue_backend.worker_wakeups is not None
    assert sqlspec_qcfg.queue_backend.worker_wakeups.transport == "polling"

    monkeypatch.setenv("QUEUE_WAKEUP_MODE", "oracle_aq")
    monkeypatch.setenv("QUEUE_EXECUTION_BACKEND", "standalone")
    aq_queue = QueueSettings()
    aq_qcfg = aq_queue.get_config(queue_db)
    assert isinstance(aq_qcfg.queue_backend, SQLSpecBackendConfig)
    assert aq_qcfg.queue_backend.worker_wakeups is not None
    assert aq_qcfg.queue_backend.worker_wakeups.transport == "txeventq"
    assert aq_qcfg.worker.placement == "server"

    monkeypatch.setenv("ORACLE_QUEUE_IN_MEMORY", "true")
    monkeypatch.setenv("QUEUE_EXECUTION_BACKEND", "immediate")
    memory_queue = QueueSettings()
    assert memory_queue.in_memory is True
    assert memory_queue.backend == "memory"
    assert memory_queue.execution_backend == "immediate"
    mem_qcfg = memory_queue.get_config(queue_db)
    assert mem_qcfg.queue_backend == "memory"
    assert mem_qcfg.execution_backend == "immediate"
    assert mem_qcfg.worker.placement == "external"


@pytest.mark.anyio
async def test_plugins_and_ioc_wire_queue_plugin_and_service(monkeypatch: MonkeyPatch) -> None:
    """Verify QueuePlugin, Autowire queues integration, and Dishka QueueService provider."""
    monkeypatch.setenv("QUEUE_BACKEND", "memory")
    Settings.from_env.cache_clear()
    config._reset()
    try:
        assert isinstance(plugins.queue, QueuePlugin)
        assert plugins.autowire.config.integration_enabled("dishka") is True
        assert plugins.autowire.config.integration_enabled("queues") is True

        container = make_container()
        try:
            queue_service = await container.get(QueueService)
            assert isinstance(queue_service, QueueService)
        finally:
            await container.close()
    finally:
        Settings.from_env.cache_clear()
        config._reset()
