# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle 26ai database connection and pool settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from litestar_queues.backends.sqlspec.extension import configure_queue_migration_extension
from sqlspec.adapters.oracledb import OracleAsyncConfig
from sqlspec.adapters.oracledb.core import default_statement_config
from sqlspec.observability import LoggingConfig, ObservabilityConfig, TelemetryConfig

from app.lib.settings._env import BASE_DIR, _env_bool, _env_int

if TYPE_CHECKING:
    from sqlspec.core import StatementConfig

__all__ = ("DatabaseSettings",)


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Oracle Database connection settings."""

    URL: str | None = field(default_factory=lambda: os.getenv("DATABASE_URL"))
    """Oracle Database URL or TNS service alias (for Autonomous DB)."""
    WALLET_PASSWORD: str | None = field(default_factory=lambda: os.getenv("WALLET_PASSWORD"))
    """Oracle Database Wallet Password (for Autonomous DB)."""
    WALLET_LOCATION: str | None = field(default_factory=lambda: os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN"))
    """Oracle Database Wallet Location (for Autonomous DB). Falls back to TNS_ADMIN if set."""

    USER: str = field(default_factory=lambda: os.getenv("DATABASE_USER", "app"))
    """Oracle Database User."""
    PASSWORD: str = field(default_factory=lambda: os.getenv("DATABASE_PASSWORD", "SuperSecret1"))
    """Oracle Database Password."""
    HOST: str = field(default_factory=lambda: os.getenv("DATABASE_HOST", "localhost"))
    """Oracle Database Host."""
    PORT: str = field(default_factory=lambda: os.getenv("DATABASE_PORT", "1521"))
    """Oracle Database Port."""
    SERVICE_NAME: str = field(default_factory=lambda: os.getenv("DATABASE_SERVICE_NAME", "freepdb1"))
    """Oracle Database Service Name."""
    DSN: str = field(default_factory=lambda: os.getenv("DATABASE_DSN", ""))
    """Oracle Database DSN."""
    POOL_MIN_SIZE: int = field(default_factory=lambda: _env_int("DATABASE_POOL_MIN_SIZE", 5))
    """Minimum pool size."""
    POOL_MAX_SIZE: int = field(default_factory=lambda: _env_int("DATABASE_POOL_MAX_SIZE", 20))
    """Maximum pool size."""
    AGENT_IN_MEMORY: bool = field(default_factory=lambda: _env_bool("ORACLE_AGENT_IN_MEMORY", True))
    """Enable Oracle INMEMORY for agent session/event tables when licensed."""
    LITESTAR_SESSION_IN_MEMORY: bool = field(
        default_factory=lambda: _env_bool("ORACLE_LITESTAR_SESSION_IN_MEMORY", True)
    )
    """Enable Oracle INMEMORY for the Litestar server-side session table when licensed."""
    MIGRATION_PATH: str = field(
        default_factory=lambda: os.getenv("DATABASE_MIGRATION_PATH", str(BASE_DIR / "db" / "migrations"))
    )
    """Database migration path."""
    FIXTURE_PATH: str = f"{BASE_DIR}/db/fixtures"
    """The path to JSON fixture files to load into tables."""
    EVENTS_BACKEND: str = field(default_factory=lambda: os.getenv("ORACLE_EVENTS_BACKEND", "txeventq"))
    """Oracle event queue backend (e.g. 'txeventq' or 'aq')."""
    EVENTS_QUEUE: str = field(default_factory=lambda: os.getenv("ORACLE_EVENTS_QUEUE", "COFFEE_EVENTS_QUEUE"))
    """Oracle Transactional Event Queue name."""
    ECHO: bool = field(
        default_factory=lambda: _env_bool(
            "DATABASE_ECHO", _env_bool("DATABASE_ECHO_SQL", _env_bool("SQLSPEC_ECHO", False))
        )
    )
    """Echo executed SQL statements to stdout and logger."""
    ENABLE_TELEMETRY: bool = field(
        default_factory=lambda: _env_bool("DATABASE_ENABLE_TELEMETRY", _env_bool("SQLSPEC_ENABLE_TELEMETRY", True))
    )
    """Enable SQLSpec OpenTelemetry spans and trace context propagation."""

    def __post_init__(self) -> None:
        """Populate DSN from HOST, PORT, and SERVICE_NAME when not explicitly provided."""
        if not self.DSN:
            object.__setattr__(self, "DSN", f"{self.HOST}:{self.PORT}/{self.SERVICE_NAME}")

    @property
    def is_autonomous(self) -> bool:
        """Detect if we're using Autonomous Database based on presence of URL and wallet password."""
        return self.URL is not None and self.WALLET_PASSWORD is not None

    def get_connection_params(self) -> dict[str, Any]:
        """Extract connection parameters based on connection mode (autonomous vs local).

        Returns:
            Oracle connection parameters for the configured deployment mode.
        """
        if self.is_autonomous and self.URL is not None:
            raw_url = self.URL.strip()
            if "://" in raw_url:
                parsed = urlparse(raw_url)
                return {
                    "user": parsed.username or self.USER,
                    "password": parsed.password or self.PASSWORD,
                    "dsn": parsed.hostname or parsed.path.lstrip("/") or self.DSN,
                    "wallet_password": self.WALLET_PASSWORD or "",
                }
            return {
                "user": self.USER,
                "password": self.PASSWORD,
                "dsn": raw_url or self.DSN,
                "wallet_password": self.WALLET_PASSWORD or "",
            }
        return {"user": self.USER, "password": self.PASSWORD, "dsn": self.DSN}

    def create_config(self) -> OracleAsyncConfig:
        """Create Oracle database configuration based on connection mode (autonomous vs local).

        Returns:
            SQLSpec Oracle async configuration for the app.

        Raises:
            ValueError: If Autonomous Database is enabled without a wallet location.
        """
        pool_config = self._build_pool_config(min_sessions=self.POOL_MIN_SIZE, max_sessions=self.POOL_MAX_SIZE)
        config = OracleAsyncConfig(
            connection_config=pool_config,
            statement_config=self._build_statement_config(),
            observability_config=self._build_observability_config(),
            driver_features={"fetch_lobs": True, "enable_session_tracing": True},
            migration_config={
                "version_table_name": "migrations",
                "script_location": self.MIGRATION_PATH,
                "project_root": BASE_DIR,
                "include_extensions": ["litestar"],
            },
            extension_config={
                "litestar": {
                    "session_table": "app_session",
                    "in_memory": self.LITESTAR_SESSION_IN_MEMORY,
                    "disable_di": True,
                    "manage_lifespan": True,
                },
                "events": {"backend": self.EVENTS_BACKEND, "aq_queue": self.EVENTS_QUEUE},
            },
        )
        configure_queue_migration_extension(config, manage_schema=_env_bool("QUEUE_MANAGE_SCHEMA", True))
        return config

    def get_config(self) -> OracleAsyncConfig:
        """Alias for ``create_config`` matching reference platform conventions."""
        return self.create_config()

    def get_queue_config(self) -> OracleAsyncConfig:
        """Create a dedicated OracleAsyncConfig for ``litestar-queues`` SQLSpec storage.

        Isolates ``OracledbAsyncQueueStore``'s ``driver_features["fetch_lobs"] = False``
        mutation from the primary application ``OracleAsyncConfig``.

        Returns:
            Dedicated ``OracleAsyncConfig`` for background queue persistence.
        """
        pool_config = self._build_pool_config(min_sessions=1, max_sessions=4)
        return OracleAsyncConfig(
            connection_config=pool_config,
            statement_config=self._build_statement_config(),
            observability_config=self._build_observability_config(),
            driver_features={"fetch_lobs": False, "enable_session_tracing": True},
            extension_config={
                "litestar": {"session_key": "queue_db_session", "disable_di": True, "manage_lifespan": True},
                "events": {"backend": self.EVENTS_BACKEND, "aq_queue": self.EVENTS_QUEUE},
                "litestar_queues": {"in_memory": self.AGENT_IN_MEMORY},
            },
        )

    def _build_pool_config(self, *, min_sessions: int, max_sessions: int) -> dict[str, Any]:
        """Construct the Oracle connection pool parameter dictionary."""
        conn_params = self.get_connection_params()

        if self.is_autonomous:
            if not self.WALLET_LOCATION:
                msg = "WALLET_LOCATION or TNS_ADMIN environment variable must be set for Autonomous Database"
                raise ValueError(msg)

            wallet_path = str(Path(self.WALLET_LOCATION).resolve())
            return {
                "user": conn_params["user"],
                "password": conn_params["password"],
                "dsn": conn_params["dsn"],
                "wallet_zip": wallet_path,
                "wallet_password": conn_params["wallet_password"],
                "min": min_sessions,
                "max": max_sessions,
            }

        return {
            "user": conn_params["user"],
            "password": conn_params["password"],
            "dsn": conn_params["dsn"],
            "min": min_sessions,
            "max": max_sessions,
        }

    def _build_statement_config(self) -> StatementConfig:
        """Construct SQLSpec statement configuration with wire-level sqlcommenter."""
        return default_statement_config.replace(
            enable_sqlcommenter=True, sqlcommenter_enable_context=True, sqlcommenter_enable_traceparent=True
        )

    def _build_observability_config(self) -> ObservabilityConfig:
        """Construct SQLSpec observability settings."""
        return ObservabilityConfig(
            print_sql=self.ECHO,
            telemetry=TelemetryConfig(enable_spans=self.ENABLE_TELEMETRY),
            logging=LoggingConfig(include_trace_context=True, include_sql_hash=True),
        )
