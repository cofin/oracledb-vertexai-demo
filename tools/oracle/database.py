# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle 26ai container lifecycle management for ADB-Free and Oracle Free flavors."""

from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from rich.console import Console

from tools.oracle.adb import (
    ADB_FREE_CONTAINER_NAME,
    ADB_FREE_DATA_VOLUME,
    ADB_FREE_DEFAULT_IMAGE,
    ADB_FREE_DEFAULT_SERVICE,
    AdbBootstrap,
    AdbBootstrapConfig,
    AdbBootstrapError,
)
from tools.oracle.container import ContainerNotFoundError, ContainerRuntime, RuntimeType

__all__ = (
    "ADB_FREE_IMAGE",
    "DEFAULT_FREE_IMAGE",
    "LEGACY_FREE_CONTAINER_NAME",
    "PDB_SERVICE_NAME",
    "ContainerFlavor",
    "ContainerStartError",
    "ContainerStatus",
    "DatabaseConfig",
    "DatabaseError",
    "OracleDatabase",
)

ADB_FREE_IMAGE = ADB_FREE_DEFAULT_IMAGE
DEFAULT_FREE_IMAGE = "gvenzl/oracle-free:latest"
DEFAULT_HOST_PORT = 1521
LEGACY_FREE_CONTAINER_NAME = "oracle-free-db"
PDB_SERVICE_NAME = "freepdb1"
ORACLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]*$")
_DEFAULT_DEV_SECRET = "SuperSecret1"  # ruff: ignore[hardcoded-password-string]


class ContainerFlavor(StrEnum):
    """Supported local Oracle 26ai container distributions."""

    ADB_FREE = "adb-free"
    FREE = "free"


class DatabaseError(Exception):
    """Base exception for database container operations."""


class ContainerStartError(DatabaseError):
    """Raised when the Oracle container fails to start or bootstrap."""


@dataclass(slots=True)
class ContainerStatus:
    """Container runtime state snapshot."""

    exists: bool
    running: bool
    healthy: bool | None
    status: str
    container_id: str | None
    uptime: str | None
    ports: dict[str, str]
    image: str
    created_at: str | None


@dataclass(slots=True)
class DatabaseConfig:
    """Configuration for the local Oracle 26ai container (`adb-free` or `free`)."""

    flavor: ContainerFlavor = ContainerFlavor.ADB_FREE
    container_name: str = ""
    image: str = ""
    hostname: str = ""
    host_port: int = 1521
    container_port: int = 0
    tls_host_port: int = 1522
    https_port: int = 8443
    service_name: str = ""
    wallet_dir: Path = field(default_factory=lambda: Path(".envs/tns"))
    wallet_password: str = _DEFAULT_DEV_SECRET
    oracle_system_password: str = _DEFAULT_DEV_SECRET
    oracle_password: str = _DEFAULT_DEV_SECRET
    app_user: str = "app"
    app_user_password: str = _DEFAULT_DEV_SECRET
    data_volume_name: str = ""
    workload_type: str = "ATP"
    enable_archive_log: bool = False
    workspace_name: str = "COFFEE"
    log_max_size: str = "10m"
    log_max_file: str = "3"
    health_interval: int = 10
    health_timeout: int = 5
    health_retries: int = 10
    restart_policy: str = "unless-stopped"

    def __post_init__(self) -> None:
        """Populate flavor-specific defaults when fields are omitted."""
        defaults = (
            (LEGACY_FREE_CONTAINER_NAME, DEFAULT_FREE_IMAGE, "db", 1521, PDB_SERVICE_NAME, "oracle-db-data")
            if self.flavor == ContainerFlavor.FREE
            else (
                ADB_FREE_CONTAINER_NAME,
                ADB_FREE_IMAGE,
                "adb-free",
                1522,
                ADB_FREE_DEFAULT_SERVICE,
                ADB_FREE_DATA_VOLUME,
            )
        )
        name, image, hostname, port, service, volume = defaults
        self.container_name = self.container_name or name
        self.image = self.image or image
        self.hostname = self.hostname or hostname
        self.container_port = self.container_port if self.container_port > 0 else port
        self.service_name = self.service_name or service
        self.data_volume_name = self.data_volume_name or volume

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """Create container configuration from environment variables."""
        raw_flavor = os.getenv("ORACLE_CONTAINER_FLAVOR", ContainerFlavor.ADB_FREE.value).strip().lower()
        flavor = ContainerFlavor.FREE if raw_flavor == ContainerFlavor.FREE.value else ContainerFlavor.ADB_FREE
        host_port = int(os.getenv("DATABASE_PORT", os.getenv("ORACLE26AI_PORT", os.getenv("ORACLE23AI_PORT", "1521"))))
        tls_host_port = int(os.getenv("ORACLE_TLS_PORT", "1522"))
        https_port = int(os.getenv("ORACLE_HTTPS_PORT", "8443"))
        default_pw = "super-secret" if flavor == ContainerFlavor.FREE else "SuperSecret1"
        oracle_system_pw = os.getenv(
            "ORACLE_ADMIN_PASSWORD", os.getenv("ORACLE_SYSTEM_PASSWORD", os.getenv("ORACLE_PASSWORD", default_pw))
        )
        wallet_loc = os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN") or ".envs/tns"
        default_service = PDB_SERVICE_NAME if flavor == ContainerFlavor.FREE else ADB_FREE_DEFAULT_SERVICE
        raw_service = os.getenv("DATABASE_SERVICE_NAME", default_service)
        if flavor == ContainerFlavor.ADB_FREE and raw_service.lower() == PDB_SERVICE_NAME:
            raw_service = ADB_FREE_DEFAULT_SERVICE
        return cls(
            flavor=flavor,
            container_name=os.getenv("ORACLE_CONTAINER_NAME", ""),
            image=os.getenv("ORACLE_IMAGE", ""),
            host_port=host_port,
            tls_host_port=tls_host_port,
            https_port=https_port,
            service_name=raw_service,
            wallet_dir=Path(wallet_loc),
            wallet_password=os.getenv("WALLET_PASSWORD", "SuperSecret1"),
            oracle_system_password=oracle_system_pw,
            oracle_password=os.getenv("ORACLE_PASSWORD", oracle_system_pw),
            app_user=os.getenv("DATABASE_USER", "app"),
            app_user_password=os.getenv("DATABASE_PASSWORD", "SuperSecret1"),
            workspace_name=os.getenv("APEX_WORKSPACE", "COFFEE"),
        )


class OracleDatabase:
    """Manage the local Oracle 26ai container lifecycle (`adb-free` or `free`)."""

    def __init__(
        self, runtime: ContainerRuntime, config: DatabaseConfig | None = None, console: Console | None = None
    ) -> None:
        """Initialize the Oracle container manager."""
        self.runtime = runtime
        self.config = config or DatabaseConfig.from_env()
        self.console = console or Console()

    def build_run_command(self) -> list[str]:
        """Build the container ``run`` argument vector for the configured flavor."""
        if self.config.flavor == ContainerFlavor.ADB_FREE:
            return self._build_adb_free_run_command()
        return self._build_free_run_command()

    def to_adb_bootstrap_config(self) -> AdbBootstrapConfig:
        """Build an ``AdbBootstrapConfig`` aligned with this database configuration."""
        return AdbBootstrapConfig(
            container_name=self.config.container_name,
            wallet_dir=self.config.wallet_dir,
            wallet_password=self.config.wallet_password,
            admin_password=self.config.oracle_password,
            app_user=self.config.app_user,
            app_password=self.config.app_user_password,
            service_name=self.config.service_name,
            tls_port=self.config.tls_host_port,
            https_port=self.config.https_port,
            workspace_name=self.config.workspace_name,
        )

    def start(self, *, pull: bool = False, recreate: bool = False) -> None:
        """Start or reuse the configured Oracle 26ai container and ensure schema readiness."""
        self.console.rule("[bold blue]Starting Oracle Database Container")
        self._guard_port_collision()

        if self.runtime.container_running(self.config.container_name):
            if not recreate:
                self.console.print("[green]✓[/green] Container already running — reusing it")
                self._finalize_ready_container(timeout=180)
                return
            self.console.print("[yellow]Removing existing container...[/yellow]")
            self.remove(force=True)

        if self.runtime.container_exists(self.config.container_name):
            if recreate:
                self.console.print("[yellow]Removing existing container...[/yellow]")
                self.remove()
            else:
                self.console.print("[cyan]Starting existing container...[/cyan]")
                self.runtime.run_command(["start", self.config.container_name])
                self.console.print("[green]✓[/green] Container started")
                self._finalize_ready_container(timeout=360)
                return

        if pull:
            self._pull_image()
        self._create_volume(self.config.data_volume_name)

        run_cmd = self.build_run_command()
        self.console.print("[cyan]Creating and starting container...[/cyan]")
        try:
            _, stdout, _stderr = self.runtime.run_command(run_cmd)
            container_id = stdout.strip()[:12]
            self.console.print(f"[green]✓[/green] Container created: [dim]{container_id}[/dim]")
        except Exception as exc:
            raise ContainerStartError(f"Failed to start container: {exc}") from exc

        self._finalize_ready_container(timeout=360 if self.config.flavor == ContainerFlavor.ADB_FREE else 300)
        self.console.print("[green]✓[/green] Database is healthy and ready")
        info = self.get_connection_info()
        self.console.print("\n[bold]Connection Info:[/bold]")
        self.console.print(f"  Host: {info['host']}")
        self.console.print(f"  Port: {info['port']}")
        self.console.print(f"  Service: {info['service_name']}")
        self.console.print(f"  User: {info['user']}")
        self.console.print(f"  DSN: {info['dsn']}")

    def stop(self, *, timeout: int = 30) -> None:
        """Stop the Oracle database container."""
        if not self.runtime.container_exists(self.config.container_name):
            raise ContainerNotFoundError(f"Container '{self.config.container_name}' does not exist")

        self.console.print("[cyan]Stopping container...[/cyan]")
        self.runtime.run_command(["stop", "-t", str(timeout), self.config.container_name])
        self.console.print("[green]✓[/green] Container stopped")

    def restart(self, *, timeout: int = 30) -> None:
        """Restart the Oracle database container."""
        if not self.runtime.container_exists(self.config.container_name):
            raise ContainerNotFoundError(f"Container '{self.config.container_name}' does not exist")

        self.console.print("[cyan]Restarting container...[/cyan]")
        self.runtime.run_command(["restart", "-t", str(timeout), self.config.container_name])
        self.console.print("[green]✓[/green] Container restarted")

    def remove(self, *, volumes: bool = False, force: bool = False) -> None:
        """Remove the Oracle database container and optionally its data volume."""
        if not self.runtime.container_exists(self.config.container_name):
            raise ContainerNotFoundError(f"Container '{self.config.container_name}' does not exist")

        remove_cmd = ["rm"]
        if force:
            remove_cmd.append("-f")
        remove_cmd.append(self.config.container_name)

        self.console.print("[cyan]Removing container...[/cyan]")
        self.runtime.run_command(remove_cmd)
        self.console.print("[green]✓[/green] Container removed")

        if volumes and self.runtime.volume_exists(self.config.data_volume_name):
            self.console.print(f"[cyan]Removing volume {self.config.data_volume_name}...[/cyan]")
            self.runtime.run_command(["volume", "rm", self.config.data_volume_name])
            self.console.print("[green]✓[/green] Volume removed")

    def logs(self, *, follow: bool = False, tail: int | None = None, since: str | None = None) -> None:
        """Stream container logs."""
        if not self.runtime.container_exists(self.config.container_name):
            raise ContainerNotFoundError(f"Container '{self.config.container_name}' does not exist")

        logs_cmd = ["logs"]
        if follow:
            logs_cmd.append("-f")
        if tail:
            logs_cmd.extend(["--tail", str(tail)])
        if since:
            logs_cmd.extend(["--since", since])
        logs_cmd.append(self.config.container_name)

        self.runtime.run_command(logs_cmd, capture_output=False)

    def status(self) -> ContainerStatus:
        """Return detailed container status."""
        exists = self.runtime.container_exists(self.config.container_name)
        if not exists:
            return ContainerStatus(
                exists=False,
                running=False,
                healthy=None,
                status="not found",
                container_id=None,
                uptime=None,
                ports={},
                image=self.config.image,
                created_at=None,
            )

        status_dict = self.runtime.get_container_status(self.config.container_name)
        running = self.runtime.container_running(self.config.container_name)
        healthy = self.is_healthy() if running else None
        ports = {str(self.config.container_port): str(self.config.host_port)}
        if self.config.flavor == ContainerFlavor.ADB_FREE:
            ports["8443"] = str(self.config.https_port)
            ports["1522"] = f"{self.config.host_port},{self.config.tls_host_port}"

        return ContainerStatus(
            exists=True,
            running=running,
            healthy=healthy,
            status=status_dict.get("status", "unknown"),
            container_id=status_dict.get("id"),
            uptime=None,
            ports=ports,
            image=status_dict.get("image", self.config.image),
            created_at=status_dict.get("created"),
        )

    def is_running(self) -> bool:
        """Return True if the container is currently running."""
        return self.runtime.container_running(self.config.container_name)

    def is_healthy(self) -> bool:
        """Return True if the container health check or wallet readiness probe passes."""
        if not self.is_running():
            return False

        try:
            _, stdout, _ = self.runtime.run_command(
                [
                    "inspect",
                    "--format",
                    "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
                    self.config.container_name,
                ],
                check=False,
            )
        except Exception:
            return False

        health_state = stdout.strip()
        if health_state == "healthy":
            return True
        if self.config.flavor == ContainerFlavor.ADB_FREE and health_state in {"none", ""}:
            returncode, _, _ = self.runtime.run_command(
                ["exec", self.config.container_name, "test", "-f", "/u01/app/oracle/wallets/tls_wallet/tnsnames.ora"],
                check=False,
            )
            return returncode == 0
        return False

    def wait_for_healthy(self, timeout: int = 300, *, show_progress: bool = True) -> bool:
        """Wait for the container health probe to report healthy."""
        start_time = time.time()

        if show_progress:
            with self.console.status("[bold yellow]Waiting for database to be healthy...") as status:
                while time.time() - start_time < timeout:
                    if self.is_healthy():
                        return True
                    elapsed = int(time.time() - start_time)
                    status.update(f"[bold yellow]Waiting for database... ({elapsed}s / {timeout}s)")
                    time.sleep(5)
        else:
            while time.time() - start_time < timeout:
                if self.is_healthy():
                    return True
                time.sleep(5)

        return False

    def get_connection_info(self) -> dict[str, Any]:
        """Return connection details for the active container flavor."""
        if self.config.flavor == ContainerFlavor.ADB_FREE:
            return {
                "host": "localhost",
                "port": self.config.tls_host_port,
                "https_port": self.config.https_port,
                "service_name": self.config.service_name,
                "user": self.config.app_user,
                "password": self.config.app_user_password,
                "wallet_dir": str(self.config.wallet_dir),
                "dsn": self.config.service_name,
            }
        return {
            "host": "localhost",
            "port": self.config.host_port,
            "service_name": self.config.service_name,
            "user": self.config.app_user,
            "password": self.config.app_user_password,
            "dsn": f"localhost:{self.config.host_port}/{self.config.service_name}",
        }

    def _guard_port_collision(self) -> None:
        """Fail fast with an actionable wipe command if ``oracle-free-db`` already binds port 1521."""
        if (
            self.config.flavor == ContainerFlavor.ADB_FREE
            and self.config.container_name != LEGACY_FREE_CONTAINER_NAME
            and self.config.host_port == DEFAULT_HOST_PORT
            and self.runtime.container_running(LEGACY_FREE_CONTAINER_NAME)
        ):
            raise ContainerStartError(
                f"Legacy '{LEGACY_FREE_CONTAINER_NAME}' container is already running on host port 1521. "
                "Stop or wipe it before starting 'cymbal-adb-free': "
                "ORACLE_CONTAINER_FLAVOR=free uv run python manage.py infra wipe --volumes --force --yes"
            )

    def _finalize_ready_container(self, *, timeout: int) -> None:
        """Run flavor-specific readiness checks, wallet export, and user/workspace provisioning."""
        if self.config.flavor == ContainerFlavor.ADB_FREE:
            self.console.print("[cyan]Waiting for ADB-Free wallet, mTLS listener, and ORDS (:8443)...[/cyan]")
            bootstrap = AdbBootstrap(self.runtime, self.to_adb_bootstrap_config(), console=self.console)
            try:
                bootstrap.bootstrap(timeout=timeout)
            except AdbBootstrapError as exc:
                logs_hint = f"{self.runtime.get_runtime_command()} logs {self.config.container_name}"
                raise ContainerStartError(f"{exc} Check logs with: {logs_hint}") from exc
            return

        self.console.print("[cyan]Waiting for database to become healthy...[/cyan]")
        if not self.wait_for_healthy(timeout=timeout):
            logs_hint = f"{self.runtime.get_runtime_command()} logs {self.config.container_name}"
            raise ContainerStartError(f"Container started but health check timed out. Check logs with: {logs_hint}")
        self._align_app_user_credentials()

    def _build_adb_free_run_command(self) -> list[str]:
        """Build the ``docker run`` argument vector for ``adb-free:latest-26ai``."""
        cmd = [
            "run",
            "-d",
            "--name",
            self.config.container_name,
            "--hostname",
            self.config.hostname,
            "-p",
            f"{self.config.host_port}:1522",
        ]
        if self.config.tls_host_port != self.config.host_port:
            cmd.extend(["-p", f"{self.config.tls_host_port}:1522"])
        cmd.extend([
            "-p",
            f"{self.config.https_port}:8443",
            "-e",
            f"WORKLOAD_TYPE={self.config.workload_type}",
            "-e",
            f"ENABLE_ARCHIVE_LOG={'TRUE' if self.config.enable_archive_log else 'FALSE'}",
            "-e",
            f"WALLET_PASSWORD={self.config.wallet_password}",
            "-e",
            f"ADMIN_PASSWORD={self.config.oracle_password}",
            "-v",
            f"{self.config.data_volume_name}:/u01/data",
            "--cap-add",
            "SYS_ADMIN",
            "--device",
            "/dev/fuse",
            "--restart",
            self.config.restart_policy,
            "--log-opt",
            f"max-size={self.config.log_max_size}",
            "--log-opt",
            f"max-file={self.config.log_max_file}",
        ])
        if sys.platform.startswith("linux") and self.runtime.get_runtime_type() == RuntimeType.DOCKER:
            cmd.append("--add-host=host.docker.internal:host-gateway")
        cmd.append(self.config.image)
        return cmd

    def _build_free_run_command(self) -> list[str]:
        """Build the ``docker run`` argument vector for ``gvenzl/oracle-free``."""
        cmd = [
            "run",
            "-d",
            "--name",
            self.config.container_name,
            "--hostname",
            self.config.hostname,
            "-p",
            f"{self.config.host_port}:{self.config.container_port}",
            "-e",
            f"ORACLE_SYSTEM_PASSWORD={self.config.oracle_system_password}",
            "-e",
            f"ORACLE_PASSWORD={self.config.oracle_password}",
            "-e",
            f"APP_USER_PASSWORD={self.config.app_user_password}",
            "-e",
            f"APP_USER={self.config.app_user}",
            "-v",
            f"{self.config.data_volume_name}:/opt/oracle/oradata",
            "--restart",
            self.config.restart_policy,
            "--log-opt",
            f"max-size={self.config.log_max_size}",
            "--log-opt",
            f"max-file={self.config.log_max_file}",
            "--health-cmd",
            "healthcheck.sh",
            "--health-interval",
            f"{self.config.health_interval}s",
            "--health-timeout",
            f"{self.config.health_timeout}s",
            "--health-retries",
            str(self.config.health_retries),
        ]

        project_root = Path(__file__).parent.parent.parent
        hook_mounts = (
            (project_root / "tools" / "oracle" / "on_init", "/container-entrypoint-initdb.d"),
            (project_root / "tools" / "oracle" / "on_startup", "/container-entrypoint-startdb.d"),
        )
        for hook_dir, mount_target in hook_mounts:
            if not hook_dir.exists():
                continue
            for script_file in sorted(hook_dir.glob("*.sql")) + sorted(hook_dir.glob("*.sh")):
                if script_file.is_file() and script_file.name != ".gitkeep":
                    cmd.extend(["-v", f"{script_file.absolute()}:{mount_target}/{script_file.name}:z"])

        cmd.append(self.config.image)
        return cmd

    def _align_app_user_credentials(self) -> None:
        """Repair the local APP user password and grants on reused ``gvenzl/oracle-free`` volumes."""
        app_user = self._oracle_identifier(self.config.app_user)
        password = self._oracle_quoted_password(self.config.app_user_password)
        pdb_name = self._oracle_identifier(self.config.service_name)
        sql = (
            f"ALTER SESSION SET CONTAINER={pdb_name};\n"  # ruff: ignore[hardcoded-sql-expression]
            "DECLARE\n"
            "  v_user_count NUMBER;\n"
            "BEGIN\n"
            f"  SELECT COUNT(*) INTO v_user_count FROM dba_users WHERE username = '{app_user}';\n"
            "  IF v_user_count = 0 THEN\n"
            f"    EXECUTE IMMEDIATE 'CREATE USER {app_user} IDENTIFIED BY {password}';\n"
            "  END IF;\n"
            "END;\n"
            "/\n"
            f"ALTER USER {app_user} IDENTIFIED BY {password} ACCOUNT UNLOCK;\n"
            f"GRANT CONNECT, RESOURCE TO {app_user};\n"
            f"GRANT SELECT ON v_$transaction TO {app_user};\n"
            f"GRANT CREATE MINING MODEL TO {app_user};\n"
            f"GRANT UNLIMITED TABLESPACE TO {app_user};\n"
            f"GRANT CREATE SEQUENCE TO {app_user};\n"
            f"GRANT CREATE TABLE TO {app_user};\n"
            f"GRANT CREATE VIEW TO {app_user};\n"
            f"GRANT CREATE PROCEDURE TO {app_user};\n"
            f"GRANT DB_DEVELOPER_ROLE TO {app_user};\n"
        )
        command = f"sqlplus -S -L / as sysdba <<'SQL'\n{sql}\nexit\nSQL\n"
        try:
            _returncode, stdout, stderr = self.runtime.run_command([
                "exec",
                self.config.container_name,
                "bash",
                "-c",
                command,
            ])
        except Exception as exc:
            raise ContainerStartError(f"Failed to align APP user credentials: {exc}") from exc
        output = f"{stdout}\n{stderr}"
        if "ORA-" in output or "PLS-" in output or "SP2-" in output:
            raise ContainerStartError(f"Failed to align APP user credentials: {output.strip()}")

    @staticmethod
    def _oracle_identifier(value: str) -> str:
        """Return an uppercase Oracle identifier for trusted local config values."""
        if not ORACLE_IDENTIFIER_RE.fullmatch(value):
            raise ContainerStartError(f"Invalid Oracle identifier: {value!r}")
        return value.upper()

    @staticmethod
    def _oracle_quoted_password(value: str) -> str:
        """Return a double-quoted Oracle password literal."""
        return '"' + value.replace('"', '""') + '"'

    def _create_volume(self, volume_name: str) -> None:
        """Create the named data volume if it does not already exist."""
        if not self.runtime.volume_exists(volume_name):
            self.console.print(f"Creating volume [cyan]{volume_name}[/cyan]...")
            self.runtime.run_command(["volume", "create", volume_name])

    def _pull_image(self) -> None:
        """Pull the configured Oracle container image."""
        self.console.print(f"Pulling image [cyan]{self.config.image}[/cyan]...")
        with self.console.status("[bold yellow]Pulling image..."):
            self.runtime.run_command(["pull", self.config.image])
