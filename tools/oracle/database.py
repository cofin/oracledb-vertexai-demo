# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle database container lifecycle management.

This module manages the local Oracle Database Free (gvenzl/oracle-free)
container used for development and the demo. The image bundles the
``/container-entrypoint-initdb.d`` (run once on first creation) and
``/container-entrypoint-startdb.d`` (run on every start) hook directories and
executes those scripts as SYSDBA, so vector-memory configuration and app-user
grants live in ``tools/oracle/on_init`` / ``tools/oracle/on_startup`` rather
than in Python.

The image is overridable via ``ORACLE_IMAGE`` for advanced setups, but the run
command, health check, and hook mounts are shaped for gvenzl/oracle-free.
Connecting the app to a remote Oracle Autonomous Database (OCI or any cloud)
is a separate, wallet-based concern handled by ``tools/oracle/connection.py``
and the app settings — it does not use this container lifecycle.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from tools.oracle.container import ContainerNotFoundError, ContainerRuntime

DEFAULT_IMAGE = "gvenzl/oracle-free:latest"
PDB_SERVICE_NAME = "freepdb1"
ORACLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]*$")


@dataclass
class DatabaseConfig:
    """Configuration for the local Oracle database container."""

    # Container settings
    container_name: str = "oracle-free-db"
    image: str = DEFAULT_IMAGE
    hostname: str = "db"

    # Port mapping
    host_port: int = 1521
    container_port: int = 1521

    # Environment variables (gvenzl/oracle-free)
    oracle_system_password: str = "super-secret"  # noqa: S105
    oracle_password: str = "super-secret"  # noqa: S105
    app_user: str = "app"
    app_user_password: str = "SuperSecret1"  # noqa: S105

    # Volumes
    data_volume_name: str = "oracle-db-data"

    # Logging
    log_max_size: str = "10m"
    log_max_file: str = "3"

    # Health check
    health_interval: int = 10  # seconds
    health_timeout: int = 5  # seconds
    health_retries: int = 10

    # Restart policy
    restart_policy: str = "unless-stopped"

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """Create configuration from environment variables."""
        host_port = os.getenv("DATABASE_PORT", os.getenv("ORACLE26AI_PORT", os.getenv("ORACLE23AI_PORT", "1521")))
        oracle_system_pw = os.getenv("ORACLE_SYSTEM_PASSWORD", os.getenv("ORACLE_PASSWORD", "super-secret"))
        return cls(
            image=os.getenv("ORACLE_IMAGE", DEFAULT_IMAGE),
            host_port=int(host_port),
            oracle_system_password=oracle_system_pw,
            oracle_password=os.getenv("ORACLE_PASSWORD", oracle_system_pw),
            app_user=os.getenv("DATABASE_USER", "app"),
            app_user_password=os.getenv("DATABASE_PASSWORD", "SuperSecret1"),
        )


class OracleDatabase:
    """Manage the local Oracle Database Free container lifecycle."""

    def __init__(
        self, runtime: ContainerRuntime, config: DatabaseConfig | None = None, console: Console | None = None
    ) -> None:
        self.runtime = runtime
        self.config = config or DatabaseConfig.from_env()
        self.console = console or Console()

    def start(self, *, pull: bool = False, recreate: bool = False) -> None:
        """Start the Oracle database container.

        Args:
            pull: Pull latest image before starting
            recreate: Remove and recreate container if it exists

        Raises:
            ContainerStartError: If the container fails to start or stay healthy
        """
        self.console.rule("[bold blue]Starting Oracle Database Container")

        # Already running — reuse it (idempotent); recreate only when asked
        if self.runtime.container_running(self.config.container_name):
            if not recreate:
                self.console.print("[green]✓[/green] Container already running — reusing it")
                if self.is_healthy():
                    self._align_app_user_credentials()
                return
            self.console.print("[yellow]Removing existing container...[/yellow]")
            self.remove(force=True)

        # Exists but stopped
        if self.runtime.container_exists(self.config.container_name):
            if recreate:
                self.console.print("[yellow]Removing existing container...[/yellow]")
                self.remove()
            else:
                self.console.print("[cyan]Starting existing container...[/cyan]")
                self.runtime.run_command(["start", self.config.container_name])
                # on_startup hooks (vector-memory verification) re-run automatically.
                self.console.print("[green]✓[/green] Container started")
                return

        # Fresh create
        if pull:
            self._pull_image()
        self._create_volume(self.config.data_volume_name)

        run_cmd = self._build_run_command()
        self.console.print("[cyan]Creating and starting container...[/cyan]")
        try:
            _, stdout, _stderr = self.runtime.run_command(run_cmd)
            container_id = stdout.strip()[:12]
            self.console.print(f"[green]✓[/green] Container created: [dim]{container_id}[/dim]")
        except Exception as e:
            raise ContainerStartError(f"Failed to start container: {e}") from e

        self.console.print("[cyan]Waiting for database to become healthy...[/cyan]")
        if not self.wait_for_healthy(timeout=300):
            logs_hint = f"{self.runtime.get_runtime_command()} logs {self.config.container_name}"
            raise ContainerStartError(f"Container started but health check timed out. Check logs with: {logs_hint}")

        self._align_app_user_credentials()
        self.console.print("[green]✓[/green] Database is healthy and ready!")
        info = self.get_connection_info()
        self.console.print("\n[bold]Connection Info:[/bold]")
        self.console.print(f"  Host: {info['host']}")
        self.console.print(f"  Port: {info['port']}")
        self.console.print(f"  Service: {info['service_name']}")
        self.console.print(f"  User: {info['user']}")
        self.console.print(f"  DSN: {info['dsn']}")

    def stop(self, *, timeout: int = 30) -> None:
        """Stop the Oracle database container.

        Raises:
            ContainerNotFoundError: If the container doesn't exist
        """
        if not self.runtime.container_exists(self.config.container_name):
            raise ContainerNotFoundError(f"Container '{self.config.container_name}' does not exist")

        self.console.print("[cyan]Stopping container...[/cyan]")
        self.runtime.run_command(["stop", "-t", str(timeout), self.config.container_name])
        self.console.print("[green]✓[/green] Container stopped")

    def restart(self, *, timeout: int = 30) -> None:
        """Restart the Oracle database container.

        Raises:
            ContainerNotFoundError: If the container doesn't exist
        """
        if not self.runtime.container_exists(self.config.container_name):
            raise ContainerNotFoundError(f"Container '{self.config.container_name}' does not exist")

        self.console.print("[cyan]Restarting container...[/cyan]")
        self.runtime.run_command(["restart", "-t", str(timeout), self.config.container_name])
        self.console.print("[green]✓[/green] Container restarted")

    def remove(self, *, volumes: bool = False, force: bool = False) -> None:
        """Remove the Oracle database container.

        Args:
            volumes: Also remove the associated data volume
            force: Force removal even if running

        Raises:
            ContainerNotFoundError: If the container doesn't exist
        """
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
        """Stream container logs.

        Raises:
            ContainerNotFoundError: If the container doesn't exist
        """
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
        """Get detailed container status."""
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

        return ContainerStatus(
            exists=True,
            running=running,
            healthy=healthy,
            status=status_dict.get("status", "unknown"),
            container_id=status_dict.get("id"),
            uptime=None,
            ports={str(self.config.container_port): str(self.config.host_port)},
            image=status_dict.get("image", self.config.image),
            created_at=status_dict.get("created"),
        )

    def is_running(self) -> bool:
        """Quick check if the container is running."""
        return self.runtime.container_running(self.config.container_name)

    def is_healthy(self) -> bool:
        """Check if the container health check is passing."""
        if not self.is_running():
            return False

        try:
            _, stdout, _ = self.runtime.run_command(
                ["inspect", "--format", "{{.State.Health.Status}}", self.config.container_name], check=False
            )
            return stdout.strip() == "healthy"
        except Exception:  # noqa: BLE001
            return False

    def wait_for_healthy(self, timeout: int = 300, *, show_progress: bool = True) -> bool:
        """Wait for the container to become healthy.

        Returns:
            bool: True if it became healthy, False on timeout
        """
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
        """Get connection information for the local database."""
        return {
            "host": "localhost",
            "port": self.config.host_port,
            "service_name": PDB_SERVICE_NAME,
            "user": self.config.app_user,
            "password": self.config.app_user_password,
            "dsn": f"localhost:{self.config.host_port}/{PDB_SERVICE_NAME}",
        }

    def exec_sql(self, sql: str, *, user: str | None = None) -> str:
        """Execute a SQL statement inside the running container as the app user.

        Raises:
            ContainerNotFoundError: If the container isn't running
            DatabaseNotReadyError: If the database isn't healthy yet
        """
        if not self.is_running():
            raise ContainerNotFoundError(f"Container '{self.config.container_name}' is not running")
        if not self.is_healthy():
            raise DatabaseNotReadyError("Database is not healthy yet")

        connect_user = user or self.config.app_user
        _, stdout, _ = self.runtime.run_command([
            "exec",
            self.config.container_name,
            "sqlplus",
            "-S",
            f"{connect_user}/{self.config.app_user_password}@localhost:{self.config.container_port}/{PDB_SERVICE_NAME}",
            sql,
        ])
        return stdout

    def _align_app_user_credentials(self) -> None:
        """Repair the local APP user password and grants on reused volumes."""
        app_user = self._oracle_identifier(self.config.app_user)
        password = self._oracle_quoted_password(self.config.app_user_password)
        sql = (
            f"ALTER SESSION SET CONTAINER={PDB_SERVICE_NAME.upper()};\n"  # noqa: S608 - local SYSDBA DDL; identifier is validated.
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
        except Exception as e:
            raise ContainerStartError(f"Failed to align APP user credentials: {e}") from e
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

    def _build_run_command(self) -> list[str]:
        """Build the container run command for gvenzl/oracle-free."""
        cmd = [
            "run",
            "-d",
            "--name",
            self.config.container_name,
            "--hostname",
            self.config.hostname,
            "-p",
            f"{self.config.host_port}:{self.config.container_port}",
            # Environment variables
            "-e",
            f"ORACLE_SYSTEM_PASSWORD={self.config.oracle_system_password}",
            "-e",
            f"ORACLE_PASSWORD={self.config.oracle_password}",
            "-e",
            f"APP_USER_PASSWORD={self.config.app_user_password}",
            "-e",
            f"APP_USER={self.config.app_user}",
            # Data volume (persistent across restarts)
            "-v",
            f"{self.config.data_volume_name}:/opt/oracle/oradata",
            # Restart policy
            "--restart",
            self.config.restart_policy,
            # Logging
            "--log-opt",
            f"max-size={self.config.log_max_size}",
            "--log-opt",
            f"max-file={self.config.log_max_file}",
            # Health check
            "--health-cmd",
            "healthcheck.sh",
            "--health-interval",
            f"{self.config.health_interval}s",
            "--health-timeout",
            f"{self.config.health_timeout}s",
            "--health-retries",
            str(self.config.health_retries),
        ]

        # Mount on_init scripts (run once during first DB creation) and on_startup
        # scripts (run on every start) into the gvenzl hook directories. These run
        # as SYSDBA and own vector-memory configuration + app-user grants.
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
                    # :z relabels for SELinux (works with both Docker and Podman)
                    cmd.extend(["-v", f"{script_file.absolute()}:{mount_target}/{script_file.name}:z"])

        cmd.append(self.config.image)
        return cmd

    def _create_volume(self, volume_name: str) -> None:
        """Create the named data volume if it doesn't already exist."""
        if not self.runtime.volume_exists(volume_name):
            self.console.print(f"Creating volume [cyan]{volume_name}[/cyan]...")
            self.runtime.run_command(["volume", "create", volume_name])

    def _pull_image(self) -> None:
        """Pull the Oracle database image."""
        self.console.print(f"Pulling image [cyan]{self.config.image}[/cyan]...")
        with self.console.status("[bold yellow]Pulling image..."):
            self.runtime.run_command(["pull", self.config.image])


@dataclass
class ContainerStatus:
    """Container status information."""

    exists: bool
    running: bool
    healthy: bool | None
    status: str  # e.g., "running", "exited", "created"
    container_id: str | None
    uptime: str | None
    ports: dict[str, str]  # container port -> host port mapping
    image: str
    created_at: str | None


class DatabaseError(Exception):
    """Base exception for database operations."""


class ContainerStartError(DatabaseError):
    """Raised when the container fails to start."""


class DatabaseNotReadyError(DatabaseError):
    """Raised when the database isn't ready for operations."""
