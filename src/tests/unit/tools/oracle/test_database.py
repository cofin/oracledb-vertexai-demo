# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Oracle database container configuration and command builder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from tools.oracle.database import DatabaseConfig, OracleDatabase
from tools.oracle.container import ContainerRuntime


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
    assert config.admin_password == "SuperSecret1"
    assert config.wallet_password == "SuperSecret1"
    assert config.wallet_location == ".envs/tns"


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

    absolute_data_path = str(Path("/var/tmp/oracle-data").resolve())
    assert f"{absolute_data_path}:/u01/data:z" in cmd

    absolute_audit_path = str(Path("/var/tmp/oracle-audit").resolve())
    assert f"{absolute_audit_path}:/u01/app/oracle/audit:z" in cmd

    absolute_oradata_path = str(Path("/var/tmp/oracle-oradata").resolve())
    assert f"{absolute_oradata_path}:/u01/app/oracle/oradata:z" in cmd
    absolute_wallet_path = str(Path(".envs/tns").resolve())
    assert f"{absolute_wallet_path}:/u01/app/oracle/wallets/tls_wallet:z" in cmd

    assert "ADMIN_PASSWORD=SuperSecret1" in cmd
    assert "WALLET_PASSWORD=SuperSecret1" in cmd
    assert not any("APP_USER" in part for part in cmd)

    assert "--privileged" in cmd
    assert "--cap-add" in cmd
    assert "SYS_ADMIN" in cmd
    assert "--device" in cmd
    assert "/dev/fuse" in cmd

    assert not any("container-entrypoint-initdb.d" in part for part in cmd)
    assert not any("container-entrypoint-startdb.d" in part for part in cmd)
