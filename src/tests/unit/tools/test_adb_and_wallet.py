# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for ADB-Free 26ai container lifecycle, wallet export, and connection helpers."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from rich.console import Console
from sqlspec.adapters.oracledb import extract_oracle_wallet_zip as sqlspec_extract_wallet_zip
from tools.oracle.adb import AdbBootstrap, AdbBootstrapConfig
from tools.oracle.connection import ConnectionConfig, ConnectionTester, DeploymentMode, detect_deployment_mode
from tools.oracle.container import ContainerRuntime, RuntimeType
from tools.oracle.database import ContainerFlavor, ContainerStartError, DatabaseConfig, OracleDatabase
from tools.oracle.wallet import WalletConfig, WalletConfigurator, WalletInfo

SAMPLE_TNSNAMES = (
    "myatp_high = (DESCRIPTION=(RETRY_COUNT=20)(RETRY_DELAY=3)"
    "(ADDRESS=(PROTOCOL=tcps)(PORT=1522)(HOST=adb-container-internal))"
    "(CONNECT_DATA=(SERVICE_NAME=myatp_high.adb.oraclecloud.com))"
    "(SECURITY=(SSL_SERVER_DN_MATCH=no)))\n"
    "myatp_low = (DESCRIPTION=(RETRY_COUNT=20)(RETRY_DELAY=3)"
    "(ADDRESS=(PROTOCOL=tcps)(PORT=1522)(HOST=adb-container-internal))"
    "(CONNECT_DATA=(SERVICE_NAME=myatp_low.adb.oraclecloud.com))"
    "(SECURITY=(SSL_SERVER_DN_MATCH=no)))\n"
)

SAMPLE_SQLNET = (
    'WALLET_LOCATION = (SOURCE = (METHOD = file) (METHOD_DATA = (DIRECTORY="?/network/admin")))\n'
    "SSL_SERVER_DN_MATCH=no\n"
)


def _make_console() -> tuple[Console, io.StringIO]:
    """Build an in-memory Rich console and backing buffer for output assertions."""
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None, width=120)
    return console, buffer


def _populate_wallet_files(target: Path) -> None:
    """Write minimal mTLS wallet files into a directory."""
    target.mkdir(parents=True, exist_ok=True)
    (target / "tnsnames.ora").write_text(SAMPLE_TNSNAMES, encoding="utf-8")
    (target / "sqlnet.ora").write_text(SAMPLE_SQLNET, encoding="utf-8")
    (target / "cwallet.sso").write_bytes(b"sso-placeholder")
    (target / "ewallet.pem").write_text(
        "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n", encoding="utf-8"
    )


def test_database_config_defaults_to_adb_free_and_supports_free_flavor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DatabaseConfig defaults to adb-free:latest-26ai and switches cleanly to free flavor."""
    for key in (
        "ORACLE_CONTAINER_FLAVOR",
        "ORACLE_IMAGE",
        "ORACLE_CONTAINER_NAME",
        "DATABASE_PORT",
        "ORACLE26AI_PORT",
        "ORACLE23AI_PORT",
        "WALLET_LOCATION",
        "ORACLE_HTTPS_PORT",
    ):
        monkeypatch.delenv(key, raising=False)

    adb_cfg = DatabaseConfig.from_env()
    assert adb_cfg.flavor == ContainerFlavor.ADB_FREE
    assert adb_cfg.image == "container-registry.oracle.com/database/adb-free:latest-26ai"
    assert adb_cfg.container_name == "cymbal-adb-free"
    assert adb_cfg.https_port == 8443
    assert adb_cfg.service_name == "myatp_low"
    assert adb_cfg.wallet_dir == Path(".envs/tns")
    assert adb_cfg.data_volume_name == "cymbal-adb-data"

    monkeypatch.setenv("ORACLE_CONTAINER_FLAVOR", "free")
    free_cfg = DatabaseConfig.from_env()
    assert free_cfg.flavor == ContainerFlavor.FREE
    assert free_cfg.image == "gvenzl/oracle-free:latest"
    assert free_cfg.container_name == "oracle-free-db"
    assert free_cfg.service_name == "freepdb1"
    assert free_cfg.data_volume_name == "oracle-db-data"


def test_container_exists_invokes_ps_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ContainerRuntime.container_exists runs `ps -a` once and matches exact container names."""
    monkeypatch.setattr(ContainerRuntime, "detect_runtime", staticmethod(lambda: RuntimeType.DOCKER))
    runtime = ContainerRuntime()
    calls: list[list[str]] = []

    def fake_run_command(args: list[str], **_kwargs: Any) -> tuple[int, str, str]:
        calls.append(args)
        return (0, "cymbal-adb-free-other\ncymbal-adb-free\n", "")

    monkeypatch.setattr(runtime, "run_command", fake_run_command)

    assert runtime.container_exists("cymbal-adb-free") is True
    assert len(calls) == 1
    assert runtime.container_exists("cymbal-adb") is False
    assert len(calls) == 2


def test_oracle_database_refuses_adb_free_start_when_legacy_free_holds_port_1521() -> None:
    """Verify starting cymbal-adb-free fails fast with an actionable wipe command when oracle-free-db is running."""
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.container_running.side_effect = lambda name: name == "oracle-free-db"
    runtime.container_exists.return_value = False
    console, _ = _make_console()
    db = OracleDatabase(
        runtime=runtime, config=DatabaseConfig(flavor=ContainerFlavor.ADB_FREE, host_port=1521), console=console
    )

    with pytest.raises(ContainerStartError, match=r"manage\.py infra wipe --volumes --force --yes"):
        db.start()


def test_adb_free_build_run_command_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify adb-free container run arguments include ports, ATP workload, FUSE capabilities, and host-gateway."""
    monkeypatch.setattr("tools.oracle.database.sys.platform", "linux")
    runtime = MagicMock(spec=ContainerRuntime)
    runtime.get_runtime_type.return_value = RuntimeType.DOCKER
    cfg = DatabaseConfig(
        flavor=ContainerFlavor.ADB_FREE,
        host_port=1521,
        tls_host_port=1522,
        https_port=8443,
        wallet_password="WalletPassword1",
        oracle_password="AdminPassword1",
    )
    console, _ = _make_console()
    db = OracleDatabase(runtime=runtime, config=cfg, console=console)

    cmd = db.build_run_command()
    joined = " ".join(cmd)

    assert "1521:1522" in cmd
    assert "1522:1522" in cmd
    assert "8443:8443" in cmd
    assert "cymbal-adb-data:/u01/data" in cmd
    assert "WORKLOAD_TYPE=ATP" in cmd
    assert "ENABLE_ARCHIVE_LOG=FALSE" in cmd
    assert "WALLET_PASSWORD=WalletPassword1" in cmd
    assert "ADMIN_PASSWORD=AdminPassword1" in cmd
    assert "--cap-add" in cmd
    assert "SYS_ADMIN" in cmd
    assert "--device" in cmd
    assert "/dev/fuse" in cmd
    assert "--add-host=host.docker.internal:host-gateway" in joined
    assert cmd[-1] == "container-registry.oracle.com/database/adb-free:latest-26ai"


def test_adb_bootstrap_export_wallet_from_container_and_zip(tmp_path: Path) -> None:
    """Verify AdbBootstrap exports wallet files, normalizes localhost in tnsnames.ora, and supports .zip bundles."""
    wallet_dir = tmp_path / "tns"
    runtime = MagicMock(spec=ContainerRuntime)

    def fake_copy(container_name: str, src_path: str, dest_path: Path) -> None:
        assert container_name == "cymbal-adb-free"
        assert src_path.startswith("/u01/app/oracle/wallets/tls_wallet")
        _populate_wallet_files(dest_path)

    runtime.copy_from_container.side_effect = fake_copy
    console, _ = _make_console()
    bootstrap = AdbBootstrap(
        runtime=runtime,
        config=AdbBootstrapConfig(wallet_dir=wallet_dir, wallet_password="WalletPassword1"),
        console=console,
    )

    exported_dir, services = bootstrap.export_wallet()
    assert exported_dir == wallet_dir.resolve()
    assert "myatp_low" in services
    rewritten_tns = (wallet_dir / "tnsnames.ora").read_text(encoding="utf-8")
    assert "(HOST=localhost)" in rewritten_tns
    assert "adb-container-internal" not in rewritten_tns

    zip_source = tmp_path / "Wallet_MYATP.zip"
    zip_target = tmp_path / "zip_tns"
    with zipfile.ZipFile(zip_source, "w") as zf:
        zf.writestr("tnsnames.ora", SAMPLE_TNSNAMES)
        zf.writestr("sqlnet.ora", SAMPLE_SQLNET)
        zf.writestr("cwallet.sso", b"sso-placeholder")
        zf.writestr("ewallet.pem", "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n")

    zip_bootstrap = AdbBootstrap(
        runtime=runtime,
        config=AdbBootstrapConfig(wallet_dir=zip_target, wallet_password="WalletPassword1"),
        console=console,
    )
    extracted_dir, zip_services = zip_bootstrap.export_wallet(source=zip_source)
    assert extracted_dir == zip_target.resolve()
    assert "myatp_low" in zip_services
    assert "(HOST=localhost)" in (zip_target / "tnsnames.ora").read_text(encoding="utf-8")


def test_adb_bootstrap_provision_schema_and_workspace_executes_idempotent_plsql(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify ADMIN provisioning grants required roles, DBMS_CLOUD_AI, ORDS schema, and COFFEE workspace."""
    wallet_dir = tmp_path / "tns"
    _populate_wallet_files(wallet_dir)
    executed: list[tuple[str, dict[str, Any]]] = []

    mock_cursor = MagicMock()

    def record_execute(sql: str, parameters: dict[str, Any] | None = None, **kw: Any) -> None:
        params = dict(parameters or {})
        params.update(kw)
        executed.append((sql, params))

    mock_cursor.execute.side_effect = record_execute
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None

    connect_calls: list[dict[str, Any]] = []

    def fake_connect(**kwargs: Any) -> Any:
        connect_calls.append(kwargs)
        return mock_conn

    monkeypatch.setattr("tools.oracle.adb.oracledb.connect", fake_connect)
    runtime = MagicMock(spec=ContainerRuntime)
    console, _ = _make_console()
    bootstrap = AdbBootstrap(
        runtime=runtime,
        config=AdbBootstrapConfig(
            wallet_dir=wallet_dir,
            wallet_password="WalletPassword1",
            admin_password="AdminPassword1",
            app_user="app",
            app_password="AppPassword1",
            workspace_name="COFFEE",
        ),
        console=console,
    )

    bootstrap.provision_schema_and_workspace()

    assert len(connect_calls) == 1
    assert connect_calls[0]["user"] == "ADMIN"
    assert connect_calls[0]["dsn"] == "myatp_low"
    combined_sql = "\n".join(sql for sql, _ in executed)
    assert "CONSOLE_DEVELOPER" in combined_sql
    assert "DWROLE" in combined_sql
    assert "DB_DEVELOPER_ROLE" in combined_sql
    assert "UNLIMITED TABLESPACE" in combined_sql
    assert "DBMS_CLOUD_AI" in combined_sql
    assert "ORDS.ENABLE_SCHEMA" in combined_sql
    assert "APEX_INSTANCE_ADMIN.ADD_WORKSPACE" in combined_sql
    assert "p_change_password_on_first_use => FALSE" in combined_sql
    assert "p_change_on_first_use" not in combined_sql
    assert "-1031" in combined_sql
    assert "-2030" in combined_sql
    mock_conn.commit.assert_called()


def test_wallet_configurator_prints_database_user_and_extracts_via_sqlspec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify WalletConfigurator defaults dest_dir to .envs/tns, forwards WALLET_PASSWORD, and prints DATABASE_USER."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WALLET_PASSWORD", "EnvWalletPass1")
    recorded_passwords: list[str | None] = []

    def spy_extract(source: Path, target_dir: Path | None = None, *, wallet_password: str | None = None) -> Path:
        recorded_passwords.append(wallet_password)
        return sqlspec_extract_wallet_zip(source, target_dir, wallet_password=wallet_password)

    monkeypatch.setattr("tools.oracle.wallet.extract_oracle_wallet_zip", spy_extract)

    console, buffer = _make_console()
    configurator = WalletConfigurator(config=WalletConfig(), console=console)

    zip_source = tmp_path / "Wallet_DEMO.zip"
    with zipfile.ZipFile(zip_source, "w") as zf:
        zf.writestr("tnsnames.ora", SAMPLE_TNSNAMES)
        zf.writestr("sqlnet.ora", SAMPLE_SQLNET)
        zf.writestr("cwallet.sso", b"sso-placeholder")
        zf.writestr("ewallet.pem", "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n")

    out_dir = configurator.extract_wallet(zip_source)
    assert out_dir == (tmp_path / ".envs" / "tns").resolve()
    assert recorded_passwords == ["EnvWalletPass1"]
    services = configurator.parse_tnsnames(out_dir)
    assert services == ["myatp_high", "myatp_low"]

    info = WalletInfo(wallet_dir=out_dir, has_cwallet=True, has_tnsnames=True, has_sqlnet=True, services=services)
    configurator.display_configuration_help(info, {"WALLET_LOCATION": str(out_dir)})
    rendered = buffer.getvalue()
    assert "DATABASE_USER=<your_username>" in rendered
    assert "DATABASE_USERNAME" not in rendered


def test_connection_tester_passes_timeout_and_defaults_managed_tns_wallet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify ConnectionConfig auto-detects .envs/tns in managed mode and ConnectionTester forwards tcp_connect_timeout."""
    monkeypatch.chdir(tmp_path)
    _populate_wallet_files(tmp_path / ".envs" / "tns")
    for key in (
        "WALLET_LOCATION",
        "TNS_ADMIN",
        "WALLET_PASSWORD",
        "DATABASE_URL",
        "DATABASE_HOST",
        "DATABASE_DEPLOYMENT_MODE",
        "ORACLE_CONTAINER_FLAVOR",
    ):
        monkeypatch.delenv(key, raising=False)

    cfg = ConnectionConfig.from_env()
    assert cfg.mode == DeploymentMode.MANAGED
    assert cfg.wallet_location == Path(".envs/tns")
    assert cfg.service_name == "myatp_low"

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("OK",)
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None

    mock_conn = MagicMock()
    mock_conn.version = "23.26.0.0.0"
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None

    connect_calls: list[dict[str, Any]] = []

    def fake_connect(**kwargs: Any) -> Any:
        connect_calls.append(kwargs)
        return mock_conn

    monkeypatch.setattr("tools.oracle.connection.oracledb.connect", fake_connect)
    console, _ = _make_console()
    result = ConnectionTester(console=console).test(cfg, timeout=7, display=False)

    assert result.success is True
    assert len(connect_calls) == 1
    assert connect_calls[0]["dsn"] == "myatp_low"
    assert connect_calls[0]["tcp_connect_timeout"] == 7.0


def test_connection_config_respects_database_deployment_mode_managed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DATABASE_DEPLOYMENT_MODE=managed overrides DATABASE_URL external inference."""
    monkeypatch.setenv("DATABASE_URL", "myatp_low")
    monkeypatch.setenv("WALLET_LOCATION", ".envs/tns")
    monkeypatch.setenv("WALLET_PASSWORD", "SuperSecret1")
    monkeypatch.setenv("DATABASE_USER", "app")
    monkeypatch.setenv("DATABASE_PASSWORD", "SuperSecret1")
    monkeypatch.delenv("DATABASE_HOST", raising=False)
    monkeypatch.delenv("DATABASE_DEPLOYMENT_MODE", raising=False)

    assert detect_deployment_mode() == DeploymentMode.EXTERNAL
    external_cfg = ConnectionConfig.from_env()
    assert external_cfg.mode == DeploymentMode.EXTERNAL
    assert external_cfg.get_dsn() == "myatp_low"

    monkeypatch.setenv("DATABASE_DEPLOYMENT_MODE", "managed")
    assert detect_deployment_mode() == DeploymentMode.MANAGED
    managed_cfg = ConnectionConfig.from_env()
    assert managed_cfg.mode == DeploymentMode.MANAGED
    assert managed_cfg.service_name == "myatp_low"
    assert managed_cfg.get_dsn() == "myatp_low"
