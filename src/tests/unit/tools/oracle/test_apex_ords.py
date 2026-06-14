# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the ORDS sidecar runtime."""

from __future__ import annotations

from unittest.mock import MagicMock

from tools.oracle.container import ContainerRuntime
from tools.oracle.ords import OrdsConfig, OrdsSidecar


def _sidecar(config: OrdsConfig | None = None) -> tuple[OrdsSidecar, MagicMock]:
    runtime = MagicMock(spec=ContainerRuntime)
    sidecar = OrdsSidecar(runtime, config or OrdsConfig(apex_images_path="/host/apex/images"))
    return sidecar, runtime


def test_ords_config_defaults() -> None:
    """ORDS targets the gvenzl DB over the host gateway, freepdb1, HTTPS 8443."""
    config = OrdsConfig()

    assert "ords" in config.image
    assert config.container_name == "oracle-ords"
    assert config.db_container == "oracle-free-db"
    assert config.service_name == "freepdb1"
    assert config.db_host == "host.docker.internal"
    assert config.db_port == 1521
    assert config.host_https_port == 8443


def test_build_run_command_shape() -> None:
    """The docker run argv names the container, maps ports, and ends with the image."""
    sidecar, _ = _sidecar()

    cmd = sidecar._build_run_command()

    assert cmd[0] == "run"
    assert "-d" in cmd
    assert cmd[cmd.index("--name") + 1] == "oracle-ords"
    assert "--add-host=host.docker.internal:host-gateway" in cmd
    assert "8443:8443" in cmd
    assert cmd[-1] == OrdsConfig().image


def test_build_run_command_mounts_images_for_i_path() -> None:
    """The Ch1 images dir is bind-mounted (SELinux :z) so ORDS can serve /i/."""
    sidecar, _ = _sidecar()

    cmd = sidecar._build_run_command()

    joined = " ".join(cmd)
    assert "/host/apex/images:" in joined
    assert ":z" in joined


def test_build_run_command_includes_db_connection_env() -> None:
    """ORDS receives the DB host/service connection via env."""
    sidecar, _ = _sidecar()

    cmd = sidecar._build_run_command()

    joined = " ".join(cmd)
    assert "DBHOST=host.docker.internal" in joined
    assert "DBSERVICENAME=freepdb1" in joined


def test_build_run_command_omits_mount_without_images_path() -> None:
    """With no images path configured, no image bind-mount is emitted."""
    sidecar, _ = _sidecar(OrdsConfig())

    cmd = sidecar._build_run_command()

    assert "/i/" not in " ".join(m for m in cmd if m == "-v")
    assert cmd.count("-v") == 0


def test_build_ords_sidecar_wires_ch1_images() -> None:
    """build_ords_sidecar pulls the resolved Ch1 images dir into the ORDS config."""
    from pathlib import Path

    from tools.oracle.ords import build_ords_sidecar

    runtime = MagicMock(spec=ContainerRuntime)
    media = MagicMock()
    media.paths.return_value.images_dir = Path("/cache/26.1/apex/images")

    sidecar = build_ords_sidecar(runtime, media)

    assert sidecar.config.apex_images_path == "/cache/26.1/apex/images"
    assert sidecar.config.service_name == "freepdb1"
    joined = " ".join(sidecar._build_run_command())
    assert "/cache/26.1/apex/images:/opt/oracle/apex/images:z" in joined
    assert "DBSERVICENAME=freepdb1" in joined
