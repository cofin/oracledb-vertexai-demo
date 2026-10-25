# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for wallet-aware APEXlang, APEX OpenAPI catalog export, and infra CLI commands."""

from __future__ import annotations

import os
import ssl
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import manage
import msgspec
import pytest
from click.testing import CliRunner
from tools.oracle import apex_catalog
from tools.oracle.apex_catalog import build_apex_catalog, export_apex_openapi_catalog, export_current_app_apex_catalog
from tools.oracle.apex_lang import ApexLang, ApexLangConfig, ApexLangResult
from tools.oracle.container import ContainerRuntime
from tools.oracle.database import ContainerFlavor, ContainerStatus, DatabaseConfig, OracleDatabase
from tools.oracle.sqlcl_installer import SQLclCapabilityStatus, SQLclInstaller

from app.utils.serialization import decode_json, format_json

SAMPLE_OPENAPI_DOCUMENT: dict[str, Any] = {
    "openapi": "3.1.0",
    "info": {"title": "Cymbal Coffee API", "version": "0.3.1"},
    "paths": {
        "/health": {
            "get": {
                "tags": ["System"],
                "responses": {
                    "200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/HealthOut"}}}}
                },
            }
        },
        "/api/apex": {"get": {"tags": ["APEX REST Catalog"], "responses": {"200": {"description": "Root index"}}}},
        "/api/apex/products": {
            "get": {
                "tags": ["APEX Products"],
                "responses": {
                    "200": {
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApexProductPage"}}}
                    }
                },
            }
        },
        "/api/apex/ai": {"get": {"tags": ["APEX AI"], "responses": {"200": {"description": "AI index"}}}},
        "/api/apex/ai/v1/chat/completions": {
            "post": {
                "tags": ["APEX AI"],
                "requestBody": {
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/OpenAIChatRequest"}}}
                },
                "responses": {"200": {"description": "Completion"}},
            }
        },
    },
    "components": {
        "schemas": {
            "ApexProductPage": {
                "type": "object",
                "properties": {"items": {"type": "array", "items": {"$ref": "#/components/schemas/ApexProductItem"}}},
            },
            "ApexProductItem": {"type": "object", "properties": {"roast": {"$ref": "#/components/schemas/RoastLevel"}}},
            "RoastLevel": {"type": "string", "enum": ["light", "medium", "dark"]},
            "OpenAIChatRequest": {"type": "object", "properties": {"model": {"type": "string"}}},
            "HealthOut": {"type": "object", "properties": {"status": {"type": "string"}}},
        }
    },
}


class _FakeHTTPSResponse(msgspec.Struct, frozen=True, gc=False):
    """Minimal HTTPResponse double for local ORDS HTTPS probe tests."""

    status: int = 200


class _FakeSubprocessResult(msgspec.Struct, frozen=True, gc=False):
    """Minimal CompletedProcess double for SQLcl subprocess tests."""

    args: list[str]
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class _FakeHTTPSConnection:
    """Minimal HTTPSConnection double recording target host, port, SSL context, and path."""

    calls: list[dict[str, Any]] = []
    next_status: int = 200

    def __init__(
        self, host: str, port: int | None = None, *, timeout: float | None = None, context: ssl.SSLContext | None = None
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.requested_method: str | None = None
        self.requested_path: str | None = None
        self.closed = False

    def request(self, method: str, url: str, **_kwargs: Any) -> None:
        """Record the outbound HTTP request."""
        self.requested_method = method
        self.requested_path = url
        self.calls.append({
            "host": self.host,
            "port": self.port,
            "timeout": self.timeout,
            "context": self.context,
            "method": method,
            "url": url,
        })

    def getresponse(self) -> _FakeHTTPSResponse:
        """Return the configured status code."""
        return _FakeHTTPSResponse(status=self.next_status)

    def close(self) -> None:
        """Mark the fake connection closed."""
        self.closed = True


def _build_capable_installer(sql_bin: Path) -> MagicMock:
    """Build a mocked SQLclInstaller that reports APEXlang 26.1.2+ capability."""
    installer = MagicMock(spec=SQLclInstaller)
    installer.apexlang_status.return_value = SQLclCapabilityStatus(
        installed=True, capable=True, version="26.1.2", minimum="26.1.2", message="SQLcl 26.1.2 supports APEXlang"
    )
    installer.sql_path.return_value = sql_bin
    return installer


def test_apex_lang_config_from_env_wallet_and_free_modes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify ApexLangConfig uses slots and resolves wallet vs EasyConnect settings from env."""
    wallet_dir = tmp_path / "tns"
    monkeypatch.setenv("WALLET_LOCATION", str(wallet_dir))
    monkeypatch.setenv("DATABASE_URL", "myatp_low")
    monkeypatch.setenv("DATABASE_USER", "app")
    monkeypatch.setenv("DATABASE_PASSWORD", "WalletSecret1")
    monkeypatch.delenv("ORACLE_CONTAINER_FLAVOR", raising=False)

    wallet_cfg = ApexLangConfig.from_env()
    assert hasattr(wallet_cfg, "__slots__")
    assert not hasattr(wallet_cfg, "__dict__")
    assert wallet_cfg.wallet_location == wallet_dir
    assert wallet_cfg.tns_alias == "myatp_low"
    assert wallet_cfg.user == "app"
    assert wallet_cfg.password == "WalletSecret1"

    result_obj = ApexLangResult(command="apex validate", target_path=tmp_path, stdout="", stderr="")
    assert hasattr(result_obj, "__slots__")
    assert not hasattr(result_obj, "__dict__")

    monkeypatch.delenv("WALLET_LOCATION", raising=False)
    monkeypatch.delenv("TNS_ADMIN", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_HOST", raising=False)
    monkeypatch.setenv("ORACLE_CONTAINER_FLAVOR", "free")
    monkeypatch.setenv("DATABASE_PORT", "1525")

    free_cfg = ApexLangConfig.from_env()
    assert free_cfg.wallet_location is None
    assert free_cfg.tns_alias is None
    assert free_cfg.port == 1525
    assert free_cfg.service_name == "freepdb1"


def test_apex_lang_connect_line_and_subprocess_tns_admin_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify ApexLang formats wallet TNS vs EasyConnect lines and injects TNS_ADMIN into SQLcl env."""
    wallet_dir = tmp_path / "wallet_tns"
    wallet_dir.mkdir(parents=True, exist_ok=True)
    sql_bin = tmp_path / "sql"
    sql_bin.write_text("", encoding="utf-8")
    installer = _build_capable_installer(sql_bin)

    recorded_calls: list[dict[str, Any]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> _FakeSubprocessResult:
        recorded_calls.append({"cmd": cmd, **kwargs})
        return _FakeSubprocessResult(args=cmd, returncode=0, stdout="Exported\n", stderr="")

    monkeypatch.setattr("tools.oracle.apex_lang.subprocess.run", fake_run)

    wallet_apex = ApexLang(
        installer=installer,
        config=ApexLangConfig(
            src_root=tmp_path / "apex_src",
            user="app",
            password='Sec"ret1',
            wallet_location=wallet_dir,
            tns_alias="myatp_low",
        ),
    )
    assert wallet_apex._connect_line() == 'connect app/"Sec""ret1"@myatp_low'

    wallet_apex.export(app_id=100, alias="cymbal-coffee-ops")
    assert len(recorded_calls) == 1
    assert recorded_calls[0]["cmd"] == [str(sql_bin), "-S", "/nolog"]
    assert recorded_calls[0]["input"].startswith('connect app/"Sec""ret1"@myatp_low\napex export ')
    assert recorded_calls[0]["env"]["TNS_ADMIN"] == str(wallet_dir.resolve())

    easy_apex = ApexLang(
        installer=installer,
        config=ApexLangConfig(
            src_root=tmp_path / "apex_src",
            host="db.internal",
            port=1521,
            service_name="freepdb1",
            user="app",
            password="EasySecret1",
            wallet_location=None,
            tns_alias=None,
        ),
    )
    easy_line = easy_apex._connect_line()
    assert "@//db.internal:1521/freepdb1" in easy_line
    assert easy_line.startswith("connect app/")

    easy_apex.export(app_id=101, alias="cymbal-coffee-ops")
    assert len(recorded_calls) == 2
    assert recorded_calls[1]["env"] is None


def test_build_apex_catalog_defaults_to_host_docker_internal_and_excludes_ai_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify build_apex_catalog defaults to host.docker.internal:8000, filters /api/apex/ai/*, and keeps transitive refs."""
    for env_key in ("APP_URL", "PORT", "LITESTAR_PORT", "LITESTAR_HOST"):
        monkeypatch.delenv(env_key, raising=False)

    catalog = build_apex_catalog(SAMPLE_OPENAPI_DOCUMENT)
    assert catalog["servers"][0]["url"] == "http://host.docker.internal:8000"
    assert sorted(catalog["paths"]) == ["/api/apex", "/api/apex/products"]
    assert sorted(catalog["components"]["schemas"]) == ["ApexProductItem", "ApexProductPage", "RoastLevel"]
    assert catalog["tags"] == [{"name": "APEX Products"}, {"name": "APEX REST Catalog"}]

    monkeypatch.setenv("PORT", "9090")
    port_catalog = build_apex_catalog(SAMPLE_OPENAPI_DOCUMENT)
    assert port_catalog["servers"][0]["url"] == "http://host.docker.internal:9090"

    monkeypatch.setenv("APP_URL", "https://coffee.example.run.app/")
    app_url_catalog = build_apex_catalog(SAMPLE_OPENAPI_DOCUMENT)
    assert app_url_catalog["servers"][0]["url"] == "https://coffee.example.run.app"

    explicit_catalog = build_apex_catalog(SAMPLE_OPENAPI_DOCUMENT, server_url="https://custom.example.com/")
    assert explicit_catalog["servers"][0]["url"] == "https://custom.example.com"


def test_export_apex_openapi_catalog_formats_via_central_serializer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify export_apex_openapi_catalog serializes output through app.utils.serialization.format_json."""
    format_calls: list[Any] = []

    def spy_format_json(value: Any, *, indent: int = 2) -> str:
        format_calls.append(value)
        return format_json(value, indent=indent)

    monkeypatch.setattr(apex_catalog, "format_json", spy_format_json)
    output_file = tmp_path / "generated" / "apex-catalog.openapi.json"

    written = export_apex_openapi_catalog(
        SAMPLE_OPENAPI_DOCUMENT, output_path=output_file, server_url="http://host.docker.internal:8000"
    )

    assert written == output_file
    assert len(format_calls) == 1
    raw_text = output_file.read_text(encoding="utf-8")
    assert raw_text.endswith("\n")
    decoded = decode_json(raw_text)
    assert decoded["servers"][0]["url"] == "http://host.docker.internal:8000"
    assert "/api/apex/ai/v1/chat/completions" not in decoded["paths"]


def test_export_current_app_apex_catalog_preserves_container_host_before_app_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify export_current_app_apex_catalog resolves host.docker.internal before create_app mutates APP_URL."""
    for env_key in ("APEX_CATALOG_SERVER_URL", "APP_URL", "PORT", "LITESTAR_PORT"):
        monkeypatch.delenv(env_key, raising=False)

    def fake_current_app_openapi() -> dict[str, Any]:
        os.environ["APP_URL"] = "http://localhost:8000"
        return SAMPLE_OPENAPI_DOCUMENT

    monkeypatch.setattr(apex_catalog, "_current_app_openapi_document", fake_current_app_openapi)
    output_file = tmp_path / "catalog.json"

    written = export_current_app_apex_catalog(output_path=output_file)
    decoded = decode_json(written.read_text(encoding="utf-8"))
    assert decoded["servers"][0]["url"] == "http://host.docker.internal:8000"

    monkeypatch.setenv("APP_URL", "http://localhost:9000")
    loopback_catalog = build_apex_catalog(SAMPLE_OPENAPI_DOCUMENT)
    assert loopback_catalog["servers"][0]["url"] == "http://host.docker.internal:9000"


def test_manage_cli_infra_and_database_command_surfaces() -> None:
    """Verify manage.py exposes trimmed infra, apex, and database command surfaces."""
    runner = CliRunner()

    infra_help = runner.invoke(manage.cli, ["infra", "--help"])
    assert infra_help.exit_code == 0, infra_help.output
    infra_commands = set(manage.infra_group.commands)
    assert infra_commands == {"start", "stop", "restart", "status", "logs", "wipe", "apex"}
    assert "ords" not in infra_commands
    assert "health" not in infra_commands

    start_help = runner.invoke(manage.cli, ["infra", "start", "--help"])
    assert start_help.exit_code == 0, start_help.output
    assert "--skip-apex" not in start_help.output
    assert "--skip-ords" not in start_help.output

    apex_help = runner.invoke(manage.cli, ["infra", "apex", "--help"])
    assert apex_help.exit_code == 0, apex_help.output
    apex_commands = set(manage.infra_group.commands["apex"].commands)  # type: ignore[attr-defined]
    assert {"status", "export-openapi", "generate", "export", "validate", "import"} <= apex_commands
    assert "install" not in apex_commands
    assert "upgrade" not in apex_commands

    db_help = runner.invoke(manage.cli, ["database", "--help"])
    assert db_help.exit_code == 0, db_help.output
    db_commands = set(manage.database_group.commands)
    assert {"connect", "wallet"} <= db_commands


def test_manage_infra_apex_status_queries_release_and_probes_ords_https(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify `manage.py infra apex status` queries APEX_RELEASE and probes ORDS HTTPS on localhost:8443."""
    wallet_dir = tmp_path / "tns"
    wallet_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("WALLET_LOCATION", str(wallet_dir))
    monkeypatch.setenv("WALLET_PASSWORD", "SuperSecret1")
    monkeypatch.setenv("DATABASE_URL", "myatp_low")
    monkeypatch.setenv("DATABASE_USER", "app")
    monkeypatch.setenv("DATABASE_PASSWORD", "SuperSecret1")
    monkeypatch.setenv("ORACLE_HTTPS_PORT", "8443")
    monkeypatch.setenv("APEX_WORKSPACE", "COFFEE")

    executed_queries: list[str] = []
    connect_kwargs: list[dict[str, Any]] = []

    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = lambda sql, *_a, **_kw: executed_queries.append(sql)
    mock_cursor.fetchone.return_value = ("26.1.5", "2026.01.05")
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None

    def fake_connect(**kwargs: Any) -> Any:
        connect_kwargs.append(kwargs)
        return mock_conn

    _FakeHTTPSConnection.calls = []
    _FakeHTTPSConnection.next_status = 200
    monkeypatch.setattr("tools.oracle.cli.apex.oracledb.connect", fake_connect)
    monkeypatch.setattr("tools.oracle.adb.http.client.HTTPSConnection", _FakeHTTPSConnection)

    result = CliRunner().invoke(manage.cli, ["infra", "apex", "status"])

    assert result.exit_code == 0, result.output
    assert any("SELECT VERSION_NO, API_COMPATIBILITY FROM APEX_RELEASE" in sql for sql in executed_queries)
    assert connect_kwargs[0]["dsn"] == "myatp_low"
    assert connect_kwargs[0]["wallet_location"] == str(wallet_dir.resolve())
    assert len(_FakeHTTPSConnection.calls) == 1
    probe = _FakeHTTPSConnection.calls[0]
    assert probe["host"] == "localhost"
    assert probe["port"] == 8443
    assert probe["url"] == "/ords/"
    assert probe["context"].verify_mode == ssl.CERT_NONE
    assert probe["context"].check_hostname is False
    assert "26.1.5" in result.output
    assert "https://localhost:8443/ords/apex" in result.output
    assert "https://localhost:8443/ords/sql-developer" in result.output
    assert "COFFEE" in result.output


def test_manage_infra_apex_status_loads_dotenv_and_defaults_to_managed_wallet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify `manage.py infra apex status` loads `.env` and defaults to `.envs/tns` when env vars are unset."""
    monkeypatch.chdir(tmp_path)
    tns_dir = tmp_path / ".envs" / "tns"
    tns_dir.mkdir(parents=True, exist_ok=True)
    (tns_dir / "tnsnames.ora").write_text("myatp_low = (DESCRIPTION=...)\n", encoding="utf-8")
    (tmp_path / ".env").write_text("DATABASE_DEPLOYMENT_MODE=managed\nAPEX_WORKSPACE=COFFEE_DOTENV\n", encoding="utf-8")
    for key in (
        "WALLET_LOCATION",
        "TNS_ADMIN",
        "WALLET_PASSWORD",
        "DATABASE_URL",
        "DATABASE_HOST",
        "DATABASE_DEPLOYMENT_MODE",
        "ORACLE_CONTAINER_FLAVOR",
        "APEX_WORKSPACE",
    ):
        monkeypatch.delenv(key, raising=False)

    connect_kwargs: list[dict[str, Any]] = []
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("26.1.5", "2026.01.05")
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None

    def fake_connect(**kwargs: Any) -> Any:
        connect_kwargs.append(kwargs)
        return mock_conn

    _FakeHTTPSConnection.calls = []
    _FakeHTTPSConnection.next_status = 200
    monkeypatch.setattr("tools.oracle.cli.apex.oracledb.connect", fake_connect)
    monkeypatch.setattr("tools.oracle.adb.http.client.HTTPSConnection", _FakeHTTPSConnection)

    result = CliRunner().invoke(manage.cli, ["infra", "apex", "status"])

    assert result.exit_code == 0, result.output
    assert connect_kwargs[0]["dsn"] == "myatp_low"
    assert connect_kwargs[0]["wallet_location"] == str(tns_dir.resolve())
    assert "COFFEE_DOTENV" in result.output


def test_manage_infra_status_renders_adb_free_endpoints_and_wallet_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify `manage.py infra status` prints APEX Builder, Database Actions, wallet dir, and myatp_low service."""
    wallet_dir = tmp_path / ".envs" / "tns"
    wallet_dir.mkdir(parents=True, exist_ok=True)
    (wallet_dir / "tnsnames.ora").write_text("myatp_low = (DESCRIPTION=...)\n", encoding="utf-8")

    runtime = MagicMock(spec=ContainerRuntime)
    cfg = DatabaseConfig(
        flavor=ContainerFlavor.ADB_FREE,
        wallet_dir=wallet_dir,
        https_port=8443,
        service_name="myatp_low",
        app_user="app",
        workspace_name="COFFEE",
    )
    fake_db = MagicMock(spec=OracleDatabase)
    fake_db.config = cfg
    fake_db.runtime = runtime
    fake_db.status.return_value = ContainerStatus(
        exists=True,
        running=True,
        healthy=True,
        status="running",
        container_id="abc123def456",
        uptime="5m",
        ports={"1522": "1521,1522", "8443": "8443"},
        image=cfg.image,
        created_at="2026-10-25T00:00:00Z",
    )

    monkeypatch.setattr("tools.oracle.cli.database._database", lambda: fake_db)

    result = CliRunner().invoke(manage.cli, ["infra", "status"])
    assert result.exit_code == 0, result.output
    assert "cymbal-adb-free" in result.output
    assert "myatp_low" in result.output
    assert str(wallet_dir) in result.output
    assert "https://localhost:8443/ords/apex" in result.output
    assert "https://localhost:8443/ords/sql-developer" in result.output
    assert "COFFEE" in result.output
    assert "APP" in result.output
