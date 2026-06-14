# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ORDS sidecar runtime for the gvenzl APEX stack.

``gvenzl/oracle-free`` ships no ORDS, so APEX has no HTTP front end until one is
added. ORDS runs as a sidecar container launched by this CLI (consistent with
the "CLI owns infra" rule). It reaches the database over the host gateway
(``host.docker.internal``) so the database lifecycle class never needs a shared
network or a recreate, and serves the APEX static images at ``/i/`` from the
host media staged in Chapter 1.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from tools.oracle.apex_media import ApexMedia
    from tools.oracle.container import ContainerRuntime

DEFAULT_ORDS_IMAGE = "container-registry.oracle.com/database/ords:latest"


@dataclass
class OrdsConfig:
    """Configuration for the ORDS sidecar container."""

    image: str = DEFAULT_ORDS_IMAGE
    container_name: str = "oracle-ords"
    db_container: str = "oracle-free-db"
    service_name: str = "freepdb1"
    db_host: str = "host.docker.internal"
    db_port: int = 1521
    host_https_port: int = 8443
    container_https_port: int = 8443
    host_http_port: int = 8181
    container_http_port: int = 8080
    apex_images_path: str = ""
    container_images_path: str = "/opt/oracle/apex/images"
    images_url_path: str = "/i/"
    db_user: str = "ORDS_PUBLIC_USER"
    db_password: str = "SuperSecret1"  # noqa: S105

    @classmethod
    def from_env(cls) -> OrdsConfig:
        """Build config from environment with quiet demo defaults.

        The service name is intentionally **not** read from ``DATABASE_SERVICE_NAME``:
        the local ORDS sidecar always targets the gvenzl PDB (``freepdb1``), whereas
        that env may point the app at a remote ATP service.
        """
        return cls(
            image=os.getenv("ORDS_IMAGE", DEFAULT_ORDS_IMAGE),
            db_password=os.getenv("DATABASE_PASSWORD", "SuperSecret1"),
        )


class OrdsSidecar:
    """Manage the ORDS sidecar container lifecycle via the container runtime."""

    def __init__(
        self,
        runtime: ContainerRuntime,
        config: OrdsConfig | None = None,
        console: Console | None = None,
    ) -> None:
        self.runtime = runtime
        self.config = config or OrdsConfig()
        self.console = console or Console()

    def _build_run_command(self) -> list[str]:
        """Build the ``docker run`` argv for the ORDS sidecar."""
        c = self.config
        cmd = [
            "run",
            "-d",
            "--name",
            c.container_name,
            # Reach the DB over the host gateway (no shared network / DB recreate).
            "--add-host=host.docker.internal:host-gateway",
            "-p",
            f"{c.host_https_port}:{c.container_https_port}",
            "-p",
            f"{c.host_http_port}:{c.container_http_port}",
            "-e",
            f"DBHOST={c.db_host}",
            "-e",
            f"DBPORT={c.db_port}",
            "-e",
            f"DBSERVICENAME={c.service_name}",
        ]
        if c.apex_images_path:
            # :z relabels for SELinux (Docker + Podman).
            cmd.extend(["-v", f"{c.apex_images_path}:{c.container_images_path}:z"])
        cmd.append(c.image)
        return cmd

    def is_running(self) -> bool:
        """True when the ORDS container is running."""
        return self.runtime.container_running(self.config.container_name)

    def start(self, *, recreate: bool = False) -> None:
        """Start the ORDS sidecar, idempotently."""
        name = self.config.container_name
        if self.runtime.container_running(name):
            if not recreate:
                self.console.print("[green]✓[/green] ORDS sidecar already running")
                return
            self.remove(force=True)
        elif self.runtime.container_exists(name):
            if recreate:
                self.remove(force=True)
            else:
                self.console.print("[cyan]Starting existing ORDS sidecar...[/cyan]")
                self.runtime.run_command(["start", name])
                return
        self.console.print("[cyan]Creating ORDS sidecar...[/cyan]")
        self.runtime.run_command(self._build_run_command())

    def stop(self, *, timeout: int = 30) -> None:
        """Stop the ORDS sidecar if it exists."""
        if self.runtime.container_exists(self.config.container_name):
            self.runtime.run_command(["stop", "-t", str(timeout), self.config.container_name])

    def remove(self, *, force: bool = False) -> None:
        """Remove the ORDS sidecar container if it exists."""
        if not self.runtime.container_exists(self.config.container_name):
            return
        cmd = ["rm"]
        if force:
            cmd.append("-f")
        cmd.append(self.config.container_name)
        self.runtime.run_command(cmd)

    def status(self) -> dict[str, str] | None:
        """Return container status details, or None when it does not exist."""
        if not self.runtime.container_exists(self.config.container_name):
            return None
        return self.runtime.get_container_status(self.config.container_name)

    def logs(self, *, follow: bool = False, tail: int | None = None) -> None:
        """Stream ORDS container logs."""
        if not self.runtime.container_exists(self.config.container_name):
            return
        cmd = ["logs"]
        if follow:
            cmd.append("-f")
        if tail:
            cmd.extend(["--tail", str(tail)])
        cmd.append(self.config.container_name)
        self.runtime.run_command(cmd, capture_output=False)

    def wait_for_healthy(self, timeout: int = 120, *, interval: int = 5) -> bool:
        """Poll until the ORDS container is up, or the timeout elapses.

        Container readiness is the deterministic signal here; a real ``/ords/``
        HTTP probe is validated in the integration smoke (Chapter 5).
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_running():
                return True
            time.sleep(interval)
        return False


def build_ords_sidecar(
    runtime: ContainerRuntime,
    media: ApexMedia,
    *,
    console: Console | None = None,
) -> OrdsSidecar:
    """Build an ORDS sidecar wired to serve Chapter 1's resolved APEX images dir."""
    config = replace(OrdsConfig.from_env(), apex_images_path=str(media.paths().images_dir))
    return OrdsSidecar(runtime, config, console=console)
