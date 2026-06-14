# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the gvenzl APEX install/upgrade engine."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from tools.oracle.apex_install import (
    ApexInstallConfig,
    ApexInstaller,
    ApexInstallError,
    compare_versions,
)
from tools.oracle.container import ContainerRuntime
from tools.oracle.database import DatabaseConfig, OracleDatabase


def _installer(*run_outputs: tuple[int, str, str]) -> tuple[ApexInstaller, MagicMock]:
    """Build an installer whose runtime.run_command yields the queued results."""
    runtime = MagicMock(spec=ContainerRuntime)
    if len(run_outputs) == 1:
        runtime.run_command.return_value = run_outputs[0]
    else:
        runtime.run_command.side_effect = list(run_outputs)
    db = OracleDatabase(runtime=runtime, config=DatabaseConfig())
    installer = ApexInstaller(runtime, db, MagicMock(), ApexInstallConfig())
    return installer, runtime


# --- config -----------------------------------------------------------------


def test_install_config_defaults() -> None:
    """Defaults target FREEPDB1, /tmp/apex, COFFEE workspace, ADMIN user, app schema."""
    config = ApexInstallConfig()

    assert config.pdb == "FREEPDB1"
    assert config.container_apex_dir == "/tmp/apex"
    assert config.images_url_path == "/i/"
    assert config.admin_user == "ADMIN"
    assert config.workspace == "COFFEE"
    assert config.primary_schema == "app"


def test_install_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """from_env honours DATABASE_USER for the primary (workspace) schema."""
    monkeypatch.setenv("DATABASE_USER", "cymbal")

    assert ApexInstallConfig.from_env().primary_schema == "cymbal"


# --- version comparison -----------------------------------------------------


def test_compare_versions_orders_releases() -> None:
    """Numeric, component-wise comparison drives skip/install/upgrade decisions."""
    assert compare_versions("24.2.14", "26.1") < 0
    assert compare_versions("26.2", "26.1") > 0
    assert compare_versions("26.1.0", "26.1.0") == 0


def test_compare_versions_normalises_differing_arity() -> None:
    """A 2-part target equals its 3-part zero-padded form (26.1 == 26.1.0)."""
    assert compare_versions("26.1", "26.1.0") == 0
    assert compare_versions("26.1.1", "26.1") > 0


# --- installed_version() + SYSDBA exec --------------------------------------


def test_installed_version_parses_value() -> None:
    """A clean apex_release query yields the version string."""
    installer, _ = _installer((0, "26.1.0\n", ""))

    assert installer.installed_version() == "26.1.0"


def test_installed_version_is_none_when_apex_absent() -> None:
    """ORA-00942 (apex_release view missing) reads as 'not installed'."""
    installer, _ = _installer((0, "ERROR at line 1:\nORA-00942: table or view does not exist\n", ""))

    assert installer.installed_version() is None


def test_installed_version_raises_on_unexpected_error() -> None:
    """A non-ORA-00942 database error surfaces loudly rather than reading as absent."""
    installer, _ = _installer((0, "ORA-01034: ORACLE not available\n", ""))

    with pytest.raises(ApexInstallError):
        installer.installed_version()


def test_exec_sysdba_runs_in_pdb_as_sysdba() -> None:
    """SYSDBA exec targets the container, uses `/ as sysdba`, and enters FREEPDB1."""
    installer, runtime = _installer((0, "26.1.0\n", ""))

    installer.installed_version()

    args = runtime.run_command.call_args.args[0]
    assert args[0] == "exec"
    assert "oracle-free-db" in args
    assert args[1:4] == ["oracle-free-db", "bash", "-c"]
    script = args[4]
    assert "sqlplus -S" in script
    assert "/ as sysdba" in script
    assert "ALTER SESSION SET CONTAINER=FREEPDB1" in script
    assert "apex_release" in script


def _orchestration_installer(*run_outputs: tuple[int, str, str]):
    """Installer with stage_media/provision_workspace mocked to isolate install()."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.run_command.side_effect = list(run_outputs)
    db = OracleDatabase(runtime=runtime, config=DatabaseConfig())
    media = MagicMock()
    media.config.version = "26.1"
    installer = ApexInstaller(runtime, db, media, ApexInstallConfig())
    installer.stage_media = MagicMock()  # type: ignore[method-assign]
    installer.provision_workspace = MagicMock()  # type: ignore[method-assign]
    return installer, runtime


def _execed_scripts(runtime: MagicMock) -> str:
    """Concatenate every bash -c script passed to run_command (for sequence asserts)."""
    return "\n".join(
        call.args[0][4] for call in runtime.run_command.call_args_list if call.args[0][0] == "exec"
    )


def test_install_runs_full_sequence_when_absent() -> None:
    """A fresh install stages media, runs apexins, configures admin, provisions, verifies."""
    installer, runtime = _orchestration_installer(
        (0, "ORA-00942: table or view does not exist\n", ""),  # detect -> None
        (0, "...apex installed...\n", ""),  # apexins
        (0, "PL/SQL procedure successfully completed.\n", ""),  # admin config
        (0, "26.1.0\n", ""),  # post-verify
    )

    result = installer.install()

    assert result == "26.1.0"
    installer.stage_media.assert_called_once()
    installer.provision_workspace.assert_called_once()
    assert "apexins.sql" in _execed_scripts(runtime)


def test_install_skips_when_target_already_satisfied() -> None:
    """Installed 26.1.0 satisfies target 26.1 -> no media staging, no apexins."""
    installer, runtime = _orchestration_installer((0, "26.1.0\n", ""))

    result = installer.install()

    assert result == "26.1.0"
    installer.stage_media.assert_not_called()
    assert "apexins.sql" not in _execed_scripts(runtime)


def test_install_upgrades_when_below_target() -> None:
    """Installed 24.2.14 is below 26.1 -> runs the install/upgrade sequence."""
    installer, _runtime = _orchestration_installer(
        (0, "24.2.14\n", ""),  # detect
        (0, "...\n", ""),  # apexins
        (0, "...\n", ""),  # admin
        (0, "26.1.0\n", ""),  # verify
    )

    result = installer.install()

    assert result == "26.1.0"
    installer.stage_media.assert_called_once()


def test_install_skips_when_installed_newer_than_target() -> None:
    """A newer installed line (27.0) is left alone (non-destructive default)."""
    installer, _runtime = _orchestration_installer((0, "27.0.0\n", ""))

    result = installer.install()

    assert result == "27.0.0"
    installer.stage_media.assert_not_called()


def test_install_force_runs_even_when_satisfied() -> None:
    """force=True re-runs the sequence regardless of the installed version."""
    installer, _runtime = _orchestration_installer(
        (0, "26.1.0\n", ""),  # detect (satisfied) but force overrides
        (0, "...\n", ""),  # apexins
        (0, "...\n", ""),  # admin
        (0, "26.1.0\n", ""),  # verify
    )

    result = installer.install(force=True)

    assert result == "26.1.0"
    installer.stage_media.assert_called_once()


def test_install_fails_loudly_when_target_not_reached() -> None:
    """If post-install apex_release doesn't satisfy the target, raise."""
    installer, _ = _orchestration_installer(
        (0, "ORA-00942: table or view does not exist\n", ""),  # detect -> None
        (0, "...\n", ""),  # apexins
        (0, "...\n", ""),  # admin
        (0, "ORA-00942: table or view does not exist\n", ""),  # verify -> still absent
    )

    with pytest.raises(ApexInstallError):
        installer.install()
