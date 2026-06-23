# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the gvenzl APEX install/upgrade engine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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
    return "\n".join(call.args[0][4] for call in runtime.run_command.call_args_list if call.args[0][0] == "exec")


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


def _exec_script(runtime: MagicMock) -> str:
    """Return the single bash -c script passed to run_command."""
    return runtime.run_command.call_args.args[0][4]


def test_provision_workspace_issues_ported_plsql() -> None:
    """The COFFEE workspace + ADMIN dev user PL/SQL matches the ported script."""
    installer, runtime = _installer((0, "PL/SQL procedure successfully completed.\n", ""))

    installer.provision_workspace()

    script = _exec_script(runtime)
    assert "apex_instance_admin.add_workspace" in script
    assert "p_workspace      => 'COFFEE'" in script
    assert "p_primary_schema => 'APP'" in script
    assert "apex_util.set_security_group_id" in script
    assert "apex_util.create_user" in script
    assert "'ADMIN'" in script
    assert "ADMIN:CREATE:DATA_LOADER:EDIT:RUN:CONVERT" in script


def test_provision_workspace_has_idempotency_guards() -> None:
    """Workspace and user creation are guarded by in-DB existence checks."""
    installer, runtime = _installer((0, "ok\n", ""))

    installer.provision_workspace()

    script = _exec_script(runtime)
    assert "apex_workspaces WHERE workspace = 'COFFEE'" in script
    assert "apex_workspace_apex_users" in script
    assert "IF v_ws = 0" in script
    assert "IF v_user = 0" in script


def test_provision_workspace_interpolates_config() -> None:
    """Custom schema / workspace / admin password / user flow into the PL/SQL."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.run_command.return_value = (0, "ok\n", "")
    db = OracleDatabase(runtime=runtime, config=DatabaseConfig())
    config = ApexInstallConfig(
        workspace="CYMBAL",
        primary_schema="cymbal",
        admin_user="DEVLEAD",
        admin_password="Pa55w0rd!",  # noqa: S106
    )
    installer = ApexInstaller(runtime, db, MagicMock(), config)

    installer.provision_workspace()

    script = _exec_script(runtime)
    assert "p_workspace      => 'CYMBAL'" in script
    assert "p_primary_schema => 'CYMBAL'" in script  # schema upper-cased
    assert "'DEVLEAD'" in script
    assert "Pa55w0rd!" in script


def test_provision_workspace_raises_on_db_error() -> None:
    """An ORA-/PLS- error in the output fails loudly."""
    installer, _ = _installer((0, "ORA-00955: name is already used by an existing object\n", ""))

    with pytest.raises(ApexInstallError):
        installer.provision_workspace()


# --- stage_media (docker cp) -------------------------------------------------


def test_stage_media_copies_tree_into_container() -> None:
    """stage_media ensures host media then docker-cps the apex/ tree into the container."""
    installer, runtime = _installer((0, "", ""), (0, "", ""))  # mkdir, cp
    installer.media.ensure.return_value.apex_dir = "/host/cache/26.1/apex"

    installer.stage_media()

    issued = [call.args[0] for call in runtime.run_command.call_args_list]
    assert ["exec", "oracle-free-db", "mkdir", "-p", "/tmp/apex"] in issued
    assert ["cp", "/host/cache/26.1/apex/.", "oracle-free-db:/tmp/apex"] in issued
    installer.media.ensure.assert_called_once_with(force=False)


def test_stage_media_force_propagates_to_ensure() -> None:
    """Force flows through to the Ch1 media pipeline (re-download/re-extract)."""
    installer, _ = _installer((0, "", ""), (0, "", ""))
    installer.media.ensure.return_value.apex_dir = "/host/apex"

    installer.stage_media(force=True)

    installer.media.ensure.assert_called_once_with(force=True)


# --- CLI auto-install on `infra start` --------------------------------------


def test_auto_install_runs_when_apex_absent() -> None:
    """Infra start installs APEX when the PDB has none."""
    from tools.oracle.cli import database as cli_db

    with patch.object(cli_db, "_build_apex_installer") as build:
        installer = build.return_value
        installer.installed_version.return_value = None
        cli_db._auto_install_apex(MagicMock())

    installer.install.assert_called_once()


def test_auto_install_skips_when_apex_present() -> None:
    """Infra start does not reinstall when APEX is already there."""
    from tools.oracle.cli import database as cli_db

    with patch.object(cli_db, "_build_apex_installer") as build:
        installer = build.return_value
        installer.installed_version.return_value = "26.1.0"
        cli_db._auto_install_apex(MagicMock())

    installer.install.assert_not_called()


def test_start_skip_apex_flag_skips_autoinstall() -> None:
    """`infra start --skip-apex` brings up the DB without touching APEX."""
    from click.testing import CliRunner
    from tools.oracle.cli import database as cli_db

    runner = CliRunner()
    with patch.object(cli_db, "_database") as mk_db, patch.object(cli_db, "_auto_install_apex") as auto:
        mk_db.return_value = MagicMock()
        result = runner.invoke(cli_db.database_start, ["--skip-apex", "--skip-ords"])

    assert result.exit_code == 0
    auto.assert_not_called()


def test_start_runs_autoinstall_by_default() -> None:
    """Plain `infra start` auto-installs APEX after the DB is healthy."""
    from click.testing import CliRunner
    from tools.oracle.cli import database as cli_db

    runner = CliRunner()
    with (
        patch.object(cli_db, "_database") as mk_db,
        patch.object(cli_db, "_auto_install_apex") as auto,
        patch.object(cli_db, "_start_ords"),
    ):
        mk_db.return_value = MagicMock()
        result = runner.invoke(cli_db.database_start, [])

    assert result.exit_code == 0
    auto.assert_called_once()


# --- infra apex CLI (Task 2.5) ----------------------------------------------


def test_apex_group_has_expected_commands() -> None:
    """The apex_group exposes install/upgrade/status plus APEXlang commands."""
    from tools.oracle.cli.apex import apex_group

    assert set(apex_group.commands) == {
        "export",
        "export-openapi",
        "generate",
        "import",
        "install",
        "status",
        "upgrade",
        "validate",
    }


@pytest.mark.parametrize("command", ["generate", "export", "validate", "import"])
def test_apexlang_command_help_lists_sqlcl_and_apex_prerequisites(command: str) -> None:
    """APEXlang lifecycle help names both local tool and runtime prerequisites."""
    from click.testing import CliRunner
    from tools.oracle.cli import apex as apex_cli

    result = CliRunner().invoke(apex_cli.apex_group, [command, "--help"])

    assert result.exit_code == 0
    assert "SQLcl 26.1.2+" in result.output
    assert "APEX 26.1+" in result.output


def test_apex_group_is_reexported() -> None:
    """apex_group is exported from both cli and the oracle package."""
    from tools.oracle import apex_group as pkg_group
    from tools.oracle.cli import apex_group as cli_group

    assert pkg_group is cli_group


def test_apex_install_command_invokes_installer() -> None:
    """`infra apex install --apex-version` builds the installer and installs."""
    from click.testing import CliRunner
    from tools.oracle.cli import apex as apex_cli

    runner = CliRunner()
    with patch.object(apex_cli, "_build_installer") as build:
        build.return_value.install.return_value = "26.1.0"
        result = runner.invoke(apex_cli.apex_group, ["install", "--apex-version", "26.1", "--force"])

    assert result.exit_code == 0
    assert build.call_args.kwargs.get("apex_version") == "26.1"
    build.return_value.install.assert_called_once_with(force=True)


def test_apex_status_command_reports_versions() -> None:
    """`infra apex status` prints installed and target versions."""
    from click.testing import CliRunner
    from tools.oracle.cli import apex as apex_cli

    runner = CliRunner()
    with patch.object(apex_cli, "_build_installer") as build:
        build.return_value.installed_version.return_value = "26.1.0"
        build.return_value.media.config.version = "26.1"
        result = runner.invoke(apex_cli.apex_group, ["status"])

    assert result.exit_code == 0
    assert "26.1.0" in result.output


def test_manage_infra_has_apex_subgroup() -> None:
    """`manage.py infra apex` resolves (apex subgroup wired into the flat infra group)."""
    import manage

    assert "apex" in manage.infra_group.commands


def test_apex_export_command_invokes_apexlang_wrapper() -> None:
    """`infra apex export` builds the APEXlang wrapper and exports an app."""
    from click.testing import CliRunner
    from tools.oracle.cli import apex as apex_cli

    runner = CliRunner()
    with patch.object(apex_cli, "_build_apex_lang") as build:
        build.return_value.export.return_value.target_path = "src/apex/cymbal-coffee-ops"
        result = runner.invoke(apex_cli.apex_group, ["export", "--app-id", "105"])

    assert result.exit_code == 0
    build.return_value.export.assert_called_once_with(app_id=105, alias="cymbal-coffee-ops", clean=True)


def test_apex_validate_command_invokes_apexlang_wrapper() -> None:
    """`infra apex validate --alias` targets the requested source alias."""
    from click.testing import CliRunner
    from tools.oracle.cli import apex as apex_cli

    runner = CliRunner()
    with patch.object(apex_cli, "_build_apex_lang") as build:
        build.return_value.validate.return_value.target_path = "src/apex/cymbal-coffee-ops"
        result = runner.invoke(apex_cli.apex_group, ["validate", "--alias", "ops"])

    assert result.exit_code == 0
    build.return_value.validate.assert_called_once_with(
        alias="ops",
        input_path=None,
        workspace=None,
        deployment=None,
        debug=False,
    )
