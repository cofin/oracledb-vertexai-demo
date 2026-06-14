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
from dataclasses import dataclass
from pathlib import Path

_FALSEY = {"0", "false", "no", "off", ""}


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
