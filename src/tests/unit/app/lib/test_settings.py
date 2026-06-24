# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Database settings contracts for SQLSpec Oracle integrations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@pytest.mark.parametrize("explicit", [True, False], ids=["explicit-true", "default-true"])
def test_oracle_adk_and_litestar_session_in_memory_wire_to_sqlspec_config(
    monkeypatch: MonkeyPatch, explicit: bool
) -> None:
    from app.lib.settings import DatabaseSettings

    if explicit:
        monkeypatch.setenv("ORACLE_ADK_IN_MEMORY", "true")
        monkeypatch.setenv("ORACLE_LITESTAR_SESSION_IN_MEMORY", "true")
    else:
        monkeypatch.delenv("ORACLE_ADK_IN_MEMORY", raising=False)
        monkeypatch.delenv("ORACLE_LITESTAR_SESSION_IN_MEMORY", raising=False)
    monkeypatch.setenv("ADK_ENABLE_MEMORY", "false")

    config = DatabaseSettings().create_config()

    assert config.extension_config["adk"]["in_memory"] is True
    assert config.extension_config["adk"]["include_memory_migration"] is False
    assert config.extension_config["adk"]["memory_table"] == "adk_memory_entries"
    assert config.extension_config["litestar"]["in_memory"] is True


def test_litestar_env_defaults_app_url_from_litestar_port(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import Settings

    monkeypatch.delenv("APP_URL", raising=False)
    monkeypatch.setenv("LITESTAR_PORT", "5006")

    Settings().setup_litestar_env()

    assert os.environ["APP_URL"] == "http://localhost:5006"


def test_litestar_env_preserves_explicit_app_url(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import Settings

    monkeypatch.setenv("APP_URL", "https://coffee.example.test")

    Settings().setup_litestar_env()

    assert os.environ["APP_URL"] == "https://coffee.example.test"


def test_ai_settings_defaults(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import AISettings

    for key in (
        "GOOGLE_CLOUD_PROJECT",
        "VERTEX_AI_PROJECT_ID",
        "VERTEX_AI_EMBEDDING_MODEL",
        "VERTEX_AI_CHAT_MODEL",
        "VERTEX_AI_INTENT_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = AISettings()

    assert settings.chat_model == "gemini-3.1-flash-lite"
    assert settings.embedding_model == "gemini-embedding-2"
    assert settings.embedding_dimensions == 3072
    assert settings.intent_model_override is None
    assert settings.intent_model == settings.chat_model


def test_intent_model_override_wins(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import AISettings

    monkeypatch.setenv("VERTEX_AI_INTENT_MODEL", "gemini-x")

    settings = AISettings()

    assert settings.intent_model_override == "gemini-x"
    assert settings.intent_model == "gemini-x"


def test_chat_settings_defaults(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import ChatSettings

    settings = ChatSettings()

    assert settings.session_app_name == "coffee_assistant"
    assert settings.response_cache_version == "menu-grounded-v2"
    assert settings.response_cache_ttl_minutes == 60
    assert settings.product_search_limit == 5
    assert settings.product_search_threshold == 0.7
    assert settings.display_history_limit == 40
    assert settings.grounded_answer_timeout_seconds == 2.5


def test_wallet_location_resolves_to_absolute_path(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import DatabaseSettings

    monkeypatch.setenv("DATABASE_URL", "oracle+oracledb://app:password@myatp_low")
    monkeypatch.setenv("WALLET_PASSWORD", "SuperSecret1")
    monkeypatch.setenv("TNS_ADMIN", "./.envs/tns")

    settings = DatabaseSettings()
    assert settings.WALLET_LOCATION == "./.envs/tns"

    config = settings.create_config()

    expected_path = str(Path("./.envs/tns").resolve())
    assert os.environ["TNS_ADMIN"] == expected_path
    assert config.connection_config["wallet_location"] == expected_path
    assert config.connection_config["config_dir"] == expected_path


def test_service_name_defaults_to_freepdb1(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import DatabaseSettings

    # clear env to get defaults (local gvenzl/oracle-free PDB)
    monkeypatch.delenv("DATABASE_SERVICE_NAME", raising=False)
    settings = DatabaseSettings()
    assert settings.SERVICE_NAME == "freepdb1"


def test_database_settings_local_contract(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import DatabaseSettings

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
    assert settings.PASSWORD == "SuperSecret1"  # noqa: S105
    assert settings.HOST == "localhost"
    assert settings.PORT == "1521"
    assert settings.SERVICE_NAME == "freepdb1"
    assert settings.DSN == "localhost:1521/freepdb1"
    assert settings.POOL_MIN_SIZE == 5
    assert settings.POOL_MAX_SIZE == 20


def test_wallet_mode_contract(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import DatabaseSettings

    monkeypatch.setenv("DATABASE_URL", "oracle+oracledb://app:SuperSecret1@myatp_low")
    monkeypatch.setenv("WALLET_PASSWORD", "SuperSecret1")
    monkeypatch.setenv("TNS_ADMIN", "./.envs/tns")

    settings = DatabaseSettings()

    assert settings.is_autonomous is True

    config = settings.create_config()
    conn = config.connection_config

    assert conn["user"] == "app"
    assert conn["dsn"] == "myatp_low"
    assert conn["wallet_password"] == "SuperSecret1"  # noqa: S105
    assert conn["wallet_location"] == str(Path("./.envs/tns").resolve())
    assert conn["config_dir"] == str(Path("./.envs/tns").resolve())


def test_shell_env_wins_over_dotenv(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import Settings

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
    from app.lib.settings import DatabaseSettings

    monkeypatch.setenv("ORACLE_ADK_IN_MEMORY", raw)
    assert DatabaseSettings().ADK_IN_MEMORY is True


@pytest.mark.parametrize("raw", ["False", "false", "0", "no", "n", ""])
def test_env_bool_parsing_falsy(monkeypatch: MonkeyPatch, raw: str) -> None:
    from app.lib.settings import DatabaseSettings

    monkeypatch.setenv("ORACLE_ADK_IN_MEMORY", raw)
    assert DatabaseSettings().ADK_IN_MEMORY is False


def test_allowed_cors_origins_json_list(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import AppSettings

    monkeypatch.setenv("ALLOWED_CORS_ORIGINS", '["*"]')
    assert AppSettings().ALLOWED_CORS_ORIGINS == ["*"]


def test_allowed_cors_origins_comma_list(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import AppSettings

    monkeypatch.setenv("ALLOWED_CORS_ORIGINS", "a.com,b.com")
    assert AppSettings().ALLOWED_CORS_ORIGINS == ["a.com", "b.com"]


def test_secret_key_honors_env(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import AppSettings

    monkeypatch.setenv("SECRET_KEY", "fixed-secret-value")
    assert AppSettings().SECRET_KEY == "fixed-secret-value"  # noqa: S105


def test_secret_key_generated_when_absent(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import AppSettings

    monkeypatch.delenv("SECRET_KEY", raising=False)
    settings = AppSettings()

    # A non-empty key is generated and stable for the lifetime of one instance.
    assert settings.SECRET_KEY
    assert settings.SECRET_KEY == settings.SECRET_KEY


def test_create_config_local_mode(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import DatabaseSettings

    for key in ("DATABASE_URL", "WALLET_PASSWORD", "WALLET_LOCATION", "TNS_ADMIN"):
        monkeypatch.delenv(key, raising=False)

    config = DatabaseSettings().create_config()
    conn = config.connection_config

    assert set(conn) >= {"user", "password", "dsn", "min", "max"}
    assert "wallet_location" not in conn
    assert "wallet_password" not in conn
    assert "config_dir" not in conn


def test_get_settings_cache_and_reset(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import Settings, get_settings

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
    """Verify that when DATABASE_URL and WALLET_PASSWORD are unset (Cloud Run env),

    DatabaseSettings is_autonomous is False and we resolve to the standard DSN.
    """
    from app.lib.settings import DatabaseSettings

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
