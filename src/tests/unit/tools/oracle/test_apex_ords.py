# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the ORDS sidecar runtime."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from tools.oracle.container import ContainerRuntime
from tools.oracle.database import ContainerStartError
from tools.oracle.ords import OrdsConfig, OrdsSidecar


def _sidecar(config: OrdsConfig | None = None) -> tuple[OrdsSidecar, MagicMock]:
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.get_container_ip.return_value = None
    sidecar = OrdsSidecar(runtime, config or OrdsConfig(apex_images_path="/host/apex/images"))
    return sidecar, runtime


def test_ords_config_defaults() -> None:
    """ORDS targets the gvenzl DB over the host gateway, freepdb1, HTTPS 8443."""
    config = OrdsConfig()

    assert config.image == "container-registry.oracle.com/database/ords:26.1.2"
    assert config.minimum_version == "26.1.1"
    assert config.preferred_version == "26.1.2"
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
    """ORDS receives the DB host/service connection and SYS password via env."""
    sidecar, _ = _sidecar()

    cmd = sidecar._build_run_command()

    joined = " ".join(cmd)
    assert "DBHOST=host.docker.internal" in joined
    assert "DBSERVICENAME=freepdb1" in joined
    # ORACLE_PWD (SYS) is required, or the ORDS image exits before installing.
    assert "ORACLE_PWD=super-secret" in joined


def test_from_env_uses_oracle_password_for_install(monkeypatch: pytest.MonkeyPatch) -> None:
    """ORACLE_PWD comes from the SYS password (ORACLE_PASSWORD), not DATABASE_PASSWORD."""
    monkeypatch.setenv("ORACLE_PASSWORD", "sys-secret")
    monkeypatch.setenv("DATABASE_PASSWORD", "app-secret")

    config = OrdsConfig.from_env()

    assert config.oracle_pwd == "sys-secret"  # noqa: S105
    joined = " ".join(OrdsSidecar(MagicMock(spec=ContainerRuntime), config)._build_run_command())
    assert "ORACLE_PWD=sys-secret" in joined
    assert "app-secret" not in joined


def test_build_run_command_prefers_running_db_container_ip() -> None:
    """Rootless Docker sidecars can reach the DB container IP when host-gateway cannot."""
    sidecar, runtime = _sidecar()
    runtime.get_container_ip.return_value = "172.17.0.3"

    cmd = sidecar._build_run_command()

    joined = " ".join(cmd)
    assert "DBHOST=172.17.0.3" in joined
    assert "DBHOST=host.docker.internal" not in joined


def test_build_run_command_preserves_explicit_db_host_override() -> None:
    """A caller-supplied DB host is respected even if the DB container has an IP."""
    sidecar, runtime = _sidecar(OrdsConfig(db_host="oracle.example.test"))
    runtime.get_container_ip.return_value = "172.17.0.3"

    cmd = sidecar._build_run_command()

    joined = " ".join(cmd)
    assert "DBHOST=oracle.example.test" in joined
    assert "DBHOST=172.17.0.3" not in joined


def test_from_env_keeps_ords_image_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """ORDS_IMAGE overrides the default image while preserving runtime version policy."""
    monkeypatch.setenv("ORDS_IMAGE", "container-registry.oracle.com/database/ords:26.1.2")

    config = OrdsConfig.from_env()

    assert config.image == "container-registry.oracle.com/database/ords:26.1.2"
    assert config.minimum_version == "26.1.1"
    assert config.preferred_version == "26.1.2"


@pytest.mark.parametrize(
    ("probed", "expected"),
    [
        ("ORDS Release 26.1.2.r123", True),
        ("Oracle REST Data Services version 26.1.1", True),
        ("Oracle REST Data Services version 26.1", True),
        ("Oracle REST Data Services version 25.4.0", False),
        ("", False),
    ],
)
def test_ords_version_probe_enforces_minimum(probed: str, expected: bool) -> None:
    """Runtime version probes must not silently accept ORDS below 26.1.1."""
    sidecar, runtime = _sidecar()
    runtime.run_command.return_value = (0, probed, "")

    assert sidecar.version_satisfies_minimum() is expected


def test_major_minor_probe_uses_explicit_image_patch_version() -> None:
    """The ORDS image can report 26.1 even when the explicit tag is 26.1.2."""
    sidecar, runtime = _sidecar(OrdsConfig(image="container-registry.oracle.com/database/ords:26.1.2"))
    runtime.run_command.return_value = (0, "Oracle REST Data Services version 26.1", "")

    assert sidecar.runtime_version() == "26.1.2"
    assert sidecar.version_satisfies_minimum() is True


def test_ords_status_includes_runtime_version_policy() -> None:
    """status() enriches container status with runtime version and policy details."""
    sidecar, runtime = _sidecar()
    runtime.container_exists.return_value = True
    runtime.get_container_status.return_value = {
        "name": "oracle-ords",
        "status": "running",
        "image": OrdsConfig().image,
        "ports": "8181/tcp",
    }
    runtime.run_command.return_value = (0, "ORDS Release 26.1.2.r123", "")

    status = sidecar.status()

    assert status is not None
    assert status["ords_version"] == "26.1.2"
    assert status["minimum_version"] == "26.1.1"
    assert status["preferred_version"] == "26.1.2"
    assert status["version_status"] == "ok"


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


def test_start_runs_container_when_absent() -> None:
    """start() issues docker run when no ORDS container exists, then verifies it."""
    sidecar, runtime = _sidecar()
    runtime.container_running.side_effect = [False, True]  # absent at first; healthy after run
    runtime.container_exists.return_value = False
    runtime.run_command.return_value = (0, "ORDS Release 26.1.2.r123", "")

    with patch.object(sidecar, "_http_ready", return_value=True):
        sidecar.start()

    issued = [call.args[0] for call in runtime.run_command.call_args_list]
    assert any(cmd[0] == "run" for cmd in issued)


def test_start_is_idempotent_when_running() -> None:
    """start() does not recreate a running ORDS sidecar that passes readiness."""
    sidecar, runtime = _sidecar()
    runtime.container_running.return_value = True
    runtime.run_command.return_value = (0, "ORDS Release 26.1.2.r123", "")

    with patch.object(sidecar, "_http_ready", return_value=True):
        sidecar.start()

    assert not any(call.args[0][0] == "run" for call in runtime.run_command.call_args_list)


def test_start_rejects_running_sidecar_below_minimum() -> None:
    """start() must not silently accept an already-running ORDS below 26.1.1."""
    sidecar, runtime = _sidecar()
    runtime.container_running.return_value = True
    runtime.run_command.return_value = (0, "ORDS Release 25.4.0", "")

    with pytest.raises(ContainerStartError, match=r"25\.4\.0.*below required minimum 26\.1\.1"):
        sidecar.start()


def test_start_reports_created_sidecar_below_minimum() -> None:
    """A freshly-created below-minimum ORDS reports the version policy failure."""
    sidecar, runtime = _sidecar()
    runtime.container_running.side_effect = [False, True]
    runtime.container_exists.return_value = False
    runtime.run_command.return_value = (0, "ORDS Release 25.4.0", "")
    runtime.get_runtime_command.return_value = "docker"

    with pytest.raises(ContainerStartError, match=r"25\.4\.0.*below required minimum 26\.1\.1"):
        sidecar.start()


def test_start_restarts_existing_stopped_container_that_recovers() -> None:
    """A stopped sidecar that comes back up is restarted (not recreated)."""
    sidecar, runtime = _sidecar()
    runtime.container_running.side_effect = [False, True]  # stopped, then healthy after restart
    runtime.container_exists.return_value = True
    runtime.run_command.return_value = (0, "ORDS Release 26.1.2.r123", "")

    with patch.object(sidecar, "_http_ready", return_value=True):
        sidecar.start()

    issued = [call.args[0] for call in runtime.run_command.call_args_list]
    assert ["start", "oracle-ords"] in issued


def test_start_recreates_stopped_container_that_stays_down() -> None:
    """A stopped sidecar that will not come back up is recreated from scratch."""
    sidecar, runtime = _sidecar()
    # top check: stopped; restart wait: still down; create wait: healthy
    runtime.container_running.side_effect = [False, False, True]
    runtime.container_exists.return_value = True
    runtime.run_command.return_value = (0, "ORDS Release 26.1.2.r123", "")

    with patch.object(sidecar, "_http_ready", return_value=True):
        sidecar.start()

    issued = [call.args[0] for call in runtime.run_command.call_args_list]
    assert ["start", "oracle-ords"] in issued
    assert ["rm", "-f", "oracle-ords"] in issued
    assert any(cmd[0] == "run" for cmd in issued)


def test_start_raises_when_sidecar_never_comes_up() -> None:
    """start() fails loudly (no silent success) when a fresh sidecar exits."""
    sidecar, runtime = _sidecar()
    runtime.container_running.side_effect = [False, False]  # absent, then never healthy
    runtime.container_exists.side_effect = [False, True]  # absent at top; exited during wait

    with pytest.raises(ContainerStartError):
        sidecar.start()

    assert runtime.run_command.call_args.args[0][0] == "run"


def test_stop_stops_existing() -> None:
    """stop() stops the container when it exists."""
    sidecar, runtime = _sidecar()
    runtime.container_exists.return_value = True

    sidecar.stop()

    assert runtime.run_command.call_args.args[0] == ["stop", "-t", "30", "oracle-ords"]


def test_remove_force() -> None:
    """remove(force=True) force-removes the container."""
    sidecar, runtime = _sidecar()
    runtime.container_exists.return_value = True

    sidecar.remove(force=True)

    assert runtime.run_command.call_args.args[0] == ["rm", "-f", "oracle-ords"]


def test_wait_for_healthy_requires_container_version_and_http_ready() -> None:
    """wait_for_healthy requires running container, minimum ORDS version, /ords/, and /i/."""
    sidecar, runtime = _sidecar()
    runtime.container_running.return_value = True
    runtime.run_command.return_value = (0, "ORDS Release 26.1.2.r123", "")

    with patch.object(sidecar, "_http_ready", return_value=True) as http_ready:
        assert sidecar.wait_for_healthy(timeout=10) is True

    http_ready.assert_any_call("/ords/")
    http_ready.assert_any_call("/i/")


def test_wait_for_healthy_retries_inconclusive_version_probe() -> None:
    """An unknown version probe is warning-level and can recover before timeout."""
    sidecar, runtime = _sidecar()
    runtime.container_running.return_value = True
    runtime.container_exists.return_value = True
    runtime.run_command.side_effect = [
        (0, "", ""),
        (0, "", ""),
        (0, "ORDS Release 26.1.2.r123", ""),
    ]

    with patch.object(sidecar, "_http_ready", return_value=True), patch("tools.oracle.ords.time.sleep"):
        assert sidecar.wait_for_healthy(timeout=1, interval=0) is True


def test_wait_for_healthy_rejects_unready_ords_http() -> None:
    """A running, version-valid container is not healthy until /ords/ is non-5xx."""
    sidecar, runtime = _sidecar()
    runtime.container_running.return_value = True
    runtime.container_exists.return_value = True
    runtime.run_command.return_value = (0, "ORDS Release 26.1.2.r123", "")

    with patch.object(sidecar, "_http_ready", return_value=False):
        assert sidecar.wait_for_healthy(timeout=0.01, interval=0) is False


def test_http_ready_accepts_non_5xx_for_ords() -> None:
    """The ORDS endpoint is ready on any routed non-5xx HTTP response."""
    sidecar, _ = _sidecar()

    with patch("tools.oracle.ords.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.status = 404

        assert sidecar._http_ready("/ords/") is True


def test_http_ready_accepts_apex_images_success() -> None:
    """The APEX images endpoint is ready when /i/ returns a curl -f compatible success."""
    sidecar, _ = _sidecar()

    with patch("tools.oracle.ords.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.status = 200

        assert sidecar._http_ready("/i/") is True


@pytest.mark.parametrize("status", [403, 404])
def test_http_ready_rejects_apex_images_client_errors(status: int) -> None:
    """The APEX images endpoint is not ready when /i/ is forbidden or missing."""
    sidecar, _ = _sidecar()

    with patch("tools.oracle.ords.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.status = status

        assert sidecar._http_ready("/i/") is False


def test_http_ready_rejects_server_errors() -> None:
    """Server errors on either readiness URL are not treated as healthy."""
    sidecar, _ = _sidecar()

    with patch("tools.oracle.ords.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.status = 503

        assert sidecar._http_ready("/ords/") is False


def test_wait_for_healthy_times_out() -> None:
    """wait_for_healthy returns False when readiness never arrives."""
    sidecar, runtime = _sidecar()
    runtime.container_running.return_value = False

    assert sidecar.wait_for_healthy(timeout=0) is False


# --- infra start/stop/remove integration (Task 3.4) -------------------------


def test_infra_start_starts_ords_after_apex() -> None:
    """`infra start` brings up ORDS after APEX is ensured (correct order)."""
    from click.testing import CliRunner
    from tools.oracle.cli import database as cli_db

    runner = CliRunner()
    with (
        patch.object(cli_db, "_database", return_value=MagicMock()),
        patch.object(cli_db, "_auto_install_apex") as auto,
        patch.object(cli_db, "_start_ords") as ords,
    ):
        manager = MagicMock()
        manager.attach_mock(auto, "auto")
        manager.attach_mock(ords, "ords")
        result = runner.invoke(cli_db.database_start, [])

    assert result.exit_code == 0
    assert [name for name, _, _ in manager.mock_calls] == ["auto", "ords"]


def test_infra_start_skip_ords() -> None:
    """`infra start --skip-ords` brings up DB + APEX but not ORDS."""
    from click.testing import CliRunner
    from tools.oracle.cli import database as cli_db

    runner = CliRunner()
    with (
        patch.object(cli_db, "_database", return_value=MagicMock()),
        patch.object(cli_db, "_auto_install_apex"),
        patch.object(cli_db, "_start_ords") as ords,
    ):
        result = runner.invoke(cli_db.database_start, ["--skip-ords"])

    assert result.exit_code == 0
    ords.assert_not_called()


def test_infra_stop_also_stops_ords() -> None:
    """`infra stop` tears down the ORDS sidecar alongside the DB."""
    from click.testing import CliRunner
    from tools.oracle.cli import database as cli_db

    runner = CliRunner()
    db = MagicMock()
    db.is_running.return_value = True
    sidecar = MagicMock()
    with (
        patch.object(cli_db, "_database", return_value=db),
        patch.object(cli_db, "_build_ords_sidecar", return_value=sidecar),
    ):
        result = runner.invoke(cli_db.database_stop, [])

    assert result.exit_code == 0
    sidecar.stop.assert_called_once()


def test_infra_remove_also_removes_ords() -> None:
    """`infra wipe` removes the ORDS sidecar alongside the DB."""
    from click.testing import CliRunner
    from tools.oracle.cli import database as cli_db

    runner = CliRunner()
    sidecar = MagicMock()
    with (
        patch.object(cli_db, "_database", return_value=MagicMock()),
        patch.object(cli_db, "_build_ords_sidecar", return_value=sidecar),
    ):
        result = runner.invoke(cli_db.database_remove, ["--force", "--yes"])

    assert result.exit_code == 0
    sidecar.remove.assert_called_once()


def test_infra_status_reports_ords_sidecar() -> None:
    """`infra status --verbose` includes ORDS sidecar state with the DB status."""
    from click.testing import CliRunner
    from tools.oracle.cli import database as cli_db

    runner = CliRunner()
    db = MagicMock()
    db.config.container_name = "oracle-free-db"
    db.status.return_value.exists = True
    db.status.return_value.running = True
    db.status.return_value.healthy = True
    db.status.return_value.image = "gvenzl/oracle-free:latest"
    db.status.return_value.created_at = "2026-06-23"
    db.status.return_value.uptime = "1 hour"
    db.status.return_value.ports = "1521/tcp"
    sidecar = MagicMock()
    sidecar.status.return_value = {
        "name": "oracle-ords",
        "running": "true",
        "image": "container-registry.oracle.com/database/ords:latest",
        "ports": "8443/tcp",
        "ords_version": "26.1.2",
        "minimum_version": "26.1.1",
        "preferred_version": "26.1.2",
        "version_status": "ok",
    }
    with (
        patch.object(cli_db, "_database", return_value=db),
        patch.object(cli_db, "_build_ords_sidecar", return_value=sidecar),
    ):
        result = runner.invoke(cli_db.database_status, ["--verbose"])

    assert result.exit_code == 0
    assert "ORDS Sidecar" in result.output
    assert "oracle-ords" in result.output
    assert "8443/tcp" in result.output
    assert "ORDS Version" in result.output
    assert "26.1.2" in result.output
    assert "APEX Media" in result.output
    assert "APEX Patch" in result.output
    sidecar.status.assert_called_once()
