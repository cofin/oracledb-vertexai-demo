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
from tools.oracle.database import ContainerNotFoundError, ContainerStartError, DatabaseConfig, OracleDatabase

DEMO_PASSWORD = "SuperSecret1"  # noqa: S105
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
    env_file.write_text("DATABASE_PASSWORD=env-secret\n", encoding="utf-8")
    runtime = MagicMock(spec=ContainerRuntime)
    db = MagicMock(spec=OracleDatabase)
    captured_password: dict[str, str | None] = {}

    def from_env() -> DatabaseConfig:
        import os

        captured_password["value"] = os.environ.get("DATABASE_PASSWORD")
        return DatabaseConfig()

    monkeypatch.setattr("tools.oracle.container.ContainerRuntime", lambda: runtime)
    monkeypatch.setattr("tools.oracle.database.DatabaseConfig.from_env", from_env)
    monkeypatch.setattr("tools.oracle.database.OracleDatabase", lambda **_: db)

    result = CliRunner().invoke(database_start, ["--env-file", str(env_file)])

    assert result.exit_code == 0
    assert captured_password["value"] == "env-secret"
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

    cursor.execute.assert_has_calls([
        call("SELECT COUNT(*) FROM dba_users WHERE username = :username", username="DEMO_APP"),
        call(f'CREATE USER demo_app IDENTIFIED BY "{DEMO_PASSWORD}"'),
        call("GRANT CONNECT, RESOURCE, DB_DEVELOPER_ROLE TO demo_app"),
        call("GRANT UNLIMITED TABLESPACE TO demo_app"),
    ])
    conn.commit.assert_called_once_with()
