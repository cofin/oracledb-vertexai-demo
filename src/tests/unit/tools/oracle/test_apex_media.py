# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the host-side APEX media staging pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.oracle.apex_media import ApexMedia, ApexMediaConfig, ApexMediaError


def _recording_fetcher(payload: bytes, declared: int | None = None):
    """A fake fetcher that writes ``payload`` to dest and reports ``declared`` length.

    ``declared=None`` means "report the real byte count" (a well-behaved server);
    an explicit int simulates a server-declared Content-Length (or ``-1`` unknown).
    """
    calls: list[str] = []

    def fetch(url: str, dest: Path) -> int:
        calls.append(url)
        dest.write_bytes(payload)
        return len(payload) if declared is None else declared

    fetch.calls = calls  # type: ignore[attr-defined]
    return fetch


def _exploding_fetcher():
    """A fetcher that fails the test if it is ever called (asserts a cache hit)."""

    def fetch(url: str, dest: Path) -> int:  # pragma: no cover - must not run
        raise AssertionError("fetcher must not be called on a cache hit")

    return fetch


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


def test_download_fetches_when_absent(tmp_path: Path) -> None:
    """A missing archive is fetched once and written to the per-version cache."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    fetcher = _recording_fetcher(b"PK\x03\x04 fake zip bytes")
    media = ApexMedia(config, fetcher=fetcher)

    archive = media.download()

    assert archive == config.archive_path
    assert archive.read_bytes() == b"PK\x03\x04 fake zip bytes"
    assert fetcher.calls == [config.url]


def test_download_creates_version_dir(tmp_path: Path) -> None:
    """The per-version cache directory is created on demand."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path / "nested" / "cache")
    media = ApexMedia(config, fetcher=_recording_fetcher(b"data"))

    media.download()

    assert config.version_dir.is_dir()


def test_download_skips_when_cached(tmp_path: Path) -> None:
    """A valid cached archive is reused without any network fetch."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    config.archive_path.parent.mkdir(parents=True)
    config.archive_path.write_bytes(b"already here")
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    archive = media.download()

    assert archive.read_bytes() == b"already here"


def test_download_force_refetches_cached(tmp_path: Path) -> None:
    """``force=True`` re-downloads even when a cached archive exists."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    config.archive_path.parent.mkdir(parents=True)
    config.archive_path.write_bytes(b"stale")
    fetcher = _recording_fetcher(b"fresh bytes")
    media = ApexMedia(config, fetcher=fetcher)

    media.download(force=True)

    assert config.archive_path.read_bytes() == b"fresh bytes"
    assert fetcher.calls == [config.url]


def test_download_raises_on_size_mismatch(tmp_path: Path) -> None:
    """A truncated download (declared != received) fails loudly and is removed."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    media = ApexMedia(config, fetcher=_recording_fetcher(b"12345", declared=100))

    with pytest.raises(ApexMediaError, match="size mismatch"):
        media.download()

    assert not config.archive_path.exists()


def test_download_raises_on_empty(tmp_path: Path) -> None:
    """An empty download is rejected and the zero-byte file removed."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    media = ApexMedia(config, fetcher=_recording_fetcher(b"", declared=-1))

    with pytest.raises(ApexMediaError, match="empty"):
        media.download()

    assert not config.archive_path.exists()


def test_download_accepts_unknown_content_length(tmp_path: Path) -> None:
    """A server that omits Content-Length (declared -1) is accepted when non-empty."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    media = ApexMedia(config, fetcher=_recording_fetcher(b"bytes without length", declared=-1))

    archive = media.download()

    assert archive.read_bytes() == b"bytes without length"
