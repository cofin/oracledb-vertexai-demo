# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Database, AI, app, and observability settings contracts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from app.lib.settings import (
    AISettings,
    AppSettings,
    ChatSettings,
    DatabaseSettings,
    LogSettings,
    MapsSettings,
    OpenTelemetrySettings,
    QueueSettings,
    ServerSettings,
    Settings,
    ViteSettings,
    get_settings,
    reload_settings,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@pytest.mark.parametrize("explicit", [True, False], ids=["explicit-true", "default-true"])
def test_litestar_session_in_memory_wires_to_sqlspec_config(monkeypatch: MonkeyPatch, explicit: bool) -> None:
    """Verify `ORACLE_LITESTAR_SESSION_IN_MEMORY` defaults to and configures `in_memory=True`."""
    if explicit:
        monkeypatch.setenv("ORACLE_LITESTAR_SESSION_IN_MEMORY", "true")
    else:
        monkeypatch.delenv("ORACLE_LITESTAR_SESSION_IN_MEMORY", raising=False)

    config = DatabaseSettings().create_config()
    litestar_ext = cast("dict[str, Any]", config.extension_config["litestar"])

    assert litestar_ext["in_memory"] is True
    assert litestar_ext["session_table"] == "app_session"


def test_litestar_env_defaults_app_url_from_litestar_port(monkeypatch: MonkeyPatch) -> None:
    """Verify `setup_litestar_env` derives `APP_URL` from `LITESTAR_PORT` when unset."""
    monkeypatch.delenv("APP_URL", raising=False)
    monkeypatch.setenv("LITESTAR_PORT", "5006")

    Settings().setup_litestar_env()

    assert os.environ["APP_URL"] == "http://localhost:5006"


def test_litestar_env_preserves_explicit_app_url(monkeypatch: MonkeyPatch) -> None:
    """Verify `setup_litestar_env` preserves an explicit `APP_URL`."""
    monkeypatch.setenv("APP_URL", "https://coffee.example.test")

    Settings().setup_litestar_env()

    assert os.environ["APP_URL"] == "https://coffee.example.test"


def test_ai_settings_defaults(monkeypatch: MonkeyPatch) -> None:
    """Verify `AISettings` defaults to `gemini-3.8-flash`, `gemini-embedding-2`, and `global` location."""
    for key in (
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_PROJECT_ID",
        "VERTEX_AI_PROJECT_ID",
        "VERTEX_AI_LOCATION",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_LOCATION",
        "VERTEX_AI_EMBEDDING_MODEL",
        "VERTEX_AI_CHAT_MODEL",
        "VERTEX_AI_INTENT_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = AISettings()

    assert settings.chat_model == "gemini-3.8-flash"
    assert settings.embedding_model == "gemini-embedding-2"
    assert settings.embedding_dimensions == 3072
    assert settings.location == "global"
    assert settings.resolve_location() == "global"
    assert settings.intent_model_override is None
    assert settings.intent_model == settings.chat_model


def test_ai_settings_falls_back_to_google_project_id(monkeypatch: MonkeyPatch) -> None:
    """Verify `AISettings.project_id` falls back to `GOOGLE_PROJECT_ID` when `GOOGLE_CLOUD_PROJECT` is unset."""
    monkeypatch.delenv("VERTEX_AI_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setenv("GOOGLE_PROJECT_ID", "cymbal-coffee-test")

    settings = AISettings()

    assert settings.project_id == "cymbal-coffee-test"


def test_intent_model_override_wins(monkeypatch: MonkeyPatch) -> None:
    """Verify `VERTEX_AI_INTENT_MODEL` overrides `intent_model`."""
    monkeypatch.setenv("VERTEX_AI_INTENT_MODEL", "gemini-x")

    settings = AISettings()

    assert settings.intent_model_override == "gemini-x"
    assert settings.intent_model == "gemini-x"


def test_chat_settings_defaults() -> None:
    """Verify `ChatSettings` default values."""
    settings = ChatSettings()

    assert settings.session_app_name == "coffee_assistant"
    assert settings.response_cache_version == "menu-grounded-v2"
    assert settings.response_cache_ttl_minutes == 60
    assert settings.product_search_limit == 5
    assert settings.product_search_threshold == 0.7
    assert settings.display_history_limit == 40
    assert settings.grounded_answer_timeout_seconds == 2.5


def test_wallet_location_resolves_to_absolute_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Verify Autonomous wallet paths resolve via SQLSpec wallet_zip without mutating TNS_ADMIN."""
    wallet_dir = tmp_path / "tns"
    wallet_dir.mkdir()
    (wallet_dir / "ewallet.pem").write_text("dummy")

    monkeypatch.setenv("DATABASE_URL", "oracle+oracledb://app:password@myatp_low")
    monkeypatch.setenv("WALLET_PASSWORD", "WalletSecret1")
    monkeypatch.setenv("WALLET_LOCATION", str(wallet_dir))
    monkeypatch.delenv("TNS_ADMIN", raising=False)

    settings = DatabaseSettings()
    assert settings.WALLET_LOCATION is not None
    assert Path(settings.WALLET_LOCATION) == wallet_dir

    expected_path = str(wallet_dir.resolve())
    pool_cfg = settings._build_pool_config(min_sessions=1, max_sessions=4)
    assert pool_cfg["wallet_zip"] == expected_path
    assert pool_cfg["wallet_password"] == "WalletSecret1"
    assert "ssl_context" not in pool_cfg
    assert "TNS_ADMIN" not in os.environ

    config = settings.create_config()
    assert "TNS_ADMIN" not in os.environ
    assert config.connection_config["wallet_location"] == expected_path
    assert config.connection_config["config_dir"] == expected_path


def test_service_name_defaults_to_freepdb1(monkeypatch: MonkeyPatch) -> None:
    """Verify `DATABASE_SERVICE_NAME` defaults to `freepdb1` for local `gvenzl/oracle-free`."""
    monkeypatch.delenv("DATABASE_SERVICE_NAME", raising=False)
    settings = DatabaseSettings()
    assert settings.SERVICE_NAME == "freepdb1"


def test_database_settings_local_contract(monkeypatch: MonkeyPatch) -> None:
    """Verify `DatabaseSettings` local connection defaults."""
    for key in (
        "DATABASE_URL",
        "WALLET_PASSWORD",
        "WALLET_LOCATION",
        "TNS_ADMIN",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_SERVICE_NAME",
        "DATABASE_DSN",
        "DATABASE_POOL_MIN_SIZE",
        "DATABASE_POOL_MAX_SIZE",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = DatabaseSettings()

    assert settings.USER == "app"
    assert settings.PASSWORD == "SuperSecret1"
    assert settings.HOST == "localhost"
    assert settings.PORT == "1521"
    assert settings.SERVICE_NAME == "freepdb1"
    assert settings.DSN == "localhost:1521/freepdb1"
    assert settings.POOL_MIN_SIZE == 5
    assert settings.POOL_MAX_SIZE == 20


@pytest.mark.parametrize(
    "database_url",
    ["oracle+oracledb://app:SuperSecret1@myatp_low", "myatp_low"],
    ids=["sqlalchemy-url", "bare-tns-alias"],
)
def test_wallet_mode_contract(tmp_path: Path, monkeypatch: MonkeyPatch, database_url: str) -> None:
    """Verify Autonomous Database wallet mode supports URL and bare TNS alias connection formats."""
    wallet_dir = tmp_path / "wallet"
    wallet_dir.mkdir()
    (wallet_dir / "ewallet.pem").write_text("dummy")

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("DATABASE_USER", "app")
    monkeypatch.setenv("DATABASE_PASSWORD", "SuperSecret1")
    monkeypatch.setenv("WALLET_PASSWORD", "WalletSecret1")
    monkeypatch.setenv("TNS_ADMIN", str(wallet_dir))

    settings = DatabaseSettings()

    assert settings.is_autonomous is True

    config = settings.create_config()
    conn = config.connection_config

    assert conn["user"] == "app"
    assert conn["dsn"] == "myatp_low"
    assert conn["wallet_password"] == "WalletSecret1"
    assert conn["wallet_location"] == str(wallet_dir.resolve())
    assert conn["config_dir"] == str(wallet_dir.resolve())


def test_shell_env_wins_over_dotenv(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Verify shell environment variables take precedence over `.env` values."""
    env_file = tmp_path / ".env"
    env_file.write_text("LITESTAR_PORT=9999\n")
    monkeypatch.setenv("LITESTAR_PORT", "8123")

    Settings.from_env.cache_clear()
    try:
        Settings.from_env(str(env_file))
    finally:
        Settings.from_env.cache_clear()

    assert os.environ["LITESTAR_PORT"] == "8123"


@pytest.mark.parametrize("raw", ["True", "true", "1", "yes", "Y", "T"])
def test_env_bool_parsing_truthy(monkeypatch: MonkeyPatch, raw: str) -> None:
    """Verify truthy string values parse to `True`."""
    monkeypatch.setenv("ORACLE_LITESTAR_SESSION_IN_MEMORY", raw)
    assert DatabaseSettings().LITESTAR_SESSION_IN_MEMORY is True


@pytest.mark.parametrize("raw", ["False", "false", "0", "no", "n", ""])
def test_env_bool_parsing_falsy(monkeypatch: MonkeyPatch, raw: str) -> None:
    """Verify falsy string values parse to `False`."""
    monkeypatch.setenv("ORACLE_LITESTAR_SESSION_IN_MEMORY", raw)
    assert DatabaseSettings().LITESTAR_SESSION_IN_MEMORY is False


def test_allowed_cors_origins_json_list(monkeypatch: MonkeyPatch) -> None:
    """Verify JSON-encoded `ALLOWED_CORS_ORIGINS` parses into a list."""
    monkeypatch.setenv("ALLOWED_CORS_ORIGINS", '["*"]')
    assert AppSettings().ALLOWED_CORS_ORIGINS == ["*"]


def test_allowed_cors_origins_comma_list(monkeypatch: MonkeyPatch) -> None:
    """Verify comma-separated `ALLOWED_CORS_ORIGINS` parses into a list."""
    monkeypatch.setenv("ALLOWED_CORS_ORIGINS", "a.com,b.com")
    assert AppSettings().ALLOWED_CORS_ORIGINS == ["a.com", "b.com"]


def test_secret_key_honors_env(monkeypatch: MonkeyPatch) -> None:
    """Verify `SECRET_KEY` reads from the environment when set."""
    monkeypatch.setenv("SECRET_KEY", "fixed-secret-value")
    assert AppSettings().SECRET_KEY == "fixed-secret-value"


def test_secret_key_generated_when_absent(monkeypatch: MonkeyPatch) -> None:
    """Verify a non-empty `SECRET_KEY` is generated when absent from the environment."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    settings = AppSettings()

    assert settings.SECRET_KEY
    assert settings.SECRET_KEY == settings.SECRET_KEY


def test_create_config_local_mode(monkeypatch: MonkeyPatch) -> None:
    """Verify local mode `create_config` omits wallet connection keys."""
    for key in ("DATABASE_URL", "WALLET_PASSWORD", "WALLET_LOCATION", "TNS_ADMIN"):
        monkeypatch.delenv(key, raising=False)

    config = DatabaseSettings().create_config()
    conn = config.connection_config

    assert set(conn) >= {"user", "password", "dsn", "min", "max"}
    assert "wallet_location" not in conn
    assert "wallet_password" not in conn
    assert "config_dir" not in conn


def test_get_settings_cache_and_reset() -> None:
    """Verify `get_settings()` caches the `Settings` instance until `cache_clear()` is called."""
    Settings.from_env.cache_clear()
    try:
        first = get_settings()
        second = get_settings()
        assert first is second

        Settings.from_env.cache_clear()
        third = get_settings()
        assert third is not first
    finally:
        Settings.from_env.cache_clear()


@pytest.mark.parametrize("unset", ["DATABASE_URL", "WALLET_PASSWORD"])
def test_cloud_run_env_uses_standard_dsn(monkeypatch: MonkeyPatch, unset: str) -> None:
    """Verify Cloud Run environment variables resolve to standard non-wallet DSN."""
    del unset
    for key, value in {
        "DATABASE_HOST": "10.10.0.10",
        "DATABASE_PORT": "1521",
        "DATABASE_SERVICE_NAME": "freepdb1",
        "DATABASE_USER": "app",
        "DATABASE_PASSWORD": "secret-from-secret-manager",
    }.items():
        monkeypatch.setenv(key, value)

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("WALLET_PASSWORD", raising=False)
    monkeypatch.delenv("DATABASE_DSN", raising=False)

    settings = DatabaseSettings()

    assert settings.is_autonomous is False
    params = settings.get_connection_params()
    assert params["dsn"] == "10.10.0.10:1521/freepdb1"
    assert params["user"] == "app"
    assert "wallet_password" not in params


def test_opentelemetry_settings_defaults(monkeypatch: MonkeyPatch) -> None:
    """Verify OpenTelemetrySettings default values and env override."""
    monkeypatch.delenv("OTEL_ENABLED", raising=False)
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)

    otel = OpenTelemetrySettings()
    assert otel.ENABLED is True
    assert otel.SERVICE_NAME == "cymbal-coffee"
    assert "^/static" in otel.EXCLUDE_PATHS

    monkeypatch.setenv("OTEL_ENABLED", "false")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "custom-coffee")

    custom_otel = OpenTelemetrySettings()
    assert custom_otel.ENABLED is False
    assert custom_otel.SERVICE_NAME == "custom-coffee"


def test_litestar_env_sets_otel_service_name(monkeypatch: MonkeyPatch) -> None:
    """Verify `setup_litestar_env` exports `OTEL_SERVICE_NAME`."""
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    Settings().setup_litestar_env()

    assert os.environ["OTEL_SERVICE_NAME"] == "cymbal-coffee"


def test_database_observability_defaults(monkeypatch: MonkeyPatch) -> None:
    """Verify DatabaseSettings default observability configuration."""
    monkeypatch.delenv("DATABASE_ECHO", raising=False)
    monkeypatch.delenv("DATABASE_ECHO_SQL", raising=False)
    monkeypatch.delenv("SQLSPEC_ECHO", raising=False)
    monkeypatch.delenv("DATABASE_ENABLE_TELEMETRY", raising=False)
    monkeypatch.delenv("SQLSPEC_ENABLE_TELEMETRY", raising=False)

    db_settings = DatabaseSettings()
    assert db_settings.ECHO is False
    assert db_settings.ENABLE_TELEMETRY is True

    config = db_settings.create_config()
    assert config.observability_config is not None
    assert config.observability_config.print_sql is False
    assert config.observability_config.telemetry is not None
    assert config.observability_config.telemetry.enable_spans is True
    assert config.observability_config.logging is not None
    assert config.observability_config.logging.include_trace_context is True


def test_database_observability_echo_and_telemetry_toggles(monkeypatch: MonkeyPatch) -> None:
    """Verify DatabaseSettings environment variable toggles for echo and telemetry."""
    monkeypatch.setenv("DATABASE_ECHO", "true")
    monkeypatch.setenv("DATABASE_ENABLE_TELEMETRY", "false")

    db_settings = DatabaseSettings()
    assert db_settings.ECHO is True
    assert db_settings.ENABLE_TELEMETRY is False

    config = db_settings.create_config()
    assert config.observability_config is not None
    assert config.observability_config.print_sql is True
    assert config.observability_config.telemetry is not None
    assert config.observability_config.telemetry.enable_spans is False


def test_agent_in_memory_removes_legacy_adk_fields(monkeypatch: MonkeyPatch) -> None:
    """Verify `DatabaseSettings` exposes `AGENT_IN_MEMORY` without legacy `ADK_*` fields."""
    monkeypatch.delenv("ORACLE_AGENT_IN_MEMORY", raising=False)
    monkeypatch.setenv("ORACLE_ADK_IN_MEMORY", "false")
    default_db = DatabaseSettings()
    assert default_db.AGENT_IN_MEMORY is True
    assert not hasattr(default_db, "ADK_IN_MEMORY")
    assert not hasattr(default_db, "ADK_ENABLE_MEMORY")

    monkeypatch.setenv("ORACLE_AGENT_IN_MEMORY", "false")
    disabled_db = DatabaseSettings()
    assert disabled_db.AGENT_IN_MEMORY is False


@pytest.mark.parametrize(
    "settings_cls",
    [
        Settings,
        AppSettings,
        ServerSettings,
        ViteSettings,
        LogSettings,
        DatabaseSettings,
        AISettings,
        ChatSettings,
        MapsSettings,
        OpenTelemetrySettings,
        QueueSettings,
    ],
)
def test_all_settings_dataclasses_define_slots(settings_cls: type[object]) -> None:
    """Verify every settings dataclass uses `slots=True` and omits per-instance `__dict__`."""
    instance = settings_cls()
    assert hasattr(settings_cls, "__slots__")
    assert not hasattr(instance, "__dict__")


def test_database_settings_enables_session_tracing_and_wire_sqlcommenter(monkeypatch: MonkeyPatch) -> None:
    """Verify `DatabaseSettings.get_config()` enables SQLSpec 0.69.0 session tracing and wire sqlcommenter."""
    for key in ("DATABASE_URL", "WALLET_PASSWORD", "WALLET_LOCATION", "TNS_ADMIN"):
        monkeypatch.delenv(key, raising=False)

    config = DatabaseSettings().get_config()

    assert config.driver_features["enable_session_tracing"] is True
    assert config.driver_features["fetch_lobs"] is True
    assert "enable_AutoLob" not in config.driver_features
    assert config.statement_config.enable_sqlcommenter is True
    assert config.statement_config.sqlcommenter_enable_context is True
    assert config.statement_config.sqlcommenter_enable_traceparent is True


def test_app_settings_mcp_api_key_and_reload(monkeypatch: MonkeyPatch) -> None:
    """Verify `AppSettings.MCP_API_KEY` parsing and `reload_settings` cache busting."""
    monkeypatch.delenv("MCP_API_KEY", raising=False)
    assert AppSettings().MCP_API_KEY is None

    monkeypatch.setenv("MCP_API_KEY", "  secret-mcp-token  ")
    assert AppSettings().MCP_API_KEY == "secret-mcp-token"

    first = get_settings()
    second = reload_settings(dotenv_filename=".missing-env")
    assert second is not first


def test_configure_genai_env_ignores_placeholder_project_id_and_preserves_api_key(monkeypatch: MonkeyPatch) -> None:
    """Verify a placeholder `project_id` with a valid `api_key` does not pop `GOOGLE_API_KEY` or enable Vertex AI."""
    monkeypatch.setenv("VERTEX_AI_PROJECT_ID", "your-project-id")
    monkeypatch.setenv("GOOGLE_API_KEY", "real-api-key-123")
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)

    settings = Settings()
    assert settings.ai.has_valid_project_id() is False
    assert settings.ai.has_valid_api_key() is True

    settings.configure_genai_env()

    assert os.environ.get("GOOGLE_API_KEY") == "real-api-key-123"
    assert os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") is None
