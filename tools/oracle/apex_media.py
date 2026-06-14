# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Host-side Oracle APEX media staging.

The ``gvenzl/oracle-free`` container bundles neither APEX nor ORDS, so the APEX
release media must be acquired and staged on the host before any install
(install engine) or ORDS image serving can run. The APEX full release is a
public, no-login download from OTN
(``https://download.oracle.com/otn_software/apex/apex_<ver>.zip``), so the whole
pipeline is automatable.

This module performs **no database or container changes**; it only downloads,
verifies, extracts, and exposes the resolved host paths and container mount
specs that downstream chapters consume.
"""

from __future__ import annotations

import os
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

_FALSEY = {"0", "false", "no", "off", ""}
_DOWNLOAD_TIMEOUT_SECONDS = 600.0
_DOWNLOAD_CHUNK_BYTES = 1 << 20

# A fetcher streams ``url`` into ``dest`` and returns the server-declared
# Content-Length (or ``-1`` when the server omits it). Injected for testability.
Fetcher = Callable[[str, Path], int]


class ApexMediaError(RuntimeError):
    """Raised when APEX media cannot be acquired, verified, or extracted."""


@dataclass(frozen=True)
class ApexMediaPaths:
    """Resolved, absolute host paths for staged APEX media (consumed downstream)."""

    version: str
    apex_dir: Path
    images_dir: Path
    apexins: Path


@dataclass
class ApexMediaConfig:
    """Configuration for acquiring and staging APEX release media."""

    version: str = "26.1"
    english_only: bool = True
    cache_root: Path = Path("tools/oracle/downloads/apex")
    base_url: str = "https://download.oracle.com/otn_software/apex"

    @property
    def filename(self) -> str:
        """Release zip name (``apex_<ver>_en.zip`` for English, else ``apex_<ver>.zip``)."""
        suffix = "_en" if self.english_only else ""
        return f"apex_{self.version}{suffix}.zip"

    @property
    def url(self) -> str:
        """Public OTN download URL for the configured release."""
        return f"{self.base_url}/{self.filename}"

    @property
    def version_dir(self) -> Path:
        """Per-version cache directory under the host cache root."""
        return self.cache_root / self.version

    @property
    def archive_path(self) -> Path:
        """Where the downloaded zip is cached on the host."""
        return self.version_dir / self.filename

    @property
    def extracted_apex_dir(self) -> Path:
        """The extracted ``apex/`` tree (contains ``apexins.sql`` and ``images/``)."""
        return self.version_dir / "apex"

    @property
    def images_dir(self) -> Path:
        """The APEX static images directory served by ORDS at ``/i/``."""
        return self.extracted_apex_dir / "images"

    @property
    def apexins_path(self) -> Path:
        """The installer entrypoint script used to gate extraction integrity."""
        return self.extracted_apex_dir / "apexins.sql"

    @classmethod
    def from_env(cls) -> ApexMediaConfig:
        """Build config from environment, falling back to quiet defaults."""
        english = os.getenv("APEX_ENGLISH_ONLY", "true").strip().lower() not in _FALSEY
        return cls(
            version=os.getenv("APEX_VERSION", "26.1"),
            english_only=english,
            cache_root=Path(os.getenv("APEX_CACHE_ROOT", "tools/oracle/downloads/apex")),
        )


def _httpx_fetch(url: str, dest: Path) -> int:
    """Stream ``url`` into ``dest`` with a progress bar; return declared length or -1."""
    import httpx
    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        TextColumn,
        TransferSpeedColumn,
    )

    declared = -1
    with httpx.stream("GET", url, follow_redirects=True, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        length_header = response.headers.get("Content-Length")
        declared = int(length_header) if length_header is not None else -1
        with (
            dest.open("wb") as handle,
            Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
            ) as progress,
        ):
            total = declared if declared >= 0 else None
            task = progress.add_task(f"APEX {dest.name}", total=total)
            for chunk in response.iter_bytes(chunk_size=_DOWNLOAD_CHUNK_BYTES):
                handle.write(chunk)
                progress.update(task, advance=len(chunk))
    return declared


class ApexMedia:
    """Acquire, verify, extract, and stage APEX release media on the host."""

    def __init__(
        self,
        config: ApexMediaConfig | None = None,
        *,
        fetcher: Fetcher | None = None,
        console: Console | None = None,
    ) -> None:
        self.config = config or ApexMediaConfig()
        self._fetch = fetcher or _httpx_fetch
        self.console = console or Console()

    def download(self, *, force: bool = False) -> Path:
        """Download the APEX zip into the per-version cache, idempotently.

        A valid (non-empty) cached archive is reused unless ``force`` is set. A
        truncated or empty download fails loudly and the partial file is removed.
        """
        archive = self.config.archive_path
        if not force and archive.exists() and archive.stat().st_size > 0:
            return archive

        archive.parent.mkdir(parents=True, exist_ok=True)
        declared = self._fetch(self.config.url, archive)
        self._validate_size(archive, declared)
        return archive

    @staticmethod
    def _validate_size(archive: Path, declared: int) -> None:
        """Reject empty or size-mismatched downloads, removing the bad partial."""
        actual = archive.stat().st_size if archive.exists() else 0
        problem: str | None = None
        if actual == 0:
            problem = f"Downloaded APEX archive is empty: {archive}"
        elif declared >= 0 and actual != declared:
            problem = (
                f"APEX download size mismatch for {archive}: "
                f"expected {declared} bytes, received {actual}"
            )
        if problem is not None:
            archive.unlink(missing_ok=True)
            raise ApexMediaError(problem)

    def verify_zip(self) -> None:
        """Verify archive integrity and that it carries ``apex/apexins.sql``."""
        archive = self.config.archive_path
        if not archive.exists():
            raise ApexMediaError(f"APEX archive not found: {archive}")
        member = "apex/apexins.sql"
        try:
            with zipfile.ZipFile(archive) as bundle:
                bad = bundle.testzip()
                if bad is not None:
                    raise ApexMediaError(f"Corrupt member in APEX archive {archive}: {bad}")
                names = set(bundle.namelist())
        except zipfile.BadZipFile as exc:
            raise ApexMediaError(f"Not a valid zip archive: {archive}") from exc
        if member not in names:
            raise ApexMediaError(f"APEX archive {archive} is missing expected member {member}")

    def extract(self, *, force: bool = False) -> Path:
        """Extract the apex/ tree into the per-version cache, idempotently.

        Skips when ``apexins.sql`` is already present unless ``force`` is set, and
        gates on that member existing after extraction.
        """
        apex_dir = self.config.extracted_apex_dir
        if not force and self.config.apexins_path.exists():
            return apex_dir

        archive = self.config.archive_path
        if not archive.exists():
            raise ApexMediaError(f"APEX archive not found: {archive}")
        self.config.version_dir.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(self.config.version_dir)
        except zipfile.BadZipFile as exc:
            raise ApexMediaError(f"Not a valid zip archive: {archive}") from exc
        if not self.config.apexins_path.exists():
            raise ApexMediaError(
                f"APEX archive {archive} did not yield {self.config.apexins_path} after extraction"
            )
        return apex_dir

    def paths(self) -> ApexMediaPaths:
        """Return the resolved, absolute staging paths for downstream consumers."""
        return ApexMediaPaths(
            version=self.config.version,
            apex_dir=self.config.extracted_apex_dir.resolve(),
            images_dir=self.config.images_dir.resolve(),
            apexins=self.config.apexins_path.resolve(),
        )

    def container_mounts(
        self,
        *,
        db_target: str | None = None,
        ords_images_target: str | None = None,
    ) -> list[str]:
        """Return ``host:container`` bind-mount specs for Ch2 install / Ch3 ORDS.

        Pure data: this never starts a container. ``db_target`` mounts the whole
        ``apex/`` tree (so ``apexins.sql`` is reachable inside the DB container);
        ``ords_images_target`` mounts only ``images/`` for ORDS to serve at ``/i/``.
        Callers prepend ``-v`` and may append ``:ro`` as needed.
        """
        mounts: list[str] = []
        if db_target:
            mounts.append(f"{self.config.extracted_apex_dir.resolve()}:{db_target}")
        if ords_images_target:
            mounts.append(f"{self.config.images_dir.resolve()}:{ords_images_target}")
        return mounts
