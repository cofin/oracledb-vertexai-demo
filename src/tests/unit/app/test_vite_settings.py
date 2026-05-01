# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


def test_vite_settings_stay_in_template_mode(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import ViteSettings

    monkeypatch.delenv("LITESTAR_TRUSTED_PROXIES", raising=False)

    config = ViteSettings().get_config()

    assert config.mode == "template"
    assert str(config.paths.resource_dir) == "src/resources"
    assert str(config.paths.bundle_dir).endswith("src/app/domain/web/static/dist")
    assert config.paths.asset_url == "/static/dist/"
    assert config.runtime.executor == "node"


def test_vite_settings_pass_trusted_proxies(monkeypatch: MonkeyPatch) -> None:
    """``litestar_vite.RuntimeConfig`` reads ``LITESTAR_TRUSTED_PROXIES`` itself."""
    from app.lib.settings import ViteSettings

    monkeypatch.setenv("LITESTAR_TRUSTED_PROXIES", "*")

    config = ViteSettings().get_config()

    assert config.runtime.trusted_proxies == "*"


def test_vite_settings_asset_url_matches_standard_env_fallback(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import ViteSettings

    monkeypatch.delenv("VITE_ASSET_URL", raising=False)
    monkeypatch.setenv("ASSET_URL", "https://cdn.example.test/static/")

    assert ViteSettings().get_config().paths.asset_url == "https://cdn.example.test/static/"

    monkeypatch.setenv("VITE_ASSET_URL", "/static/dist/")

    assert ViteSettings().get_config().paths.asset_url == "/static/dist/"


def test_settings_exports_app_url_from_litestar_port(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    from app.lib.settings import Settings

    Settings.from_env.cache_clear()
    monkeypatch.delenv("APP_URL", raising=False)
    monkeypatch.delenv("LITESTAR_PORT", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LITESTAR_PORT=5006\n")

    try:
        settings = Settings.from_env(str(env_file))

        assert settings.app.URL == "http://localhost:5006"
        assert os.environ["APP_URL"] == "http://localhost:5006"
    finally:
        Settings.from_env.cache_clear()


def test_settings_preserves_shell_app_url_override(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    from app.lib.settings import Settings

    Settings.from_env.cache_clear()
    monkeypatch.setenv("APP_URL", "http://localhost:9000")
    env_file = tmp_path / ".env"
    env_file.write_text("LITESTAR_PORT=5006\nAPP_URL=http://localhost:${LITESTAR_PORT}\n")

    try:
        settings = Settings.from_env(str(env_file))

        assert settings.app.URL == "http://localhost:9000"
        assert os.environ["APP_URL"] == "http://localhost:9000"
    finally:
        Settings.from_env.cache_clear()


def test_maps_settings_default_to_link_only_mode(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import MapsSettings

    monkeypatch.delenv("MAPS_ENABLE_EMBED", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_EMBED_API_KEY", raising=False)

    settings = MapsSettings()

    assert settings.ENABLE_EMBED is False
    assert not settings.EMBED_API_KEY
    assert settings.embed_enabled is False


def test_maps_settings_require_flag_and_separate_key(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import MapsSettings

    monkeypatch.setenv("MAPS_ENABLE_EMBED", "true")
    monkeypatch.delenv("GOOGLE_MAPS_EMBED_API_KEY", raising=False)

    assert MapsSettings().embed_enabled is False

    monkeypatch.setenv("GOOGLE_MAPS_EMBED_API_KEY", "maps-key")

    assert MapsSettings().embed_enabled is True
