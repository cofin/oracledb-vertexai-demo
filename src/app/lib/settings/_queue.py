# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Background task queue settings for litestar-queues."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, cast

from litestar_queues import QueueConfig, WorkerConfig, WorkerPlacement
from litestar_queues.backends.sqlspec import SQLSpecBackendConfig, SQLSpecWorkerWakeupConfig

from app.lib.settings._database import DatabaseSettings
from app.lib.settings._env import _env_bool, _env_float, _env_int

if TYPE_CHECKING:
    from sqlspec.adapters.oracledb import OracleAsyncConfig

__all__ = ("QueueBackendMode", "QueueExecutionMode", "QueueSettings", "QueueWakeupMode")

QueueBackendMode = Literal["sqlspec", "memory"]
QueueExecutionMode = Literal["asgi", "standalone", "immediate", "none"]
QueueWakeupMode = Literal["polling", "oracle_aq"]


@dataclass(frozen=True, slots=True)
class QueueSettings:
    """Configuration settings for background task queues."""

    ENABLED: bool = field(default_factory=lambda: _env_bool("QUEUE_ENABLED", True))
    """Enable background task queue processing."""
    IN_MEMORY: bool = field(default_factory=lambda: _env_bool("ORACLE_QUEUE_IN_MEMORY", False))
    """Force in-memory queue storage instead of Oracle SQLSpec persistence."""
    BACKEND: QueueBackendMode = field(
        default_factory=lambda: (
            "memory"
            if _env_bool("ORACLE_QUEUE_IN_MEMORY", False)
            or os.getenv("QUEUE_BACKEND", "sqlspec").strip().lower() == "memory"
            else "sqlspec"
        )
    )
    """Queue storage backend ('sqlspec' or 'memory')."""
    EXECUTION_BACKEND: QueueExecutionMode = field(
        default_factory=lambda: (
            cast("QueueExecutionMode", raw)
            if (raw := os.getenv("QUEUE_EXECUTION_BACKEND", "asgi").strip().lower())
            in {"asgi", "standalone", "immediate", "none"}
            else "asgi"
        )
    )
    """Worker placement mode ('asgi', 'standalone', 'immediate', or 'none')."""
    WAKEUP_MODE: QueueWakeupMode = field(
        default_factory=lambda: (
            "oracle_aq" if os.getenv("QUEUE_WAKEUP_MODE", "polling").strip().lower() == "oracle_aq" else "polling"
        )
    )
    """Worker wakeup transport ('polling' or 'oracle_aq')."""
    CONCURRENCY: int = field(default_factory=lambda: _env_int("QUEUE_CONCURRENCY", 4))
    """Maximum concurrent tasks executed by the worker."""
    POLL_INTERVAL: float = field(default_factory=lambda: _env_float("QUEUE_POLL_INTERVAL", 2.0))
    """Base worker polling interval in seconds."""
    MANAGE_SCHEMA: bool = field(default_factory=lambda: _env_bool("QUEUE_MANAGE_SCHEMA", True))
    """Allow litestar-queues to register and manage queue schema migrations."""

    def get_config(self, sqlspec_config: OracleAsyncConfig | None = None) -> QueueConfig:
        """Build a ``QueueConfig`` instance from current settings.

        Args:
            sqlspec_config: Dedicated queue ``OracleAsyncConfig`` instance.

        Returns:
            Configured ``QueueConfig`` for ``QueuePlugin``.
        """
        effective_backend: QueueBackendMode = "memory" if self.IN_MEMORY else self.BACKEND
        effective_execution: Literal["local", "immediate"] = (
            "immediate" if self.EXECUTION_BACKEND == "immediate" else "local"
        )
        placement: WorkerPlacement
        if not self.ENABLED or self.EXECUTION_BACKEND in {"none", "immediate"}:
            placement = "external"
        elif self.EXECUTION_BACKEND == "standalone":
            placement = "asgi" if effective_backend == "memory" else "server"
        else:
            placement = "asgi"

        worker_config = WorkerConfig(
            placement=placement, max_concurrency=self.CONCURRENCY, poll_interval=self.POLL_INTERVAL
        )

        if effective_backend == "memory":
            return QueueConfig(
                namespace="coffee",
                queue_backend="memory",
                execution_backend=effective_execution,
                worker=worker_config,
                initialize_schedules=self.ENABLED and self.EXECUTION_BACKEND not in {"none", "immediate"},
            )

        if sqlspec_config is None:
            sqlspec_config = DatabaseSettings().get_queue_config()

        transport = "txeventq" if self.WAKEUP_MODE == "oracle_aq" else "polling"
        backend_config = SQLSpecBackendConfig(
            sqlspec_config=sqlspec_config,
            worker_wakeups=SQLSpecWorkerWakeupConfig(transport=transport),
            manage_schema=self.MANAGE_SCHEMA,
        )
        return QueueConfig(
            namespace="coffee",
            queue_backend=backend_config,
            execution_backend=effective_execution,
            worker=worker_config,
            initialize_schedules=self.ENABLED and self.EXECUTION_BACKEND not in {"none", "immediate"},
        )
