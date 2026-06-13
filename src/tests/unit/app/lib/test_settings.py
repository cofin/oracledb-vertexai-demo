# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Database settings contracts for SQLSpec Oracle integrations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_oracle_adk_and_litestar_session_flags_wire_to_sqlspec_config(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import DatabaseSettings

    monkeypatch.setenv("ORACLE_ADK_IN_MEMORY", "true")
    monkeypatch.setenv("ORACLE_LITESTAR_SESSION_IN_MEMORY", "true")
    monkeypatch.setenv("ADK_ENABLE_MEMORY", "false")

    config = DatabaseSettings().create_config()

    assert config.extension_config["adk"]["in_memory"] is True
    assert config.extension_config["adk"]["include_memory_migration"] is False
    assert config.extension_config["adk"]["memory_table"] == "adk_memory_entries"
    assert config.extension_config["litestar"]["in_memory"] is True


def test_oracle_adk_and_litestar_session_in_memory_default_to_true(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import DatabaseSettings

    monkeypatch.delenv("ORACLE_ADK_IN_MEMORY", raising=False)
    monkeypatch.delenv("ORACLE_LITESTAR_SESSION_IN_MEMORY", raising=False)

    config = DatabaseSettings().create_config()

    assert config.extension_config["adk"]["in_memory"] is True
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


def test_vite_config_uses_resources_as_frontend_root() -> None:
    from app.lib.settings import BASE_DIR, ViteSettings

    config = ViteSettings().get_config()

    assert config.paths.root == BASE_DIR.parent / "resources"
    assert config.paths.resource_dir == Path()
    assert config.paths.static_dir == Path("public")
    assert config.types is not None
    assert config.types.output == BASE_DIR.parent / "resources" / "generated"


def test_wallet_location_resolves_to_absolute_path(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import DatabaseSettings

    monkeypatch.setenv("DATABASE_URL", "oracle+oracledb://app:password@myatp_low")
    monkeypatch.setenv("WALLET_PASSWORD", "SuperSecret1")
    monkeypatch.setenv("TNS_ADMIN", "./.envs/tns")

    settings = DatabaseSettings()
    assert settings.WALLET_LOCATION == "./.envs/tns"

    settings.create_config()

    expected_path = str(Path("./.envs/tns").resolve())
    assert os.environ["TNS_ADMIN"] == expected_path


def test_service_name_defaults_to_myatp_low(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import DatabaseSettings

    # clear env to get defaults
    monkeypatch.delenv("DATABASE_SERVICE_NAME", raising=False)
    settings = DatabaseSettings()
    assert settings.SERVICE_NAME == "myatp_low"
