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

    sidecar.start()

    assert runtime.run_command.call_args.args[0][0] == "run"


def test_start_is_idempotent_when_running() -> None:
    """start() is a no-op when ORDS is already running."""
    sidecar, runtime = _sidecar()
    runtime.container_running.return_value = True

    sidecar.start()

    runtime.run_command.assert_not_called()


def test_start_restarts_existing_stopped_container_that_recovers() -> None:
    """A stopped sidecar that comes back up is restarted (not recreated)."""
    sidecar, runtime = _sidecar()
    runtime.container_running.side_effect = [False, True]  # stopped, then healthy after restart
    runtime.container_exists.return_value = True

    sidecar.start()

    assert runtime.run_command.call_args.args[0] == ["start", "oracle-ords"]


def test_start_recreates_stopped_container_that_stays_down() -> None:
    """A stopped sidecar that will not come back up is recreated from scratch."""
    sidecar, runtime = _sidecar()
    # top check: stopped; restart wait: still down; create wait: healthy
    runtime.container_running.side_effect = [False, False, True]
    runtime.container_exists.return_value = True

    sidecar.start()

    issued = [call.args[0] for call in runtime.run_command.call_args_list]
    assert ["start", "oracle-ords"] in issued
    assert ["rm", "-f", "oracle-ords"] in issued
    assert issued[-1][0] == "run"  # recreated as the final action


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


def test_wait_for_healthy_true_when_running() -> None:
    """wait_for_healthy returns True promptly once the container is running."""
    sidecar, runtime = _sidecar()
    runtime.container_running.return_value = True

    assert sidecar.wait_for_healthy(timeout=10) is True


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
