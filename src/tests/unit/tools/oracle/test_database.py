# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Oracle database container configuration and command builder."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from click.testing import CliRunner
from tools.oracle.cli.database import database_remove, database_start
from tools.oracle.container import ContainerRuntime
from tools.oracle.database import (
    VECTOR_MEMORY_CHECK_SQL,
    ContainerNotFoundError,
    ContainerStartError,
    DatabaseConfig,
    OracleDatabase,
)

DEMO_PASSWORD = "SuperSecret1"  # noqa: S105
OEE_ENV_PASSWORD = "OeeSecret123"  # noqa: S105
INVALID_ORACLE_PROFILE_VALUE = "secret1"


def test_database_config_defaults() -> None:
    """Verify default configurations for ADB Free container."""
    config = DatabaseConfig()
    assert config.image == "container-registry.oracle.com/database/adb-free:latest-26ai"
    assert config.host_port == 1521
    assert config.container_port == 1522
    assert config.host_mtls_port == 1522
    assert config.container_mtls_port == 1522
    assert config.host_https_port == 8443
    assert config.container_https_port == 8443
    assert config.host_mongo_port == 27017
    assert config.container_mongo_port == 27017
    assert config.admin_username == "admin"
    assert config.admin_password == DEMO_PASSWORD
    assert config.wallet_password == DEMO_PASSWORD
    assert config.app_username == "app"
    assert config.app_password == DEMO_PASSWORD
    assert config.oee_password == DEMO_PASSWORD
    assert config.wallet_location == ".envs/tns"
    assert config.data_location == "/dev/shm/oracle-data"
    assert config.audit_location == "/dev/shm/oracle-audit"
    assert config.oradata_location == "/dev/shm/oracle-oradata"


def test_database_config_reads_audit_location_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The database container should allow relocating Oracle audit files."""
    monkeypatch.setenv("ORACLE_AUDIT_LOCATION", "/tmp/oracle-audit")

    config = DatabaseConfig.from_env()

    assert config.audit_location == "/tmp/oracle-audit"


def test_database_config_reads_ports_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The database container config should load host ports from environment variables."""
    monkeypatch.setenv("ORACLE26AI_PORT", "1234")
    monkeypatch.setenv("ORACLE_MTLS_PORT", "2345")
    monkeypatch.setenv("ORACLE_HTTPS_PORT", "3456")
    monkeypatch.setenv("ORACLE_MONGO_PORT", "4567")

    config = DatabaseConfig.from_env()

    assert config.host_port == 1234
    assert config.host_mtls_port == 2345
    assert config.host_https_port == 3456
    assert config.host_mongo_port == 4567


def test_database_config_reads_oee_password_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The managed ADB installer should allow a dedicated OEE demo password."""
    monkeypatch.setenv("OEE_PASSWORD", OEE_ENV_PASSWORD)

    config = DatabaseConfig.from_env()

    assert config.oee_password == OEE_ENV_PASSWORD


def test_build_run_command_contains_correct_flags() -> None:
    """Verify built docker/podman command contains required ADB parameters."""
    runtime = MagicMock(spec=ContainerRuntime)
    config = DatabaseConfig(wallet_location=".envs/tns")
    db = OracleDatabase(runtime=runtime, config=config)
    cmd = db._build_run_command()

    assert cmd[-1] == "container-registry.oracle.com/database/adb-free:latest-26ai"

    assert "-p" in cmd
    assert "1521:1522" in cmd
    assert "1522:1522" in cmd
    assert "8443:8443" in cmd
    assert "27017:27017" in cmd
    assert "--shm-size" in cmd
    assert "2g" in cmd

    absolute_data_path = str(Path("/dev/shm/oracle-data").resolve())
    assert f"{absolute_data_path}:/u01/data:z" in cmd
    absolute_audit_path = str(Path("/dev/shm/oracle-audit").resolve())
    assert f"{absolute_audit_path}:/u01/app/oracle/audit:z" in cmd
    absolute_oradata_path = str(Path("/dev/shm/oracle-oradata").resolve())
    assert f"{absolute_oradata_path}:/u01/app/oracle/oradata:z" in cmd
    absolute_wallet_path = str(Path(".envs/tns").resolve())
    assert f"{absolute_wallet_path}:/u01/app/oracle/wallets/tls_wallet:z" in cmd

    assert not any("/opt/oracle/scripts/setup" in part for part in cmd)
    assert not any("/opt/oracle/scripts/startup" in part for part in cmd)
    assert not any("/opt/oracle/apex-downloads" in part for part in cmd)

    assert "WORKLOAD_TYPE=ATP" in cmd
    assert f"ADMIN_PASSWORD={DEMO_PASSWORD}" in cmd
    assert f"WALLET_PASSWORD={DEMO_PASSWORD}" in cmd
    assert not any("APP_USER" in part for part in cmd)

    health_index = cmd.index("--health-cmd")
    assert cmd[health_index + 1] == "lsnrctl status | grep -qi 'myatp_low.adb.oraclecloud.com'"

    assert "--privileged" not in cmd
    assert "--cap-add" in cmd
    assert "SYS_ADMIN" in cmd
    assert "--device" in cmd
    assert "/dev/fuse" in cmd

    assert not any("container-entrypoint-initdb.d" in part for part in cmd)
    assert not any("container-entrypoint-startdb.d" in part for part in cmd)


def test_configure_vector_memory_uses_sysdba_when_pool_is_unallocated() -> None:
    """Instance-level vector memory setup should use OS-authenticated SYSDBA."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.run_command.side_effect = [
        (0, "0\n", ""),
        (0, "Vector memory configured\n", ""),
        (0, "536870912\n", ""),
    ]
    db = OracleDatabase(runtime=runtime, config=DatabaseConfig())
    db.wait_for_healthy = MagicMock(return_value=True)  # type: ignore[method-assign]

    db.configure_vector_memory()

    assert runtime.run_command.call_count == 3
    configure_call = runtime.run_command.call_args_list[1]
    assert configure_call.args[0][:4] == ["exec", "oracle-free-db", "bash", "-lc"]
    assert "sqlplus -S / as sysdba" in configure_call.args[0][4]
    assert "ALTER SYSTEM SET vector_memory_size = 512M SCOPE = SPFILE" in configure_call.args[0][4]
    assert "SHUTDOWN IMMEDIATE" in configure_call.args[0][4]
    assert "STARTUP" in configure_call.args[0][4]
    db.wait_for_healthy.assert_called_once_with(timeout=300)
    # Fail-loud re-read confirms the SPFILE change actually took effect.
    recheck_call = runtime.run_command.call_args_list[2]
    assert "V$SGAINFO" in recheck_call.args[0][4]


def test_configure_vector_memory_skips_sysdba_restart_when_pool_exists() -> None:
    """Configured vector memory should not restart the database on every boot."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.run_command.return_value = (0, "536870912\n", "")
    db = OracleDatabase(runtime=runtime, config=DatabaseConfig())
    db.wait_for_healthy = MagicMock()  # type: ignore[method-assign]

    db.configure_vector_memory()

    runtime.run_command.assert_called_once()
    db.wait_for_healthy.assert_not_called()


def test_configure_vector_memory_raises_when_pool_stays_zero() -> None:
    """A failed SYSDBA bounce must fail loudly instead of deferring to ORA-51962."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.run_command.side_effect = [
        (0, "0\n", ""),
        (0, "Vector memory configured\n", ""),
        (0, "0\n", ""),
    ]
    db = OracleDatabase(runtime=runtime, config=DatabaseConfig())
    db.wait_for_healthy = MagicMock(return_value=True)  # type: ignore[method-assign]

    with pytest.raises(ContainerStartError, match=r"still 0 after configuration"):
        db.configure_vector_memory()

    assert runtime.run_command.call_count == 3


def test_start_configures_vector_memory_before_app_schema(tmp_path: Path) -> None:
    """Successful managed startup should run SYSDBA setup before app-user setup."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.return_value = False
    runtime.container_exists.return_value = False
    runtime.run_command.return_value = (0, "abcdef1234567890\n", "")
    config = DatabaseConfig(
        data_location=str(tmp_path / "oracle-data"),
        wallet_location=str(tmp_path / "tns"),
    )
    db = OracleDatabase(runtime=runtime, config=config)
    db.wait_for_healthy = MagicMock(return_value=True)  # type: ignore[method-assign]
    db.configure_vector_memory = MagicMock()  # type: ignore[method-assign]
    db._patch_host_sqlnet_ora = MagicMock()  # type: ignore[method-assign]
    db.initialize_db_users = MagicMock()  # type: ignore[method-assign]

    db.start()

    db.configure_vector_memory.assert_called_once_with()
    db._patch_host_sqlnet_ora.assert_called_once_with()
    db.initialize_db_users.assert_called_once_with()


def test_start_existing_stopped_container_runs_vector_memory_check(tmp_path: Path) -> None:
    """Restarting an already-initialized container must re-verify vector memory.

    The SPFILE pool lives on /dev/shm tmpfs and is lost on host reboot, so the
    every-start path must self-heal without re-running destructive user init.
    """
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.return_value = False
    runtime.container_exists.return_value = True
    runtime.run_command.return_value = (0, "", "")
    config = DatabaseConfig(
        data_location=str(tmp_path / "oracle-data"),
        wallet_location=str(tmp_path / "tns"),
    )
    db = OracleDatabase(runtime=runtime, config=config)
    db.wait_for_healthy = MagicMock(return_value=True)  # type: ignore[method-assign]
    db._exec_sysdba_sql = MagicMock(return_value="536870912\n")  # type: ignore[method-assign]
    db._patch_host_sqlnet_ora = MagicMock()  # type: ignore[method-assign]
    db.initialize_db_users = MagicMock()  # type: ignore[method-assign]

    db.start()

    db._exec_sysdba_sql.assert_called_once_with(VECTOR_MEMORY_CHECK_SQL)
    db._patch_host_sqlnet_ora.assert_called_once_with()
    db.initialize_db_users.assert_not_called()
    runtime.run_command.assert_any_call(["start", "oracle-free-db"])


def test_database_remove_is_idempotent_when_container_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The wipe command should succeed when the container has already been removed."""
    runtime = MagicMock(spec=ContainerRuntime)
    db = MagicMock(spec=OracleDatabase)
    db.remove.side_effect = ContainerNotFoundError("Container 'oracle-free-db' does not exist")

    monkeypatch.setattr("tools.oracle.container.ContainerRuntime", lambda: runtime)
    monkeypatch.setattr("tools.oracle.database.DatabaseConfig.from_env", DatabaseConfig)
    monkeypatch.setattr("tools.oracle.database.OracleDatabase", lambda **_: db)

    result = CliRunner().invoke(database_remove, ["--volumes", "--force", "--yes"])

    assert result.exit_code == 0
    assert "already removed" in result.output


def test_database_start_loads_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The infra start command should honor the env file before reading config."""
    env_file = tmp_path / ".env"
    env_file.write_text(f"DATABASE_PASSWORD=env-secret\nOEE_PASSWORD={OEE_ENV_PASSWORD}\n", encoding="utf-8")
    runtime = MagicMock(spec=ContainerRuntime)
    db = MagicMock(spec=OracleDatabase)
    captured_env: dict[str, str | None] = {}

    def from_env() -> DatabaseConfig:
        import os

        captured_env["database_password"] = os.environ.get("DATABASE_PASSWORD")
        captured_env["oee_password"] = os.environ.get("OEE_PASSWORD")
        return DatabaseConfig()

    monkeypatch.setattr("tools.oracle.container.ContainerRuntime", lambda: runtime)
    monkeypatch.setattr("tools.oracle.database.DatabaseConfig.from_env", from_env)
    monkeypatch.setattr("tools.oracle.database.OracleDatabase", lambda **_: db)

    result = CliRunner().invoke(database_start, ["--env-file", str(env_file)])

    assert result.exit_code == 0
    assert captured_env == {
        "database_password": "env-secret",
        "oee_password": OEE_ENV_PASSWORD,
    }
    db.start.assert_called_once_with(pull=False, recreate=False)


def test_start_raises_when_health_check_times_out(tmp_path: Path) -> None:
    """Startup should fail if the container never becomes ready."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.return_value = False
    runtime.container_exists.return_value = False
    runtime.run_command.return_value = (0, "abcdef1234567890\n", "")
    config = DatabaseConfig(
        data_location=str(tmp_path / "oracle-data"),
        wallet_location=str(tmp_path / "tns"),
    )
    db = OracleDatabase(runtime=runtime, config=config)
    db.wait_for_healthy = MagicMock(return_value=False)  # type: ignore[method-assign]

    with pytest.raises(ContainerStartError, match="health check timed out"):
        db.start()


def test_start_validates_app_password_before_recreating_container(tmp_path: Path) -> None:
    """Invalid app passwords should fail before mutating an existing container."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.return_value = True
    config = DatabaseConfig(
        app_password=INVALID_ORACLE_PROFILE_VALUE,
        data_location=str(tmp_path / "oracle-data"),
        wallet_location=str(tmp_path / "tns"),
    )
    db = OracleDatabase(runtime=runtime, config=config)

    with pytest.raises(ContainerStartError, match=r"DATABASE_PASSWORD.*uppercase"):
        db.start(recreate=True)

    runtime.run_command.assert_not_called()


def test_start_validates_oee_password_before_creating_container(tmp_path: Path) -> None:
    """Invalid OEE passwords should fail before mutating the managed container."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.return_value = False
    runtime.container_exists.return_value = False
    config = DatabaseConfig(
        oee_password=INVALID_ORACLE_PROFILE_VALUE,
        data_location=str(tmp_path / "oracle-data"),
        wallet_location=str(tmp_path / "tns"),
    )
    db = OracleDatabase(runtime=runtime, config=config)

    with pytest.raises(ContainerStartError, match=r"OEE_PASSWORD.*uppercase"):
        db.start()

    runtime.run_command.assert_not_called()


@pytest.mark.parametrize(
    ("app_password", "message"),
    [
        ("Secret1a", "12 to 30"),
        ("AppPassword1", "cannot contain DATABASE_USER"),
        ('SuperSecret1"', "double quote"),
    ],
)
def test_start_validates_app_password_against_autonomous_profile(
    app_password: str,
    message: str,
    tmp_path: Path,
) -> None:
    """Managed ADB app passwords should satisfy the cloud password profile."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.return_value = False
    runtime.container_exists.return_value = False
    config = DatabaseConfig(
        app_password=app_password,
        data_location=str(tmp_path / "oracle-data"),
        wallet_location=str(tmp_path / "tns"),
    )
    db = OracleDatabase(runtime=runtime, config=config)

    with pytest.raises(ContainerStartError, match=message):
        db.start()

    runtime.run_command.assert_not_called()


def test_initialize_db_users_uses_configured_app_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The managed container should create the same app credentials the app uses."""
    cursor = MagicMock()
    cursor.fetchone.return_value = [0]
    cursor_context = MagicMock()
    cursor_context.__enter__.return_value = cursor
    conn = MagicMock()
    conn.cursor.return_value = cursor_context
    oracledb = MagicMock()
    oracledb.connect.return_value = conn
    monkeypatch.setitem(sys.modules, "oracledb", oracledb)

    config = DatabaseConfig(
        app_username="demo_app",
        app_password=DEMO_PASSWORD,
        wallet_location=str(tmp_path / "tns"),
    )
    db = OracleDatabase(runtime=MagicMock(spec=ContainerRuntime), config=config)

    db.initialize_db_users()

    oracledb.connect.assert_called_once()
    assert oracledb.connect.call_args.kwargs["dsn"] == "myatp_medium"
    cursor.execute.assert_has_calls([
        call("SELECT COUNT(*) FROM dba_users WHERE username = :username", username="DEMO_APP"),
        call(f'CREATE USER demo_app IDENTIFIED BY "{DEMO_PASSWORD}" QUOTA UNLIMITED ON DATA'),
        call("GRANT CONNECT, CONSOLE_DEVELOPER, DWROLE, RESOURCE TO demo_app"),
        call("""BEGIN
    ORDS.ENABLE_SCHEMA(
        p_enabled => TRUE,
        p_schema => 'DEMO_APP',
        p_url_mapping_type => 'BASE_PATH',
        p_url_mapping_pattern => 'demo_app',
        p_auto_rest_auth => TRUE
    );
    COMMIT;
END;"""),
        call("ALTER USER demo_app QUOTA UNLIMITED ON DATA"),
        call(f'ALTER USER MPACK_OEE IDENTIFIED BY "{DEMO_PASSWORD}" ACCOUNT UNLOCK'),
    ])
    conn.commit.assert_called_once_with()
