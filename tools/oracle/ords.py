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
import re
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rich.console import Console

from tools.oracle.database import ContainerStartError

if TYPE_CHECKING:
    from tools.oracle.apex_media import ApexMedia
    from tools.oracle.container import ContainerRuntime

DEFAULT_ORDS_IMAGE = "container-registry.oracle.com/database/ords:26.1.2"
_VERSION_RE = re.compile(r"\b(\d+\.\d+(?:\.\d+)?)\b")
_IMAGE_TAG_VERSION_RE = re.compile(r":(\d+\.\d+(?:\.\d+)?)$")
_HTTP_READY_MIN = 200
_HTTP_STATIC_READY_MAX = 400
_HTTP_READY_MAX = 500


@dataclass
class OrdsConfig:
    """Configuration for the ORDS sidecar container."""

    image: str = DEFAULT_ORDS_IMAGE
    minimum_version: str = "26.1.1"
    preferred_version: str = "26.1.2"
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
    # SYS password the ORDS image uses for its first-run `ords install`. gvenzl sets
    # SYS/SYSTEM from ORACLE_PASSWORD, so this must mirror that, not DATABASE_PASSWORD
    # (the app user). Without it the container exits: "ORACLE_PWD ... must be declared".
    oracle_pwd: str = "super-secret"  # noqa: S105
    http_probe_timeout: float = 5.0

    @classmethod
    def from_env(cls) -> OrdsConfig:
        """Build config from environment with quiet demo defaults.

        The service name is intentionally **not** read from ``DATABASE_SERVICE_NAME``:
        the local ORDS sidecar always targets the gvenzl PDB (``freepdb1``), whereas
        that env may point the app at a remote ATP service.
        """
        return cls(
            image=os.getenv("ORDS_IMAGE", DEFAULT_ORDS_IMAGE),
            oracle_pwd=os.getenv("ORACLE_PASSWORD", os.getenv("ORACLE_SYSTEM_PASSWORD", "super-secret")),
        )


class OrdsSidecar:
    """Manage the ORDS sidecar container lifecycle via the container runtime."""

    def __init__(
        self, runtime: ContainerRuntime, config: OrdsConfig | None = None, console: Console | None = None
    ) -> None:
        self.runtime = runtime
        self.config = config or OrdsConfig()
        self.console = console or Console()
        self._last_health_failure: str | None = None
        self._terminal_health_failure = False

    def _build_run_command(self) -> list[str]:
        """Build the ``docker run`` argv for the ORDS sidecar."""
        c = self.config
        db_host = self._database_host_for_sidecar()
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
            f"DBHOST={db_host}",
            "-e",
            f"DBPORT={c.db_port}",
            "-e",
            f"DBSERVICENAME={c.service_name}",
            # SYS password for the image's first-run `ords install` (required, or it exits).
            "-e",
            f"ORACLE_PWD={c.oracle_pwd}",
        ]
        if c.apex_images_path:
            # :z relabels for SELinux (Docker + Podman).
            cmd.extend(["-v", f"{c.apex_images_path}:{c.container_images_path}:z"])
        cmd.append(c.image)
        return cmd

    def _database_host_for_sidecar(self) -> str:
        """Return the DB host reachable from the ORDS sidecar."""
        if self.config.db_host != OrdsConfig.db_host:
            return self.config.db_host
        return self.runtime.get_container_ip(self.config.db_container) or self.config.db_host

    def is_running(self) -> bool:
        """True when the ORDS container is running."""
        return self.runtime.container_running(self.config.container_name)

    @staticmethod
    def _version_tuple(version: str) -> tuple[int, ...]:
        """Parse a dotted version into comparable integer parts."""
        return tuple(int(part) for part in version.split("."))

    @classmethod
    def _compare_versions(cls, left: str, right: str) -> int:
        """Component-wise dotted version compare."""
        left_parts = cls._version_tuple(left)
        right_parts = cls._version_tuple(right)
        width = max(len(left_parts), len(right_parts))
        padded_left = left_parts + (0,) * (width - len(left_parts))
        padded_right = right_parts + (0,) * (width - len(right_parts))
        return (padded_left > padded_right) - (padded_left < padded_right)

    @staticmethod
    def _parse_ords_version(output: str) -> str | None:
        """Extract an ORDS version from command or log output."""
        for line in output.splitlines():
            if "ords" not in line.lower() and "oracle rest data services" not in line.lower():
                continue
            match = _VERSION_RE.search(line)
            if match is not None:
                return match.group(1)
        match = _VERSION_RE.search(output)
        return match.group(1) if match is not None else None

    @staticmethod
    def _image_tag_version(image: str) -> str | None:
        """Extract a dotted version from an explicit ORDS image tag."""
        match = _IMAGE_TAG_VERSION_RE.search(image)
        return match.group(1) if match is not None else None

    @classmethod
    def _normalize_runtime_version(cls, version: str, *, image: str) -> str:
        """Use explicit image tag precision when ORDS reports only major.minor."""
        tag_version = cls._image_tag_version(image)
        if tag_version is None:
            return version
        version_parts = cls._version_tuple(version)
        tag_parts = cls._version_tuple(tag_version)
        if len(version_parts) < len(tag_parts) and tag_parts[: len(version_parts)] == version_parts:
            return tag_version
        return version

    def runtime_version(self) -> str | None:
        """Probe the running ORDS container version, falling back to logs."""
        name = self.config.container_name
        for cmd in (["exec", name, "ords", "--version"], ["logs", "--tail", "200", name]):
            try:
                _returncode, stdout, stderr = self.runtime.run_command(cmd, check=False, timeout=20)
            except Exception:  # noqa: BLE001 - runtime failures make the probe inconclusive.
                stdout = ""
                stderr = ""
            version = self._parse_ords_version(f"{stdout}\n{stderr}")
            if version is not None:
                return self._normalize_runtime_version(version, image=self.config.image)
        return None

    def version_satisfies_minimum(self) -> bool:
        """True when the probed ORDS version is at or above the configured minimum."""
        version = self.runtime_version()
        return version is not None and self._compare_versions(version, self.config.minimum_version) >= 0

    def _version_below_minimum(self, version: str) -> bool:
        """True when a known ORDS version is below the configured minimum."""
        return self._compare_versions(version, self.config.minimum_version) < 0

    def _version_status(self, version: str | None) -> str:
        """Return a compact status label for the probed ORDS version."""
        if version is None:
            return "unknown"
        if self._compare_versions(version, self.config.minimum_version) < 0:
            return "outdated"
        return "ok"

    def _http_url(self, path: str) -> str:
        """Build a localhost HTTP readiness URL for the ORDS sidecar."""
        normalized = path if path.startswith("/") else f"/{path}"
        return f"http://localhost:{self.config.host_http_port}{normalized}"

    def _http_status(self, path: str) -> int | None:
        """Return HTTP status for a readiness path, or None when unreachable."""
        request = Request(self._http_url(path), method="GET")  # noqa: S310
        try:
            with urlopen(request, timeout=self.config.http_probe_timeout) as response:  # noqa: S310
                return cast("int", response.status)
        except HTTPError as exc:
            return exc.code
        except (TimeoutError, URLError, OSError):
            return None

    def _http_ready(self, path: str) -> bool:
        """Return readiness for ORDS routing and APEX static media paths."""
        status = self._http_status(path)
        if status is None:
            return False
        if path.startswith(self.config.images_url_path):
            return _HTTP_READY_MIN <= status < _HTTP_STATIC_READY_MAX
        return _HTTP_READY_MIN <= status < _HTTP_READY_MAX

    def http_ready(self, path: str) -> bool:
        """Public wrapper for ORDS HTTP readiness checks."""
        return self._http_ready(path)

    def _health_failure_reason(self) -> str:
        """Return the latest health failure in a form suitable for operator errors."""
        if self._last_health_failure:
            return self._last_health_failure
        return f"ORDS did not satisfy the readiness/version policy (minimum ORDS {self.config.minimum_version})"

    def _check_health_once(self) -> tuple[bool, bool]:
        """Run one ORDS health probe; return (healthy, stop_waiting)."""
        name = self.config.container_name
        running = self.is_running()
        if not running:
            exists = self.runtime.container_exists(name)
            if exists:
                self._last_health_failure = f"ORDS sidecar '{name}' exited before readiness completed"
            else:
                self._last_health_failure = f"ORDS sidecar '{name}' is not running yet"
            return False, exists

        version = self.runtime_version()
        if version is None:
            self._last_health_failure = (
                f"ORDS runtime version probe is inconclusive (minimum ORDS {self.config.minimum_version})"
            )
            return False, False
        if self._version_below_minimum(version):
            self._last_health_failure = (
                f"ORDS runtime version {version} is below required minimum {self.config.minimum_version}"
            )
            self._terminal_health_failure = True
            return False, True

        failed_path = ""
        if not self._http_ready("/ords/"):
            failed_path = "/ords/ HTTP"
        elif not self._http_ready(self.config.images_url_path):
            failed_path = f"static media path {self.config.images_url_path}"
        if failed_path:
            self._last_health_failure = f"ORDS {failed_path} readiness did not pass"
            return False, False

        self._last_health_failure = None
        return True, False

    def start(self, *, recreate: bool = False) -> None:
        """Start the ORDS sidecar and verify it stays up.

        A stopped sidecar is treated as a prior failure: it is restarted once and,
        if it does not stay up, recreated. Raises if the sidecar never comes up so
        callers report a real failure instead of a misleading success.

        Raises:
            ContainerStartError: If the sidecar exits or never becomes healthy.
        """
        name = self.config.container_name
        if self.runtime.container_running(name):
            if not recreate:
                if not self.wait_for_healthy():
                    raise ContainerStartError(
                        f"ORDS sidecar '{self.config.container_name}' is running but {self._health_failure_reason()}."
                    )
                self.console.print("[green]OK[/green] ORDS sidecar already running")
                return
            self.remove(force=True)
        elif self.runtime.container_exists(name):
            if not recreate and self._restart_existing():
                return
            self.remove(force=True)
        self._create_and_verify()

    def _restart_existing(self) -> bool:
        """Restart a stopped sidecar; return True only if it stays up."""
        self.console.print("[cyan]Starting existing ORDS sidecar...[/cyan]")
        self.runtime.run_command(["start", self.config.container_name])
        if self.wait_for_healthy():
            self.console.print("[green]OK[/green] ORDS sidecar is up")
            return True
        if self._terminal_health_failure:
            raise ContainerStartError(
                f"ORDS sidecar '{self.config.container_name}' restarted but {self._health_failure_reason()}."
            )
        self.console.print("[yellow]ORDS sidecar did not stay up - recreating...[/yellow]")
        return False

    def _create_and_verify(self) -> None:
        """Create the sidecar and fail loudly if it does not stay up."""
        self.console.print("[cyan]Creating ORDS sidecar...[/cyan]")
        self.runtime.run_command(self._build_run_command())
        if self.wait_for_healthy():
            self.console.print("[green]OK[/green] ORDS sidecar is up")
            return
        logs_hint = f"{self.runtime.get_runtime_command()} logs {self.config.container_name}"
        raise ContainerStartError(
            f"ORDS sidecar '{self.config.container_name}' started but {self._health_failure_reason()}. "
            f"Check logs with: {logs_hint}"
        )

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
        status = self.runtime.get_container_status(self.config.container_name)
        version = self.runtime_version()
        status["ords_version"] = version or "unknown"
        status["minimum_version"] = self.config.minimum_version
        status["preferred_version"] = self.config.preferred_version
        status["version_status"] = self._version_status(version)
        return status

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
        """Poll until ORDS version and HTTP readiness probes pass."""
        self._last_health_failure = None
        self._terminal_health_failure = False
        start_time = time.time()
        while time.time() - start_time < timeout:
            healthy, stop_waiting = self._check_health_once()
            if healthy:
                return True
            if stop_waiting:
                return False
            time.sleep(interval)
        if self._last_health_failure is None:
            self._last_health_failure = (
                f"timed out waiting for ORDS readiness/version policy (minimum ORDS {self.config.minimum_version})"
            )
        return False


def build_ords_sidecar(runtime: ContainerRuntime, media: ApexMedia, *, console: Console | None = None) -> OrdsSidecar:
    """Build an ORDS sidecar wired to serve Chapter 1's resolved APEX images dir."""
    config = replace(OrdsConfig.from_env(), apex_images_path=str(media.paths().images_dir))
    return OrdsSidecar(runtime, config, console=console)
