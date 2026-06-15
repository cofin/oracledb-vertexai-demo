# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the local gvenzl Oracle container configuration and lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner
from tools.oracle.cli.database import database_remove, database_start
from tools.oracle.container import ContainerRuntime
from tools.oracle.database import (
    DEFAULT_IMAGE,
    ContainerNotFoundError,
    ContainerStartError,
    DatabaseConfig,
    OracleDatabase,
)

if TYPE_CHECKING:
    from pathlib import Path

DEMO_PASSWORD = "SuperSecret1"  # noqa: S105
CONTAINER_NAME = "oracle-free-db"


def _database(runtime: MagicMock, **config_kwargs: object) -> OracleDatabase:
    config = DatabaseConfig(**config_kwargs)  # type: ignore[arg-type]
    return OracleDatabase(runtime=runtime, config=config)


def test_database_config_defaults() -> None:
    """The local container defaults to the gvenzl image and the app user."""
    config = DatabaseConfig()
    assert config.image == DEFAULT_IMAGE == "gvenzl/oracle-free:latest"
    assert config.container_name == CONTAINER_NAME
    assert config.app_user == "app"
    assert config.host_port == 1521
    assert config.container_port == 1521
    assert config.data_volume_name == "oracle-db-data"


def test_database_config_from_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """from_env honours the image, credentials, and port overrides."""
    monkeypatch.setenv("ORACLE_IMAGE", "container-registry.oracle.com/database/adb-free:latest-26ai")
    monkeypatch.setenv("DATABASE_USER", "barista")
    monkeypatch.setenv("DATABASE_PASSWORD", "Roast1234")
    monkeypatch.setenv("DATABASE_PORT", "1599")

    config = DatabaseConfig.from_env()

    assert config.image == "container-registry.oracle.com/database/adb-free:latest-26ai"
    assert config.app_user == "barista"
    assert config.app_user_password == "Roast1234"  # noqa: S105
    assert config.host_port == 1599


def test_build_run_command_contains_gvenzl_flags() -> None:
    """The run command wires gvenzl env vars, the persistent volume, and health check."""
    db = _database(MagicMock(spec=ContainerRuntime), app_user_password=DEMO_PASSWORD)
    cmd = db._build_run_command()

    assert cmd[0] == "run"
    assert "-d" in cmd
    flat = " ".join(cmd)
    assert "APP_USER=app" in cmd
    assert f"APP_USER_PASSWORD={DEMO_PASSWORD}" in cmd
    assert any(c.startswith("ORACLE_PASSWORD=") for c in cmd)
    assert "oracle-db-data:/opt/oracle/oradata" in cmd
    assert "healthcheck.sh" in cmd
    # Image is always the final argument.
    assert cmd[-1] == DEFAULT_IMAGE
    # No adb-free / wallet / mTLS artifacts remain.
    assert "WALLET_PASSWORD" not in flat
    assert "SYS_ADMIN" not in flat


def test_build_run_command_mounts_sysdba_hook_scripts() -> None:
    """on_init/on_startup scripts mount into the gvenzl SYSDBA hook directories."""
    db = _database(MagicMock(spec=ContainerRuntime))
    flat = " ".join(db._build_run_command())

    assert "00_configure_vector_memory.sql:/container-entrypoint-initdb.d/00_configure_vector_memory.sql:z" in flat
    assert "db_init.sql:/container-entrypoint-initdb.d/db_init.sql:z" in flat
    assert "00_verify_vector_memory.sql:/container-entrypoint-startdb.d/00_verify_vector_memory.sql:z" in flat


def test_start_creates_container_when_absent(tmp_path: Path) -> None:
    """A fresh start builds the run command and waits for health."""
    del tmp_path
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.return_value = False
    runtime.container_exists.return_value = False
    runtime.volume_exists.return_value = True
    runtime.run_command.return_value = (0, "abcdef1234567890\n", "")
    db = _database(runtime)
    db.wait_for_healthy = MagicMock(return_value=True)  # type: ignore[method-assign]

    db.start()

    db.wait_for_healthy.assert_called_once_with(timeout=300)
    run_calls = [c.args[0] for c in runtime.run_command.call_args_list]
    assert any(call[0] == "run" for call in run_calls)


def test_start_existing_stopped_container_starts_and_returns() -> None:
    """Restarting a stopped container starts it without recreating."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.return_value = False
    runtime.container_exists.return_value = True
    runtime.run_command.return_value = (0, "", "")
    db = _database(runtime)
    db._build_run_command = MagicMock()  # type: ignore[method-assign]

    db.start()

    runtime.run_command.assert_called_once_with(["start", CONTAINER_NAME])
    db._build_run_command.assert_not_called()


def test_start_reuses_already_running_container_without_recreate() -> None:
    """Starting an already-running container without --recreate reuses it (idempotent)."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.return_value = True
    db = _database(runtime)

    db.start()  # idempotent: reuses the running container instead of raising

    runtime.run_command.assert_not_called()


def test_start_raises_when_health_check_times_out() -> None:
    """Startup fails loudly if the container never becomes healthy."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.return_value = False
    runtime.container_exists.return_value = False
    runtime.volume_exists.return_value = True
    runtime.run_command.return_value = (0, "abcdef1234567890\n", "")
    db = _database(runtime)
    db.wait_for_healthy = MagicMock(return_value=False)  # type: ignore[method-assign]

    with pytest.raises(ContainerStartError, match="health check timed out"):
        db.start()


def test_get_connection_info_targets_freepdb1() -> None:
    """Connection info points at the gvenzl FREEPDB1 service as the app user."""
    db = _database(MagicMock(spec=ContainerRuntime), app_user="app", app_user_password=DEMO_PASSWORD, host_port=1521)
    info = db.get_connection_info()

    assert info["service_name"] == "freepdb1"
    assert info["dsn"] == "localhost:1521/freepdb1"
    assert info["user"] == "app"


def test_remove_removes_volume_when_requested() -> None:
    """remove(volumes=True) drops the named data volume."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_exists.return_value = True
    runtime.volume_exists.return_value = True
    db = _database(runtime)

    db.remove(volumes=True, force=True)

    runtime.run_command.assert_any_call(["volume", "rm", "oracle-db-data"])


def test_database_remove_is_idempotent_when_container_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The remove command succeeds when the container has already been removed."""
    runtime = MagicMock(spec=ContainerRuntime)
    db = MagicMock(spec=OracleDatabase)
    db.remove.side_effect = ContainerNotFoundError(f"Container '{CONTAINER_NAME}' does not exist")

    monkeypatch.setattr("tools.oracle.container.ContainerRuntime", lambda: runtime)
    monkeypatch.setattr("tools.oracle.database.DatabaseConfig.from_env", DatabaseConfig)
    monkeypatch.setattr("tools.oracle.database.OracleDatabase", lambda **_: db)

    result = CliRunner().invoke(database_remove, ["--volumes", "--force", "--yes"])

    assert result.exit_code == 0
    assert "already removed" in result.output


def test_database_start_loads_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The start command honours the env file before reading config."""
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_PASSWORD=env-secret\n", encoding="utf-8")
    runtime = MagicMock(spec=ContainerRuntime)
    db = MagicMock(spec=OracleDatabase)
    captured: dict[str, str | None] = {}

    def from_env() -> DatabaseConfig:
        import os

        captured["database_password"] = os.environ.get("DATABASE_PASSWORD")
        return DatabaseConfig()

    monkeypatch.setattr("tools.oracle.container.ContainerRuntime", lambda: runtime)
    monkeypatch.setattr("tools.oracle.database.DatabaseConfig.from_env", from_env)
    monkeypatch.setattr("tools.oracle.database.OracleDatabase", lambda **_: db)

    result = CliRunner().invoke(database_start, ["--env-file", str(env_file)])

    assert result.exit_code == 0
    assert captured["database_password"] == "env-secret"  # noqa: S105
    db.start.assert_called_once_with(pull=False, recreate=False)
