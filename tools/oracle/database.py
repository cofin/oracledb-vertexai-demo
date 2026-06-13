# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle database container lifecycle management.

This module manages Oracle Database Free container deployment and operations.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from tools.oracle.container import ContainerNotFoundError, ContainerRuntime


@dataclass
class DatabaseConfig:
    """Configuration for Oracle database container."""

    container_name: str = "oracle-free-db"
    image: str = "container-registry.oracle.com/database/adb-free:latest-26ai"
    hostname: str = "db"

    host_port: int = 1521
    container_port: int = 1522

    host_mtls_port: int = 1522
    container_mtls_port: int = 1522

    host_https_port: int = 8443
    container_https_port: int = 8443

    host_mongo_port: int = 27017
    container_mongo_port: int = 27017

    admin_username: str = "admin"
    admin_password: str = "SuperSecret1"
    wallet_password: str = "SuperSecret1"
    wallet_location: str = ".envs/tns"

    data_location: str = "/var/tmp/oracle-data"
    audit_location: str = "/var/tmp/oracle-audit"
    oradata_location: str = "/var/tmp/oracle-oradata"

    log_max_size: str = "10m"
    log_max_file: str = "3"

    health_interval: int = 10
    health_timeout: int = 5
    health_retries: int = 10

    restart_policy: str = "unless-stopped"

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """Create configuration from environment variables."""
        oracle_system_pw = os.getenv("ORACLE_SYSTEM_PASSWORD", "SuperSecret1")
        wallet_pw = os.getenv("WALLET_PASSWORD", "SuperSecret1")
        wallet_loc = os.getenv("TNS_ADMIN", os.getenv("WALLET_LOCATION", ".envs/tns"))
        host_port = os.getenv("ORACLE26AI_PORT", os.getenv("ORACLE23AI_PORT", "1521"))

        return cls(
            host_port=int(host_port),
            admin_password=oracle_system_pw,
            wallet_password=wallet_pw,
            wallet_location=wallet_loc,
        )


class OracleDatabase:
    """Manage Oracle Database Free container lifecycle."""

    def __init__(
        self,
        runtime: ContainerRuntime,
        config: DatabaseConfig | None = None,
        console: Console | None = None,
    ) -> None:
        """Initialize Oracle database manager.

        Args:
            runtime: Container runtime instance
            config: Database configuration (uses defaults if None)
            console: Rich console for output (creates new if None)
        """
        self.runtime = runtime
        self.config = config or DatabaseConfig()
        self.console = console or Console()

    def start(
        self,
        *,
        pull: bool = False,
        recreate: bool = False,
    ) -> None:
        """Start Oracle database container.

        Args:
            pull: Pull latest image before starting
            recreate: Remove and recreate container if exists

        Process:
            1. Check if container already exists
            2. Pull image if requested
            3. Create data volume if needed
            4. Prepare init script mount
            5. Build container run command
            6. Start container
            7. Wait for health check
            8. Display connection info

        Raises:
            ContainerAlreadyRunningError: If container is already running
            ContainerStartError: If container fails to start
        """
        self.console.rule("[bold blue]Starting Oracle Database Container")

        # Check if already running
        if self.runtime.container_running(self.config.container_name):
            if not recreate:
                raise ContainerAlreadyRunningError(
                    f"Container '{self.config.container_name}' is already running. "
                    "Use --recreate to remove and recreate it."
                )
            self.console.print("[yellow]Removing existing container...[/yellow]")
            self.remove(force=True)

        # Check if exists but stopped
        if self.runtime.container_exists(self.config.container_name):
            if recreate:
                self.console.print("[yellow]Removing existing container...[/yellow]")
                self.remove()
            else:
                self.console.print("[cyan]Starting existing container...[/cyan]")
                self.runtime.run_command(["start", self.config.container_name])
                self.console.print("[green]✓[/green] Container started")
                return

        # Pull image if requested
        if pull:
            self._pull_image()

        run_cmd = self._build_run_command()

        # Start container
        self.console.print("[cyan]Creating and starting container...[/cyan]")
        try:
            _, stdout, _stderr = self.runtime.run_command(run_cmd)
            container_id = stdout.strip()[:12]
            self.console.print(f"[green]✓[/green] Container created: [dim]{container_id}[/dim]")
        except Exception as e:
            raise ContainerStartError(f"Failed to start container: {e}") from e

        self.console.print("[cyan]Waiting for database to become healthy...[/cyan]")
        if self.wait_for_healthy(timeout=300):
            self.console.print("[green]✓[/green] Database is healthy and ready!")
            self._patch_host_sqlnet_ora()
            self.initialize_db_users()
            info = self.get_connection_info()
            self.console.print("\n[bold]Connection Info:[/bold]")
            self.console.print(f"  Host: {info['host']}")
            self.console.print(f"  Port: {info['port']}")
            self.console.print(f"  Service: {info['service_name']}")
            self.console.print(f"  User: {info['user']}")
            self.console.print(f"  DSN: {info['dsn']}")
        else:
            self.console.print("[yellow]⚠[/yellow] Container started but health check timed out")
            self.console.print(
                f"  Check logs with: {self.runtime.get_runtime_command()} logs {self.config.container_name}"
            )

    def stop(self, *, timeout: int = 30) -> None:
        """Stop Oracle database container.

        Args:
            timeout: Seconds to wait before forcing stop

        Raises:
            ContainerNotFoundError: If container doesn't exist
        """
        if not self.runtime.container_exists(self.config.container_name):
            raise ContainerNotFoundError(f"Container '{self.config.container_name}' does not exist")

        self.console.print("[cyan]Stopping container...[/cyan]")
        self.runtime.run_command(["stop", "-t", str(timeout), self.config.container_name])
        self.console.print("[green]✓[/green] Container stopped")

    def restart(self, *, timeout: int = 30) -> None:
        """Restart Oracle database container.

        Args:
            timeout: Seconds to wait for stop before forcing

        Raises:
            ContainerNotFoundError: If container doesn't exist
        """
        if not self.runtime.container_exists(self.config.container_name):
            raise ContainerNotFoundError(f"Container '{self.config.container_name}' does not exist")

        self.console.print("[cyan]Restarting container...[/cyan]")
        self.runtime.run_command(["restart", "-t", str(timeout), self.config.container_name])
        self.console.print("[green]✓[/green] Container restarted")

    def remove(
        self,
        *,
        volumes: bool = False,
        force: bool = False,
    ) -> None:
        """Remove Oracle database container.

        Args:
            volumes: Also remove associated volumes
            force: Force removal even if running

        Raises:
            ContainerNotFoundError: If container doesn't exist
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

        if volumes:
            for loc in (self.config.data_location, self.config.audit_location, self.config.oradata_location):
                path = Path(loc).resolve()
                if path.exists():
                    self.console.print(f"[cyan]Removing directory {loc}...[/cyan]")
                    import shutil
                    shutil.rmtree(path, ignore_errors=True)
                    self.console.print("[green]✓[/green] Directory removed")

    def logs(
        self,
        *,
        follow: bool = False,
        tail: int | None = None,
        since: str | None = None,
    ) -> None:
        """Stream container logs.

        Args:
            follow: Continue streaming new logs
            tail: Number of lines from end to show
            since: Show logs since timestamp/duration

        Raises:
            ContainerNotFoundError: If container doesn't exist
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

        # Stream logs directly (don't capture)
        self.runtime.run_command(logs_cmd, capture_output=False)

    def status(self) -> ContainerStatus:
        """Get detailed container status.

        Returns:
            ContainerStatus: Current status information

        Raises:
            ContainerNotFoundError: If container doesn't exist
        """
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

        # Get status from runtime
        status_dict = self.runtime.get_container_status(self.config.container_name)
        running = self.runtime.container_running(self.config.container_name)
        healthy = self.is_healthy() if running else None

        return ContainerStatus(
            exists=True,
            running=running,
            healthy=healthy,
            status=status_dict.get("status", "unknown"),
            container_id=status_dict.get("id"),
            uptime=None,  # Could parse from created_at if needed
            ports={"1521": str(self.config.host_port)},
            image=status_dict.get("image", self.config.image),
            created_at=status_dict.get("created"),
        )

    def is_running(self) -> bool:
        """Quick check if container is running.

        Returns:
            bool: True if container exists and is running
        """
        return self.runtime.container_running(self.config.container_name)

    def is_healthy(self) -> bool:
        """Check if container health check is passing.

        Returns:
            bool: True if container is healthy

        Note:
            Returns False if container doesn't exist or isn't running
        """
        if not self.is_running():
            return False

        try:
            _, stdout, _ = self.runtime.run_command(
                ["inspect", "--format", "{{.State.Health.Status}}", self.config.container_name],
                check=False,
            )
            health_status = stdout.strip()
            return health_status == "healthy"
        except Exception:  # noqa: BLE001
            return False

    def wait_for_healthy(
        self,
        timeout: int = 300,
        *,
        show_progress: bool = True,
    ) -> bool:
        """Wait for container to become healthy.

        Args:
            timeout: Maximum seconds to wait
            show_progress: Show progress indicator

        Returns:
            bool: True if became healthy, False if timeout

        Used after starting container to ensure it's ready.
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

    def initialize_db_users(self) -> None:
        """Initialize the development users/schemas post container start."""
        self.console.print("[cyan]Initializing app user and privileges...[/cyan]")
        absolute_wallet_path = Path(self.config.wallet_location).resolve()
        original_tns_admin = os.environ.get("TNS_ADMIN")
        os.environ["TNS_ADMIN"] = str(absolute_wallet_path)

        import oracledb

        self.console.print(f"[dim]Wallet Location: {absolute_wallet_path}[/dim]")
        self.console.print(f"[dim]TNS_ADMIN env: {os.environ.get('TNS_ADMIN')}[/dim]")
        try:
            self.console.print(f"[dim]Files in wallet: {[f.name for f in absolute_wallet_path.glob('*')]}[/dim]")
        except Exception as err:
            self.console.print(f"[dim]Error listing wallet files: {err}[/dim]")

        masked_pwd = self.config.admin_password[:3] + "..." + self.config.admin_password[-1:] if self.config.admin_password else "None"
        self.console.print(f"[dim]Connection parameters: user=ADMIN, dsn=myatp_low, pwd={masked_pwd}, pwd_len={len(self.config.admin_password)}[/dim]")

        conn_params = {
            "user": "ADMIN",
            "password": self.config.admin_password,
            "dsn": "myatp_low",
            "wallet_location": str(absolute_wallet_path),
            "wallet_password": self.config.wallet_password,
        }
        sql = """
        DECLARE
            user_exists NUMBER;
        BEGIN
            SELECT COUNT(*) INTO user_exists FROM dba_users WHERE username = 'APP';
            IF user_exists = 0 THEN
                EXECUTE IMMEDIATE 'CREATE USER app IDENTIFIED BY "SuperSecret1"';
                EXECUTE IMMEDIATE 'GRANT CONNECT, RESOURCE, DB_DEVELOPER_ROLE TO app';
                EXECUTE IMMEDIATE 'GRANT UNLIMITED TABLESPACE TO app';
            END IF;
        END;
        """

        import time

        max_retries = 24
        retry_interval = 5
        conn = None

        self.console.print("[cyan]Connecting to database and creating app schema...[/cyan]")
        for attempt in range(1, max_retries + 1):
            try:
                conn = oracledb.connect(**conn_params)
                self.console.print(f"[green]✓[/green] Connected successfully on attempt {attempt}")
                break
            except Exception as e:
                self.console.print(f"[dim]Connection attempt {attempt} failed: {e}. Retrying in {retry_interval}s...[/dim]")
                time.sleep(retry_interval)
        else:
            self.console.print("[red]✗ Max connection retries reached. Database initialization failed.[/red]")
            raise DatabaseNotReadyError("Database failed to become ready for connections")

        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
            conn.commit()
            conn.close()
        except Exception as e:
            self.console.print(f"[red]✗ Failed to execute app user initialization: {e}[/red]")
            raise
        else:
            self.console.print("[green]✓[/green] App user schema initialized successfully.")
        finally:
            if original_tns_admin is not None:
                os.environ["TNS_ADMIN"] = original_tns_admin
            else:
                os.environ.pop("TNS_ADMIN", None)

    def _patch_host_sqlnet_ora(self) -> None:
        """Patch TNS_ADMIN placeholder in host sqlnet.ora with absolute path."""
        wallet_dir = Path(self.config.wallet_location).resolve()
        
        # Grant write permission to the wallet files using a temporary container
        try:
            self.runtime.run_command([
                "run",
                "--rm",
                "-v",
                f"{wallet_dir}:/mnt/tns",
                "busybox",
                "chmod",
                "-R",
                "777",
                "/mnt/tns",
            ])
        except Exception as e:
            self.console.print(f"[yellow]⚠ Warning: Failed to fix wallet file permissions: {e}[/yellow]")

        sqlnet_path = wallet_dir / "sqlnet.ora"
        if sqlnet_path.exists():
            self.console.print("[cyan]Patching host sqlnet.ora wallet directory...[/cyan]")
            content = sqlnet_path.read_text()
            if "$TNS_ADMIN" in content:
                content = content.replace("$TNS_ADMIN", str(wallet_dir))
                sqlnet_path.write_text(content)
                self.console.print("[green]✓[/green] Patched sqlnet.ora")

    def get_connection_info(self) -> dict[str, Any]:
        """Get connection information for the database."""
        return {
            "host": "localhost",
            "port": self.config.host_port,
            "service_name": "myatp_low",
            "user": "app",
            "password": "SuperSecret1",
            "dsn": f"localhost:{self.config.host_port}/myatp_low",
        }

    def exec_sql(self, sql: str, *, user: str = "app") -> str:
        """Execute SQL command in running container.

        Args:
            sql: SQL command to execute
            user: Database user to connect as

        Returns:
            str: Command output

        Raises:
            ContainerNotFoundError: If container doesn't exist
            DatabaseNotReadyError: If database isn't healthy
        """
        if not self.is_running():
            raise ContainerNotFoundError(f"Container '{self.config.container_name}' is not running")

        if not self.is_healthy():
            raise DatabaseNotReadyError("Database is not healthy yet")

        _, stdout, _ = self.runtime.run_command([
            "exec",
            self.config.container_name,
            "sqlplus",
            "-S",
            f"{user}/SuperSecret1@myatp_low",
            sql,
        ])

        return stdout

    def _build_run_command(self) -> list[str]:
        """Build the container run command.

        Returns:
            list[str]: Command arguments for container run
        """
        absolute_wallet_path = Path(self.config.wallet_location).resolve()
        absolute_wallet_path.mkdir(parents=True, exist_ok=True)
        absolute_wallet_path.chmod(0o777)

        absolute_data_path = Path(self.config.data_location).resolve()
        absolute_data_path.mkdir(parents=True, exist_ok=True)
        absolute_data_path.chmod(0o777)

        absolute_audit_path = Path(self.config.audit_location).resolve()
        absolute_audit_path.mkdir(parents=True, exist_ok=True)
        absolute_audit_path.chmod(0o777)

        absolute_oradata_path = Path(self.config.oradata_location).resolve()
        absolute_oradata_path.mkdir(parents=True, exist_ok=True)
        absolute_oradata_path.chmod(0o777)

        cmd = [
            "run",
            "-d",
            "--name",
            self.config.container_name,
            "--shm-size",
            "2g",
            "--hostname",
            self.config.hostname,
            "-p",
            f"{self.config.host_port}:{self.config.container_port}",
            "-p",
            f"{self.config.host_mtls_port}:{self.config.container_mtls_port}",
            "-p",
            f"{self.config.host_https_port}:{self.config.container_https_port}",
            "-p",
            f"{self.config.host_mongo_port}:{self.config.container_mongo_port}",
            "-e",
            f"ADMIN_PASSWORD={self.config.admin_password}",
            "-e",
            f"WALLET_PASSWORD={self.config.wallet_password}",
            "-e",
            "ENABLE_ARCHIVE_LOG=FALSE",
            "-v",
            f"{absolute_data_path}:/u01/data:z",
            "-v",
            f"{absolute_audit_path}:/u01/app/oracle/audit:z",
            "-v",
            f"{absolute_oradata_path}:/u01/app/oracle/oradata:z",
            "-v",
            f"{absolute_wallet_path}:/u01/app/oracle/wallets/tls_wallet:z",
            "--privileged",
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
            "--health-cmd",
            "healthcheck.sh",
            "--health-interval",
            f"{self.config.health_interval}s",
            "--health-timeout",
            f"{self.config.health_timeout}s",
            "--health-retries",
            str(self.config.health_retries),
        ]

        cmd.append(self.config.image)
        return cmd



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
    ports: dict[str, str]  # Container port -> host port mapping
    image: str
    created_at: str | None


class DatabaseError(Exception):
    """Base exception for database operations."""


class ContainerAlreadyRunningError(DatabaseError):
    """Raised when trying to start an already running container."""


class ContainerStartError(DatabaseError):
    """Raised when container fails to start."""


class DatabaseNotReadyError(DatabaseError):
    """Raised when database isn't ready for operations."""
