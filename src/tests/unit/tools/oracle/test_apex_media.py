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


def _make_zip(path: Path, members: dict[str, bytes]) -> None:
    """Write a real zip at ``path`` containing the given ``members``."""
    import zipfile

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def _good_members() -> dict[str, bytes]:
    return {
        "apex/apexins.sql": b"prompt installing APEX...\n",
        "apex/apex_rest_config.sql": b"-- rest config\n",
        "apex/images/get_started.png": b"\x89PNG fake",
    }


def test_verify_zip_accepts_good_archive(tmp_path: Path) -> None:
    """A well-formed zip containing apex/apexins.sql passes verification."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    _make_zip(config.archive_path, _good_members())
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    media.verify_zip()  # no raise


def test_verify_zip_rejects_corrupt_archive(tmp_path: Path) -> None:
    """Non-zip / corrupt bytes fail verification loudly."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    config.archive_path.parent.mkdir(parents=True)
    config.archive_path.write_bytes(b"not a real zip file at all")
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    with pytest.raises(ApexMediaError):
        media.verify_zip()


def test_verify_zip_rejects_missing_apexins(tmp_path: Path) -> None:
    """A valid zip lacking apexins.sql is rejected (wrong payload)."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    _make_zip(config.archive_path, {"apex/readme.txt": b"hi"})
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    with pytest.raises(ApexMediaError, match=r"apexins\.sql"):
        media.verify_zip()


def test_extract_writes_apex_tree(tmp_path: Path) -> None:
    """Extraction yields the apex/ tree with apexins.sql and images/."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    _make_zip(config.archive_path, _good_members())
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    apex_dir = media.extract()

    assert apex_dir == config.extracted_apex_dir
    assert config.apexins_path.exists()
    assert config.images_dir.is_dir()


def test_extract_skips_when_already_extracted(tmp_path: Path) -> None:
    """An existing apexins.sql means extraction is skipped (no archive needed)."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    config.extracted_apex_dir.mkdir(parents=True)
    config.apexins_path.write_bytes(b"already extracted")
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    apex_dir = media.extract()  # archive absent on purpose

    assert apex_dir == config.extracted_apex_dir
    assert config.apexins_path.read_bytes() == b"already extracted"


def test_extract_force_reextracts(tmp_path: Path) -> None:
    """``force=True`` re-extracts over a stale tree."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    config.extracted_apex_dir.mkdir(parents=True)
    config.apexins_path.write_bytes(b"stale")
    _make_zip(config.archive_path, _good_members())
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    media.extract(force=True)

    assert config.apexins_path.read_bytes() == b"prompt installing APEX...\n"


def test_extract_raises_when_apexins_absent_after(tmp_path: Path) -> None:
    """A valid zip without apexins.sql fails the post-extract gate."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    _make_zip(config.archive_path, {"apex/readme.txt": b"hi"})
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    with pytest.raises(ApexMediaError):
        media.extract()


def test_paths_returns_resolved_absolute_paths(tmp_path: Path) -> None:
    """paths() exposes resolved, absolute host paths plus the version string."""
    config = ApexMediaConfig(version="26.1", cache_root=Path("tools/oracle/downloads/apex"))
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    paths = media.paths()

    assert paths.version == "26.1"
    assert paths.apex_dir.is_absolute()
    assert paths.images_dir.is_absolute()
    assert paths.apexins.is_absolute()
    assert paths.apex_dir == config.extracted_apex_dir.resolve()
    assert paths.images_dir == config.images_dir.resolve()
    assert paths.apexins == config.apexins_path.resolve()


def test_paths_is_frozen(tmp_path: Path) -> None:
    """ApexMediaPaths is immutable so the staging contract can't be mutated."""
    from dataclasses import FrozenInstanceError

    media = ApexMedia(ApexMediaConfig(cache_root=tmp_path), fetcher=_exploding_fetcher())
    paths = media.paths()

    with pytest.raises(FrozenInstanceError):
        paths.version = "99.9"  # type: ignore[misc]


def test_container_mounts_db_target(tmp_path: Path) -> None:
    """A db_target maps the apex/ tree to an absolute host:container spec."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    mounts = media.container_mounts(db_target="/opt/oracle/apex")

    assert mounts == [f"{config.extracted_apex_dir.resolve()}:/opt/oracle/apex"]


def test_container_mounts_ords_images_target(tmp_path: Path) -> None:
    """An ords_images_target maps images/ to the ORDS /i/ location."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    mounts = media.container_mounts(ords_images_target="/opt/oracle/apex/images")

    assert mounts == [f"{config.images_dir.resolve()}:/opt/oracle/apex/images"]


def test_container_mounts_both_targets_in_order(tmp_path: Path) -> None:
    """Both targets produce both mounts (db first, then ords images)."""
    config = ApexMediaConfig(version="26.1", cache_root=tmp_path)
    media = ApexMedia(config, fetcher=_exploding_fetcher())

    mounts = media.container_mounts(
        db_target="/opt/oracle/apex",
        ords_images_target="/opt/oracle/apex/images",
    )

    assert mounts == [
        f"{config.extracted_apex_dir.resolve()}:/opt/oracle/apex",
        f"{config.images_dir.resolve()}:/opt/oracle/apex/images",
    ]


def test_container_mounts_empty_without_targets(tmp_path: Path) -> None:
    """No targets means no mounts (pure data contract, nothing applied)."""
    media = ApexMedia(ApexMediaConfig(cache_root=tmp_path), fetcher=_exploding_fetcher())

    assert media.container_mounts() == []


def test_downloads_dir_is_gitignored() -> None:
    """The host media cache must never be committed."""
    repo_root = Path(__file__).resolve().parents[5]
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")

    assert "tools/oracle/downloads/" in gitignore
