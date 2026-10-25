# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Connection tester and deployment-mode detection for Oracle 26ai databases."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import oracledb
from rich.console import Console
from rich.table import Table
from sqlspec.adapters.oracledb import extract_oracle_wallet_zip

__all__ = (
    "AutonomousConnectionError",
    "ConnectionConfig",
    "ConnectionInfo",
    "ConnectionTestResult",
    "ConnectionTester",
    "DeploymentMode",
    "LocalConnectionError",
    "OracleConnectionError",
    "RemoteConnectionError",
    "detect_deployment_mode",
    "get_connection_suggestions",
)

_SQLALCHEMY_URL_RE = re.compile(r"oracle\+oracledb://([^:]+):([^@]+)@(.+)")
_DEFAULT_DEV_SECRET = "SuperSecret1"  # ruff: ignore[hardcoded-password-string]


class DeploymentMode(StrEnum):
    """Database deployment modes."""

    MANAGED = "managed"
    EXTERNAL = "external"


class OracleConnectionError(Exception):
    """Base exception for connection errors."""


class LocalConnectionError(OracleConnectionError):
    """Raised when a local container connection fails."""


class RemoteConnectionError(OracleConnectionError):
    """Raised when a remote database connection fails."""


class AutonomousConnectionError(OracleConnectionError):
    """Raised when an Autonomous AI Database connection fails."""


def detect_deployment_mode() -> DeploymentMode:
    """Resolve deployment mode from ``DATABASE_DEPLOYMENT_MODE`` or host/URL settings."""
    explicit = os.getenv("DATABASE_DEPLOYMENT_MODE", "").strip().lower()
    if explicit == DeploymentMode.MANAGED.value:
        return DeploymentMode.MANAGED
    if explicit == DeploymentMode.EXTERNAL.value:
        return DeploymentMode.EXTERNAL

    if os.getenv("DATABASE_HOST") or os.getenv("DATABASE_URL"):
        return DeploymentMode.EXTERNAL
    return DeploymentMode.MANAGED


def get_connection_suggestions(mode: DeploymentMode, error: str, has_wallet: bool = False) -> list[str]:
    """Return actionable troubleshooting suggestions for a connection failure."""
    suggestions: list[str] = []
    error_lower = error.lower()

    if has_wallet:
        if "wallet" in error_lower:
            suggestions.extend([
                "Verify WALLET_LOCATION points to a valid wallet directory or .zip",
                "Check TNS_ADMIN is set or matches WALLET_LOCATION",
            ])
        if "password" in error_lower:
            suggestions.append("Verify WALLET_PASSWORD matches the wallet password")
        if "tns" in error_lower or "service" in error_lower:
            suggestions.extend([
                "Verify DATABASE_URL / DATABASE_SERVICE_NAME matches a service in tnsnames.ora (e.g. myatp_low)",
                "Check wallet files: cwallet.sso, tnsnames.ora, sqlnet.ora",
            ])

    if mode == DeploymentMode.MANAGED:
        suggestions.extend([
            "Check if the Oracle container is running: docker ps",
            "Start managed ADB-Free container: uv run python manage.py infra start",
        ])
        if "refused" in error_lower or "cannot connect" in error_lower:
            suggestions.append("Verify listener port mappings (1521/1522 and HTTPS 8443)")
        if "invalid username" in error_lower or "invalid password" in error_lower:
            suggestions.append("Check DATABASE_USER and DATABASE_PASSWORD environment variables")
    elif mode == DeploymentMode.EXTERNAL:
        if "refused" in error_lower or "cannot connect" in error_lower:
            suggestions.extend(["Verify host and port are correct", "Check firewall rules and database listener state"])
        if "invalid username" in error_lower or "invalid password" in error_lower:
            suggestions.append("Verify DATABASE_USER and DATABASE_PASSWORD")

    return suggestions


@dataclass(slots=True)
class ConnectionConfig:
    """Database connection configuration across managed and external modes."""

    mode: DeploymentMode
    user: str
    password: str
    host: str | None = None
    port: int | None = None
    service_name: str | None = None
    dsn: str | None = None
    wallet_location: Path | None = None
    wallet_password: str | None = None
    database_url: str | None = None

    @classmethod
    def from_env(cls) -> ConnectionConfig:
        """Create connection configuration from environment variables."""
        mode = detect_deployment_mode()
        wallet_location = os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN")
        wallet_password = os.getenv("WALLET_PASSWORD")
        database_url = os.getenv("DATABASE_URL")

        if database_url:
            match = _SQLALCHEMY_URL_RE.match(database_url)
            if match:
                user, password, service_name = match.groups()
                return cls(
                    mode=mode,
                    user=user,
                    password=password,
                    service_name=service_name,
                    database_url=database_url,
                    wallet_location=Path(wallet_location) if wallet_location else None,
                    wallet_password=wallet_password,
                )

        user = os.getenv("DATABASE_USER", "app")
        password = os.getenv("DATABASE_PASSWORD", "SuperSecret1" if mode == DeploymentMode.MANAGED else "")
        host = os.getenv("DATABASE_HOST", "localhost" if mode == DeploymentMode.MANAGED else "")
        port = int(os.getenv("DATABASE_PORT", "1521"))
        default_service = "myatp_low" if wallet_location else "freepdb1"
        service_name = (
            database_url.strip()
            if database_url and "://" not in database_url
            else os.getenv("DATABASE_SERVICE_NAME", default_service)
        )
        dsn = os.getenv("DATABASE_DSN")

        return cls(
            mode=mode,
            user=user,
            password=password,
            host=host,
            port=port,
            service_name=service_name,
            dsn=dsn,
            wallet_location=Path(wallet_location) if wallet_location else None,
            wallet_password=wallet_password,
            database_url=database_url,
        )

    @classmethod
    def for_managed(
        cls,
        user: str = "app",
        password: str = _DEFAULT_DEV_SECRET,
        host: str = "localhost",
        port: int = 1521,
        service_name: str = "myatp_low",
        wallet_location: Path | None = Path(".envs/tns"),
        wallet_password: str | None = _DEFAULT_DEV_SECRET,
    ) -> ConnectionConfig:
        """Create configuration for the managed ``cymbal-adb-free`` container."""
        return cls(
            mode=DeploymentMode.MANAGED,
            user=user,
            password=password,
            host=host,
            port=port,
            service_name=service_name,
            wallet_location=wallet_location,
            wallet_password=wallet_password,
        )

    @classmethod
    def for_external(
        cls,
        user: str,
        password: str,
        host: str | None = None,
        port: int = 1521,
        service_name: str = "freepdb1",
        database_url: str | None = None,
        wallet_location: Path | None = None,
        wallet_password: str | None = None,
    ) -> ConnectionConfig:
        """Create configuration for an external Oracle database (with optional wallet)."""
        return cls(
            mode=DeploymentMode.EXTERNAL,
            user=user,
            password=password,
            host=host,
            port=port,
            service_name=service_name,
            database_url=database_url,
            wallet_location=wallet_location,
            wallet_password=wallet_password,
        )

    def get_dsn(self) -> str:
        """Return the effective DSN or TNS alias string."""
        if self.dsn:
            return self.dsn
        if self.wallet_location:
            return self.service_name or ""
        return f"{self.host}:{self.port}/{self.service_name}"


@dataclass(slots=True)
class ConnectionTestResult:
    """Outcome of a database connection test."""

    success: bool
    mode: DeploymentMode
    message: str
    connection_time_ms: float | None = None
    server_version: str | None = None
    user_info: dict[str, Any] | None = None
    error: str | None = None
    suggestions: list[str] | None = None


@dataclass(slots=True)
class ConnectionInfo:
    """Detailed connection parameters for display and diagnostics."""

    mode: DeploymentMode
    host: str
    port: int
    service_name: str
    user: str
    dsn: str
    wallet_location: str | None = None
    database_url: str | None = None


class ConnectionTester:
    """Test Oracle database connectivity across managed and external deployment modes."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the connection tester."""
        self.console = console or Console()

    def test(
        self, config: ConnectionConfig | None = None, *, timeout: int = 10, display: bool = True
    ) -> ConnectionTestResult:
        """Execute a connectivity and authentication test against the configured database."""
        resolved_config = config if config is not None else ConnectionConfig.from_env()
        result = self._do_connection_test(resolved_config, timeout)
        if display:
            self.display_test_result(result)
        return result

    def get_connection_info(self, config: ConnectionConfig | None = None) -> ConnectionInfo:
        """Return structured connection details."""
        resolved_config = config if config is not None else ConnectionConfig.from_env()
        return ConnectionInfo(
            mode=resolved_config.mode,
            host=resolved_config.host or "N/A",
            port=resolved_config.port or 0,
            service_name=resolved_config.service_name or "N/A",
            user=resolved_config.user,
            dsn=resolved_config.get_dsn(),
            wallet_location=str(resolved_config.wallet_location) if resolved_config.wallet_location else None,
            database_url=resolved_config.database_url,
        )

    def display_test_result(self, result: ConnectionTestResult) -> None:
        """Render connection test results to the Rich console."""
        self.console.print()
        if result.success:
            self.console.print(f"[green]✓ {result.message}[/green]")
            if result.connection_time_ms:
                self.console.print(f"  Connection time: {result.connection_time_ms:.2f}ms")
            if result.server_version:
                self.console.print(f"  Server version: {result.server_version}")
        else:
            self.console.print(f"[red]✗ {result.message}[/red]")
            if result.suggestions:
                self.console.print("\n[yellow]Suggestions:[/yellow]")
                for suggestion in result.suggestions:
                    self.console.print(f"  • {suggestion}")
        self.console.print()

    def display_connection_info(self, info: ConnectionInfo) -> None:
        """Render a Rich table of connection details."""
        table = Table(title="Connection Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Mode", info.mode.value)
        table.add_row("Host", info.host)
        table.add_row("Port", str(info.port))
        table.add_row("Service Name", info.service_name)
        table.add_row("User", info.user)
        table.add_row("DSN", info.dsn)

        if info.wallet_location:
            table.add_row("Wallet Location", info.wallet_location)
        if info.database_url:
            table.add_row("Database URL", info.database_url)

        self.console.print(table)

    def validate_credentials(self, config: ConnectionConfig) -> bool:
        """Validate required connection and wallet fields without opening a socket."""
        if not config.user or not config.password:
            return False

        if config.wallet_location:
            if not config.wallet_location.exists():
                return False
            if config.wallet_location.is_file() and config.wallet_location.suffix == ".zip":
                return True
            required_files = ("cwallet.sso", "tnsnames.ora", "sqlnet.ora")
            return all((config.wallet_location / name).exists() for name in required_files)

        return bool(config.host and config.port and config.service_name)

    def _do_connection_test(self, config: ConnectionConfig, timeout: int = 10) -> ConnectionTestResult:
        """Run preflight wallet validation and a live ``SELECT 'OK' FROM DUAL`` probe."""
        del timeout
        start_time = time.time()

        if config.wallet_location and not config.wallet_location.exists():
            return ConnectionTestResult(
                success=False,
                mode=config.mode,
                message=f"Wallet path not found: {config.wallet_location}",
                error=f"Path does not exist: {config.wallet_location}",
                suggestions=[
                    "Verify WALLET_LOCATION path",
                    "Start ADB-Free to export wallet: uv run python manage.py infra start",
                ],
            )

        try:
            return self._run_connection_probe(config, start_time=start_time)
        except Exception as exc:
            error_msg = str(exc)
            suggestions = get_connection_suggestions(config.mode, error_msg, config.wallet_location is not None)
            return ConnectionTestResult(
                success=False,
                mode=config.mode,
                message=f"Connection failed: {error_msg}",
                error=error_msg,
                suggestions=suggestions,
            )

    def _run_connection_probe(self, config: ConnectionConfig, *, start_time: float) -> ConnectionTestResult:
        """Open a ``python-oracledb`` connection and verify ``SELECT 'OK' FROM DUAL``."""
        dsn = config.get_dsn()
        conn_params = self._connection_params(config, dsn)
        with oracledb.connect(**conn_params) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 'OK' FROM DUAL")
                cursor.fetchone()
            connection_time_ms = (time.time() - start_time) * 1000
            return self._successful_connection_result(config, dsn, str(connection.version), connection_time_ms)

    @staticmethod
    def _connection_params(config: ConnectionConfig, dsn: str) -> dict[str, Any]:
        """Build ``python-oracledb`` connection parameters, normalizing `.zip` or PEM wallets via SQLSpec."""
        conn_params: dict[str, Any] = {"user": config.user, "password": config.password, "dsn": dsn}
        if config.wallet_location:
            resolved_wallet = extract_oracle_wallet_zip(config.wallet_location, wallet_password=config.wallet_password)
            wallet_path = str(resolved_wallet)
            conn_params["wallet_location"] = wallet_path
            conn_params["config_dir"] = wallet_path
        if config.wallet_password:
            conn_params["wallet_password"] = config.wallet_password
        return conn_params

    @staticmethod
    def _successful_connection_result(
        config: ConnectionConfig, dsn: str, version: str, connection_time_ms: float
    ) -> ConnectionTestResult:
        """Build a successful ``ConnectionTestResult``."""
        mode_desc = "managed container" if config.mode == DeploymentMode.MANAGED else "external database"
        wallet_desc = " (wallet)" if config.wallet_location else ""
        return ConnectionTestResult(
            success=True,
            mode=config.mode,
            message=f"Successfully connected to {mode_desc}{wallet_desc}: {dsn}",
            connection_time_ms=connection_time_ms,
            server_version=version,
        )
