# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Container runtime abstraction for Docker and Podman."""

from __future__ import annotations

import shutil
import subprocess
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = (
    "ContainerNotFoundError",
    "ContainerRuntime",
    "ContainerRuntimeError",
    "NoRuntimeAvailableError",
    "RuntimeType",
)


class RuntimeType(StrEnum):
    """Supported container runtime backends."""

    DOCKER = "docker"
    PODMAN = "podman"
    NONE = "none"


class ContainerRuntimeError(Exception):
    """Base exception for container runtime errors."""


class NoRuntimeAvailableError(ContainerRuntimeError):
    """Raised when neither Docker nor Podman is available on PATH."""


class ContainerNotFoundError(ContainerRuntimeError):
    """Raised when the specified container does not exist."""


class ContainerRuntime:
    """Unified interface for Docker and Podman container operations."""

    def __init__(self) -> None:
        """Initialize container runtime by auto-detecting the available CLI."""
        self._runtime_type = self.detect_runtime()
        self._command = self._runtime_type.value if self._runtime_type != RuntimeType.NONE else None

    @staticmethod
    def detect_runtime() -> RuntimeType:
        """Detect which container runtime is available on the host.

        Returns:
            RuntimeType: ``DOCKER``, ``PODMAN``, or ``NONE``.
        """
        for candidate, runtime_type in (("docker", RuntimeType.DOCKER), ("podman", RuntimeType.PODMAN)):
            binary = shutil.which(candidate)
            if not binary:
                continue
            try:
                result = subprocess.run([binary, "--version"], capture_output=True, timeout=5, check=False)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
            if result.returncode == 0:
                return runtime_type
        return RuntimeType.NONE

    def is_available(self) -> bool:
        """Return True if Docker or Podman is available."""
        return self._runtime_type != RuntimeType.NONE

    def get_runtime_type(self) -> RuntimeType:
        """Return the detected container runtime enum."""
        return self._runtime_type

    def get_runtime_command(self) -> str:
        """Return the base CLI executable name for the active runtime.

        Raises:
            NoRuntimeAvailableError: If neither Docker nor Podman is installed.
        """
        if self._command is None:
            raise NoRuntimeAvailableError(
                "No container runtime available. Please install Docker or Podman.\n"
                "Docker: https://docs.docker.com/get-docker/\n"
                "Podman: https://podman.io/getting-started/installation"
            )
        return self._command

    def run_command(
        self, args: list[str], *, capture_output: bool = True, check: bool = True, timeout: int | None = None
    ) -> tuple[int, str, str]:
        """Run a container runtime command and return ``(returncode, stdout, stderr)``."""
        cmd = self.get_runtime_command()
        result = subprocess.run([cmd, *args], capture_output=capture_output, timeout=timeout, check=check, text=True)
        stdout = result.stdout if capture_output else ""
        stderr = result.stderr if capture_output else ""
        return result.returncode, stdout, stderr

    def copy_from_container(self, container_name: str, src_path: str, dest_path: Path) -> None:
        """Copy a file or directory tree out of a container onto the host filesystem."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        self.run_command(["cp", f"{container_name}:{src_path}", str(dest_path)])

    def version(self) -> str:
        """Return the container runtime version string."""
        _, stdout, _ = self.run_command(["--version"])
        return stdout.strip()

    def container_exists(self, container_name: str) -> bool:
        """Return True if a container with ``container_name`` exists in any state."""
        try:
            returncode, stdout, _ = self.run_command(
                ["ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"], check=False
            )
        except (subprocess.CalledProcessError, NoRuntimeAvailableError):
            return False
        if returncode != 0:
            return False
        names = {line.strip() for line in stdout.splitlines() if line.strip()}
        return container_name in names

    def container_running(self, container_name: str) -> bool:
        """Return True if ``container_name`` is currently running."""
        try:
            returncode, stdout, _ = self.run_command(
                ["ps", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"], check=False
            )
        except (subprocess.CalledProcessError, NoRuntimeAvailableError):
            return False
        if returncode != 0:
            return False
        names = {line.strip() for line in stdout.splitlines() if line.strip()}
        return container_name in names

    def get_container_status(self, container_name: str) -> dict[str, str]:
        """Return detailed inspect metadata and port mappings for ``container_name``.

        Raises:
            ContainerNotFoundError: If the container does not exist.
        """
        if not self.container_exists(container_name):
            raise ContainerNotFoundError(f"Container '{container_name}' does not exist")

        _, stdout, _ = self.run_command([
            "inspect",
            "--format",
            "{{.Name}}|{{.State.Status}}|{{.Id}}|{{.Config.Image}}|{{.Created}}",
            container_name,
        ])

        min_parts_for_status = 2
        min_parts_for_id = 3
        min_parts_for_image = 4
        min_parts_for_created = 5
        short_id_length = 12

        parts = stdout.strip().split("|")
        status_dict = {
            "name": parts[0].lstrip("/") if parts[0] else container_name,
            "status": parts[1] if len(parts) > min_parts_for_status - 1 else "unknown",
            "id": parts[2][:short_id_length] if len(parts) > min_parts_for_id - 1 else "",
            "image": parts[3] if len(parts) > min_parts_for_image - 1 else "",
            "created": parts[4] if len(parts) > min_parts_for_created - 1 else "",
        }

        _, ports_output, _ = self.run_command(["port", container_name], check=False)
        status_dict["ports"] = ports_output.strip() if ports_output else "none"
        return status_dict

    def get_container_ip(self, container_name: str) -> str | None:
        """Return the first container network IP address, or None when unavailable."""
        try:
            returncode, stdout, _stderr = self.run_command(
                ["inspect", "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", container_name],
                check=False,
            )
        except (subprocess.CalledProcessError, NoRuntimeAvailableError):
            return None
        if returncode != 0:
            return None
        ip_address = stdout.strip()
        return ip_address or None

    def volume_exists(self, volume_name: str) -> bool:
        """Return True if a named volume exists."""
        try:
            returncode, stdout, _ = self.run_command(
                ["volume", "ls", "--filter", f"name=^{volume_name}$", "--format", "{{.Name}}"], check=False
            )
        except (subprocess.CalledProcessError, NoRuntimeAvailableError):
            return False
        if returncode != 0:
            return False
        names = {line.strip() for line in stdout.splitlines() if line.strip()}
        return volume_name in names
