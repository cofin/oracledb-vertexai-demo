# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Oracle APEX 26.1 Vertex AI and Litestar gateway provisioning."""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import]
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self
from unittest.mock import MagicMock

import manage
import pytest
from click.testing import CliRunner
from google.auth.exceptions import DefaultCredentialsError
from tools.oracle import (
    ApexVertexConfig,
    ApexVertexConfigurator,
    ApexVertexError,
    ApexVertexMode,
    ApexVertexResult,
    mint_vertex_access_token,
)

FAKE_OAUTH_TOKEN = "fake-oauth-access-token"
FAKE_GATEWAY_KEY = "fake-local-gateway-key"


class _FakeClob:
    """Minimal python-oracledb CLOB double returning a string payload on read()."""

    def __init__(self, text: str) -> None:
        self._text = text

    def read(self) -> str:
        """Return the stored CLOB text."""
        return self._text


class _FakeOutVar:
    """Minimal python-oracledb bind variable double supporting getvalue()."""

    def __init__(self, data_type: Any) -> None:
        self.data_type = data_type
        self.value: Any = None

    def getvalue(self) -> Any:
        """Return the bound output value."""
        return self.value


class _FakeOracleCursor:
    """In-memory python-oracledb cursor double recording SQL statements and bind dicts."""

    def __init__(
        self,
        *,
        apex_schema_row: tuple[str, ...] | None = ("APEX_260100",),
        verify_output: Any = "Welcome to Cymbal Coffee, where every roast is crafted with care.",
        fail_on_substring: str | None = None,
        fail_message: str = "ORA-20000: simulated failure",
    ) -> None:
        self.apex_schema_row = apex_schema_row
        self.verify_output = verify_output
        self.fail_on_substring = fail_on_substring
        self.fail_message = fail_message
        self.executed: list[tuple[str, dict[str, Any]]] = []
        self._last_sql = ""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def var(self, data_type: Any) -> _FakeOutVar:
        """Allocate an output bind variable double."""
        return _FakeOutVar(data_type)

    def execute(self, sql: str, parameters: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Record parameterized SQL execution and populate APEX_AI.GENERATE out-binds."""
        merged = dict(parameters or {})
        merged.update(kwargs)
        self.executed.append((sql, merged))
        self._last_sql = sql
        if self.fail_on_substring and self.fail_on_substring in sql:
            raise RuntimeError(self.fail_message)
        if "APEX_AI.GENERATE" in sql and isinstance(merged.get("resp"), _FakeOutVar):
            merged["resp"].value = self.verify_output

    def fetchone(self) -> tuple[Any, ...] | None:
        """Return the configured ALL_USERS row when resolving the APEX engine schema."""
        if "all_users" in self._last_sql.lower():
            return self.apex_schema_row
        return None


class _FakeOracleConnection:
    """In-memory python-oracledb connection double tracking commits."""

    def __init__(self, cursor_instance: _FakeOracleCursor) -> None:
        self.cursor_instance = cursor_instance
        self.committed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def cursor(self) -> _FakeOracleCursor:
        """Return the attached cursor double."""
        return self.cursor_instance

    def commit(self) -> None:
        """Mark the transaction committed."""
        self.committed = True


class _StubConfigurator:
    """In-memory ApexVertexConfigurator double recording CLI-dispatched configure() calls."""

    recorded_calls: list[tuple[ApexVertexConfig, bool, bool]] = []

    def __init__(self, config: ApexVertexConfig) -> None:
        self.config = config

    def configure(self, *, refresh_token_only: bool = False, verify: bool = False) -> ApexVertexResult:
        """Record the CLI call arguments and return a deterministic ApexVertexResult."""
        self.recorded_calls.append((self.config, refresh_token_only, verify))
        return ApexVertexResult(
            mode=self.config.mode,
            base_url=self.config.base_url,
            model=self.config.model,
            workspace_name=self.config.workspace_name,
            credential_static_id="VERTEX_AI_CRED" if self.config.mode == ApexVertexMode.DIRECT else None,
            service_static_id=self.config.service_static_id,
            apex_schema="APEX_260100",
            acl_host=self.config.acl_host_and_port[0],
            acl_port=self.config.acl_host_and_port[1],
            token_refreshed=self.config.mode == ApexVertexMode.DIRECT,
            verification_response="Hello from Cymbal Coffee." if verify else None,
            verification_latency_ms=42.5 if verify else None,
        )


def _clear_vertex_and_db_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear Vertex AI, gateway, and Oracle wallet environment variables."""
    for key in (
        "VERTEX_AI_PROJECT_ID",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_PROJECT_ID",
        "VERTEX_AI_LOCATION",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_LOCATION",
        "VERTEX_AI_CHAT_MODEL",
        "APEX_GATEWAY_URL",
        "APEX_GATEWAY_API_KEY",
        "APEX_WORKSPACE",
        "WALLET_LOCATION",
        "TNS_ADMIN",
        "WALLET_PASSWORD",
        "ORACLE_ADMIN_PASSWORD",
        "DATABASE_ADMIN_PASSWORD",
        "ORACLE_PASSWORD",
        "DATABASE_USER",
        "DATABASE_SERVICE_NAME",
        "DATABASE_URL",
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_DSN",
        "ORACLE_CONTAINER_FLAVOR",
    ):
        monkeypatch.delenv(key, raising=False)


def test_apex_vertex_config_direct_and_gateway_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ApexVertexConfig resolves Direct Vertex AI /endpoints/openapi and Gateway settings from env."""
    _clear_vertex_and_db_env(monkeypatch)
    monkeypatch.setenv("VERTEX_AI_PROJECT_ID", "cymbal-coffee-proj")
    monkeypatch.setenv("VERTEX_AI_LOCATION", "global")

    direct_cfg = ApexVertexConfig.from_env(mode=ApexVertexMode.DIRECT)
    assert hasattr(direct_cfg, "__slots__")
    assert not hasattr(direct_cfg, "__dict__")
    assert direct_cfg.mode == ApexVertexMode.DIRECT
    assert (
        direct_cfg.base_url
        == "https://aiplatform.googleapis.com/v1/projects/cymbal-coffee-proj/locations/global/endpoints/openapi"
    )
    assert direct_cfg.acl_host_and_port == ("aiplatform.googleapis.com", 443)
    assert direct_cfg.model == "google/gemini-3.8-flash"
    assert direct_cfg.credential_static_id == "VERTEX_AI_CRED"
    assert direct_cfg.service_static_id == "COFFEE_VERTEX_AI"
    assert direct_cfg.workspace_name == "COFFEE"
    assert direct_cfg.app_schema == "APP"

    monkeypatch.setenv("VERTEX_AI_CHAT_MODEL", "gemini-3.8-pro")
    regional_cfg = ApexVertexConfig.from_env(mode="direct", location="us-central1")
    assert (
        regional_cfg.base_url
        == "https://aiplatform.googleapis.com/v1/projects/cymbal-coffee-proj/locations/us-central1/endpoints/openapi"
    )
    assert regional_cfg.model == "google/gemini-3.8-pro"

    _clear_vertex_and_db_env(monkeypatch)
    monkeypatch.setenv("VERTEX_AI_CHAT_MODEL", "google/gemini-3.8-flash")
    monkeypatch.setenv("DATABASE_HOST", "db.internal")
    monkeypatch.setenv("DATABASE_PORT", "1525")
    monkeypatch.setenv("DATABASE_SERVICE_NAME", "freepdb1")

    gateway_cfg = ApexVertexConfig.from_env(mode=ApexVertexMode.GATEWAY)
    assert gateway_cfg.mode == ApexVertexMode.GATEWAY
    assert gateway_cfg.base_url == "http://host.docker.internal:8000/api/apex/ai/v1"
    assert gateway_cfg.acl_host_and_port == ("host.docker.internal", 8000)
    assert gateway_cfg.model == "gemini-3.8-flash"
    assert gateway_cfg.wallet_dir is None
    assert gateway_cfg.db_dsn == "db.internal:1525/freepdb1"


@pytest.mark.parametrize(
    "invalid_project", ["", "   ", "demo-project", "your-project-id", "your-gcp-project-id", "placeholder"]
)
def test_apex_vertex_config_rejects_missing_or_placeholder_project_in_direct_mode(invalid_project: str) -> None:
    """Verify Direct Vertex AI mode rejects empty or placeholder project IDs with actionable remediation."""
    cfg = ApexVertexConfig(mode=ApexVertexMode.DIRECT, project_id=invalid_project)
    with pytest.raises(ApexVertexError, match=r"VERTEX_AI_PROJECT_ID.*--project"):
        _ = cfg.base_url


def test_mint_vertex_access_token_fallback_chain_and_redaction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify mint_vertex_access_token tries gcloud, gcloud ADC, and google.auth.default without leaking tokens."""
    monkeypatch.setattr("tools.oracle.apex_vertex.shutil.which", lambda _cmd: "/usr/bin/gcloud")
    monkeypatch.setattr(
        "tools.oracle.apex_vertex.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=f"  {FAKE_OAUTH_TOKEN}\n"),
    )
    assert mint_vertex_access_token() == FAKE_OAUTH_TOKEN

    invoked_cmds: list[list[str]] = []

    def fallback_to_adc(cmd: list[str], **_kwargs: Any) -> SimpleNamespace:
        invoked_cmds.append(cmd)
        if "application-default" not in cmd:
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd)
        return SimpleNamespace(returncode=0, stdout=f"{FAKE_OAUTH_TOKEN}-adc\n")

    monkeypatch.setattr("tools.oracle.apex_vertex.subprocess.run", fallback_to_adc)
    assert mint_vertex_access_token() == f"{FAKE_OAUTH_TOKEN}-adc"
    assert len(invoked_cmds) == 2

    monkeypatch.setattr("tools.oracle.apex_vertex.shutil.which", lambda _cmd: None)
    fake_creds = MagicMock()
    fake_creds.token = None
    fake_creds.valid = False

    def refresh_creds(_request: object) -> None:
        fake_creds.token = f"{FAKE_OAUTH_TOKEN}-google-auth\n"
        fake_creds.valid = True

    fake_creds.refresh.side_effect = refresh_creds
    monkeypatch.setattr("tools.oracle.apex_vertex.google.auth.default", lambda **_kw: (fake_creds, "proj"))
    assert mint_vertex_access_token() == f"{FAKE_OAUTH_TOKEN}-google-auth"
    fake_creds.refresh.assert_called_once()

    def raise_auth_error(**_kw: Any) -> Any:
        raise DefaultCredentialsError(f"ADC missing ({FAKE_OAUTH_TOKEN})")  # type: ignore[no-untyped-call]

    monkeypatch.setattr("tools.oracle.apex_vertex.google.auth.default", raise_auth_error)
    with pytest.raises(ApexVertexError, match="gcloud auth application-default login") as exc_info:
        mint_vertex_access_token()
    assert FAKE_OAUTH_TOKEN not in str(exc_info.value)


def test_configurator_direct_mode_executes_parameterized_plsql_without_interpolating_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify Direct Vertex AI provisioning binds parameters for ACLs, VERTEX_AI_CRED, and COFFEE_VERTEX_AI."""
    wallet_dir = tmp_path / "tns"
    wallet_dir.mkdir(parents=True, exist_ok=True)
    cursor = _FakeOracleCursor()
    connection = _FakeOracleConnection(cursor)
    connect_calls: list[dict[str, Any]] = []

    def fake_connect(**kwargs: Any) -> _FakeOracleConnection:
        connect_calls.append(kwargs)
        return connection

    monkeypatch.setattr("tools.oracle.apex_vertex.oracledb.connect", fake_connect)

    cfg = ApexVertexConfig(
        mode=ApexVertexMode.DIRECT,
        project_id="cymbal-coffee-proj",
        location="global",
        wallet_dir=wallet_dir,
        wallet_password="WalletPassword1",
        admin_password="AdminPassword1",
    )
    result = ApexVertexConfigurator(cfg, token_provider=lambda: FAKE_OAUTH_TOKEN).configure()

    assert hasattr(result, "__slots__")
    assert len(connect_calls) == 1
    assert connect_calls[0]["user"] == "ADMIN"
    assert connect_calls[0]["dsn"] == "myatp_low"
    assert connect_calls[0]["wallet_location"] == str(wallet_dir.resolve())
    assert connect_calls[0]["config_dir"] == str(wallet_dir.resolve())
    assert connection.committed is True

    for sql, _params in cursor.executed:
        assert FAKE_OAUTH_TOKEN not in sql
        assert "AdminPassword1" not in sql
        assert "WalletPassword1" not in sql

    acl_calls = [(sql, params) for sql, params in cursor.executed if "DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE" in sql]
    assert len(acl_calls) == 2
    assert {params["principal_name"] for _, params in acl_calls} == {"APP", "APEX_260100"}
    assert all(
        params["acl_host"] == "aiplatform.googleapis.com" and params["acl_port"] == 443 for _, params in acl_calls
    )

    cred_calls = [
        (sql, params) for sql, params in cursor.executed if "APEX_CREDENTIAL.SET_PERSISTENT_CREDENTIALS" in sql
    ]
    assert len(cred_calls) == 1
    cred_sql, cred_params = cred_calls[0]
    assert "APEX_CREDENTIAL.CREATE_CREDENTIAL" in cred_sql
    assert "'Bearer ' || :bearer_token" in cred_sql
    assert cred_params["cred_id"] == "VERTEX_AI_CRED"
    assert cred_params["bearer_token"] == FAKE_OAUTH_TOKEN
    assert cred_params["workspace_name"] == "COFFEE"

    service_calls = [(sql, params) for sql, params in cursor.executed if "create_remote_server" in sql]
    assert len(service_calls) == 1
    service_sql, service_params = service_calls[0]
    assert "wwv_flow_imp.import_begin" in service_sql
    assert "wwv_flow_remote_servers" in service_sql
    assert "p_ai_is_builder_service" in service_sql
    assert service_params["service_id"] == "COFFEE_VERTEX_AI"
    assert service_params["model_name"] == "google/gemini-3.8-flash"
    assert service_params["use_cred"] == 1
    assert (
        service_params["base_url"]
        == "https://aiplatform.googleapis.com/v1/projects/cymbal-coffee-proj/locations/global/endpoints/openapi"
    )

    assert result.mode == ApexVertexMode.DIRECT
    assert result.credential_static_id == "VERTEX_AI_CRED"
    assert result.service_static_id == "COFFEE_VERTEX_AI"
    assert result.apex_schema == "APEX_260100"
    assert result.token_refreshed is True
    assert result.verification_response is None


def test_configurator_refresh_token_and_verify_clob_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify --refresh-token skips ACL/service recreation, extracts .zip wallets, and --verify runs APEX_AI.GENERATE."""
    wallet_zip = tmp_path / "Wallet_ADB.zip"
    with zipfile.ZipFile(wallet_zip, "w") as archive:
        archive.writestr("tnsnames.ora", "myatp_low = (DESCRIPTION=...)\n")
    extracted_dir = tmp_path / "extracted_wallet"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    extract_calls: list[Path] = []

    def fake_extract(wallet_source: Path, *_args: Any, **_kwargs: Any) -> Path:
        extract_calls.append(wallet_source)
        return extracted_dir

    cursor = _FakeOracleCursor(verify_output=_FakeClob("  Bright bergamot notes from Ethiopia Yirgacheffe.  "))
    connection = _FakeOracleConnection(cursor)
    monkeypatch.setattr("tools.oracle.apex_vertex.extract_oracle_wallet_zip", fake_extract)
    monkeypatch.setattr("tools.oracle.apex_vertex.oracledb.connect", lambda **_kw: connection)

    cfg = ApexVertexConfig(mode=ApexVertexMode.DIRECT, project_id="cymbal-coffee-proj", wallet_dir=wallet_zip)
    result = ApexVertexConfigurator(cfg, token_provider=lambda: FAKE_OAUTH_TOKEN).configure(
        refresh_token_only=True, verify=True, verification_prompt="Recommend a light roast."
    )

    assert extract_calls == [wallet_zip]
    assert not any("DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE" in sql for sql, _ in cursor.executed)
    assert not any("create_remote_server" in sql for sql, _ in cursor.executed)
    assert any("APEX_CREDENTIAL.SET_PERSISTENT_CREDENTIALS" in sql for sql, _ in cursor.executed)

    verify_calls = [(sql, params) for sql, params in cursor.executed if "APEX_AI.GENERATE" in sql]
    assert len(verify_calls) == 1
    _, verify_params = verify_calls[0]
    assert verify_params["prompt"] == "Recommend a light roast."
    assert verify_params["service_id"] == "COFFEE_VERTEX_AI"
    assert result.token_refreshed is True
    assert result.verification_response == "Bright bergamot notes from Ethiopia Yirgacheffe."
    assert result.verification_latency_ms is not None
    assert result.verification_latency_ms >= 0.0


def test_configurator_gateway_mode_optional_api_key_and_error_redaction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify Gateway mode works with or without APEX_GATEWAY_API_KEY and scrubs secrets on DB errors."""
    unauth_cursor = _FakeOracleCursor()
    unauth_conn = _FakeOracleConnection(unauth_cursor)
    monkeypatch.setattr("tools.oracle.apex_vertex.oracledb.connect", lambda **_kw: unauth_conn)

    def unexpected_token_call() -> str:
        raise AssertionError("token_provider must not be called in gateway mode")

    unauth_cfg = ApexVertexConfig(
        mode=ApexVertexMode.GATEWAY,
        model="gemini-3.8-flash",
        gateway_url="http://host.docker.internal:8000/api/apex/ai/v1/",
        gateway_api_key=None,
        wallet_dir=None,
        db_dsn="localhost:1521/freepdb1",
    )
    unauth_result = ApexVertexConfigurator(unauth_cfg, token_provider=unexpected_token_call).configure()
    assert unauth_result.mode == ApexVertexMode.GATEWAY
    assert unauth_result.base_url == "http://host.docker.internal:8000/api/apex/ai/v1"
    assert unauth_result.acl_host == "host.docker.internal"
    assert unauth_result.acl_port == 8000
    assert unauth_result.credential_static_id is None
    assert unauth_result.token_refreshed is False
    assert not any("APEX_CREDENTIAL" in sql for sql, _ in unauth_cursor.executed)
    service_params = next(params for sql, params in unauth_cursor.executed if "create_remote_server" in sql)
    assert service_params["use_cred"] == 0

    auth_cursor = _FakeOracleCursor()
    monkeypatch.setattr("tools.oracle.apex_vertex.oracledb.connect", lambda **_kw: _FakeOracleConnection(auth_cursor))
    auth_cfg = ApexVertexConfig(
        mode=ApexVertexMode.GATEWAY,
        model="gemini-3.8-flash",
        gateway_api_key=FAKE_GATEWAY_KEY,
        wallet_dir=None,
        db_dsn="localhost:1521/freepdb1",
    )
    auth_result = ApexVertexConfigurator(auth_cfg, token_provider=unexpected_token_call).configure()
    assert auth_result.credential_static_id == "VERTEX_AI_CRED"
    assert auth_result.token_refreshed is True
    assert all(FAKE_GATEWAY_KEY not in sql for sql, _ in auth_cursor.executed)

    no_apex_cursor = _FakeOracleCursor(apex_schema_row=None)
    monkeypatch.setattr(
        "tools.oracle.apex_vertex.oracledb.connect", lambda **_kw: _FakeOracleConnection(no_apex_cursor)
    )
    with pytest.raises(ApexVertexError, match="APEX"):
        ApexVertexConfigurator(unauth_cfg, token_provider=unexpected_token_call).configure()

    failing_cursor = _FakeOracleCursor(
        fail_on_substring="APEX_CREDENTIAL", fail_message=f"ORA-20099: simulated error mentioning {FAKE_OAUTH_TOKEN}"
    )
    monkeypatch.setattr(
        "tools.oracle.apex_vertex.oracledb.connect", lambda **_kw: _FakeOracleConnection(failing_cursor)
    )
    direct_cfg = ApexVertexConfig(
        mode=ApexVertexMode.DIRECT, project_id="cymbal-coffee-proj", wallet_dir=None, db_dsn="localhost:1521/freepdb1"
    )
    with pytest.raises(ApexVertexError) as exc_info:
        ApexVertexConfigurator(direct_cfg, token_provider=lambda: FAKE_OAUTH_TOKEN).configure()
    assert FAKE_OAUTH_TOKEN not in str(exc_info.value)


def test_manage_infra_apex_configure_vertex_cli_direct_and_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify `manage.py infra apex configure-vertex` dispatches direct/gateway flags and never prints tokens."""
    _StubConfigurator.recorded_calls = []
    monkeypatch.setattr("tools.oracle.cli.apex._build_apex_vertex_configurator", _StubConfigurator)
    runner = CliRunner()

    direct_cli = runner.invoke(
        manage.cli,
        ["infra", "apex", "configure-vertex", "--mode", "direct", "--project", "cymbal-coffee-proj", "--verify"],
    )
    assert direct_cli.exit_code == 0, direct_cli.output
    assert len(_StubConfigurator.recorded_calls) == 1
    assert _StubConfigurator.recorded_calls[0][0].mode == ApexVertexMode.DIRECT
    assert _StubConfigurator.recorded_calls[0][1] is False
    assert _StubConfigurator.recorded_calls[0][2] is True
    assert (
        "https://aiplatform.googleapis.com/v1/projects/cymbal-coffee-proj/locations/global/endpoints/openapi"
        in direct_cli.output
    )
    assert "google/gemini-3.8-flash" in direct_cli.output
    assert "COFFEE_VERTEX_AI" in direct_cli.output
    assert "--refresh-token" in direct_cli.output
    assert "Hello from Cymbal Coffee." in direct_cli.output
    assert FAKE_OAUTH_TOKEN not in direct_cli.output

    gateway_cli = runner.invoke(manage.cli, ["infra", "apex", "configure-vertex", "--mode", "gateway"])
    assert gateway_cli.exit_code == 0, gateway_cli.output
    assert "http://host.docker.internal:8000/api/apex/ai/v1" in gateway_cli.output
    assert "gemini-3.8-flash" in gateway_cli.output

    def fail_builder(_config: ApexVertexConfig) -> Any:
        raise ApexVertexError("Simulated missing project ID")

    monkeypatch.setattr("tools.oracle.cli.apex._build_apex_vertex_configurator", fail_builder)
    failed_cli = runner.invoke(manage.cli, ["infra", "apex", "configure-vertex"])
    assert failed_cli.exit_code != 0
    assert "Simulated missing project ID" in failed_cli.output
