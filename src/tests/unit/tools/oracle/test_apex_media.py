# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the host-side APEX media staging pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.oracle.apex_media import ApexMediaConfig


def test_config_defaults() -> None:
    """Default config targets APEX 26.1, English-only, gitignored host cache."""
    config = ApexMediaConfig()

    assert config.version == "26.1"
    assert config.english_only is True
    assert config.cache_root == Path("tools/oracle/downloads/apex")
    assert config.base_url == "https://download.oracle.com/otn_software/apex"


def test_filename_english_vs_full() -> None:
    """English-only yields the ``_en`` zip; full yields the plain zip."""
    assert ApexMediaConfig(version="26.1", english_only=True).filename == "apex_26.1_en.zip"
    assert ApexMediaConfig(version="26.1", english_only=False).filename == "apex_26.1.zip"


def test_url_is_public_otn_path() -> None:
    """The download URL is the public, no-login OTN location."""
    config = ApexMediaConfig(version="26.1", english_only=False)

    assert config.url == "https://download.oracle.com/otn_software/apex/apex_26.1.zip"


def test_derived_paths_for_default_version() -> None:
    """Per-version cache layout exposes the apex tree, images, archive, apexins."""
    config = ApexMediaConfig(version="26.1")

    assert config.version_dir == Path("tools/oracle/downloads/apex/26.1")
    assert config.archive_path == Path("tools/oracle/downloads/apex/26.1/apex_26.1_en.zip")
    assert config.extracted_apex_dir == Path("tools/oracle/downloads/apex/26.1/apex")
    assert config.images_dir == Path("tools/oracle/downloads/apex/26.1/apex/images")
    assert config.apexins_path == Path("tools/oracle/downloads/apex/26.1/apex/apexins.sql")


def test_derived_paths_for_future_version() -> None:
    """The same command serves a future version with no code change."""
    config = ApexMediaConfig(version="27.1", english_only=False)

    assert config.filename == "apex_27.1.zip"
    assert config.url == "https://download.oracle.com/otn_software/apex/apex_27.1.zip"
    assert config.version_dir == Path("tools/oracle/downloads/apex/27.1")
    assert config.apexins_path == Path("tools/oracle/downloads/apex/27.1/apex/apexins.sql")


def test_from_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """``from_env`` honours APEX_VERSION / APEX_ENGLISH_ONLY / APEX_CACHE_ROOT."""
    monkeypatch.setenv("APEX_VERSION", "27.2")
    monkeypatch.setenv("APEX_ENGLISH_ONLY", "false")
    monkeypatch.setenv("APEX_CACHE_ROOT", "/tmp/apex-cache")

    config = ApexMediaConfig.from_env()

    assert config.version == "27.2"
    assert config.english_only is False
    assert config.cache_root == Path("/tmp/apex-cache")
    assert config.filename == "apex_27.2.zip"


def test_from_env_defaults_to_quiet_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no env set, ``from_env`` matches the dataclass defaults."""
    for key in ("APEX_VERSION", "APEX_ENGLISH_ONLY", "APEX_CACHE_ROOT"):
        monkeypatch.delenv(key, raising=False)

    config = ApexMediaConfig.from_env()

    assert config.version == "26.1"
    assert config.english_only is True
    assert config.cache_root == Path("tools/oracle/downloads/apex")
