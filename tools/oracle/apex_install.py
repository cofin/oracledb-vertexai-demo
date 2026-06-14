# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Idempotent Oracle APEX install/upgrade engine for the gvenzl container.

gvenzl/oracle-free permits SYSDBA OS-auth inside the container
(``sqlplus / as sysdba``), so APEX installs via the standard ``apexins.sql``
path. This engine stages Ch1 media into the container with ``docker cp`` and
runs the SYSDBA scripts via ``docker exec`` — it never modifies the
``OracleDatabase`` lifecycle class.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from tools.oracle.apex_media import ApexMedia
    from tools.oracle.container import ContainerRuntime
    from tools.oracle.database import OracleDatabase


class ApexInstallError(RuntimeError):
    """Raised when an APEX install/upgrade step fails."""


def _version_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted version into a tuple of ints (non-digits dropped per chunk)."""
    parts: list[int] = []
    for chunk in version.strip().split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def compare_versions(left: str, right: str) -> int:
    """Component-wise version compare; returns -1/0/1.

    Differing arity is zero-padded so ``26.1`` and ``26.1.0`` compare equal.
    """
    lt, rt = _version_tuple(left), _version_tuple(right)
    width = max(len(lt), len(rt))
    padded_left = lt + (0,) * (width - len(lt))
    padded_right = rt + (0,) * (width - len(rt))
    return (padded_left > padded_right) - (padded_left < padded_right)


@dataclass
class ApexInstallConfig:
    """Configuration for installing/upgrading APEX into the gvenzl PDB."""

    pdb: str = "FREEPDB1"
    # Staging path *inside* the ephemeral container (docker cp target read by SYSDBA),
    # not a host temp file — the S108 heuristic does not apply here.
    container_apex_dir: str = "/tmp/apex"  # noqa: S108
    images_url_path: str = "/i/"
    admin_user: str = "ADMIN"
    admin_password: str = "SuperSecret1"  # noqa: S105
    workspace: str = "COFFEE"
    primary_schema: str = "app"

    @classmethod
    def from_env(cls) -> ApexInstallConfig:
        """Build config from environment with quiet demo defaults."""
        return cls(
            admin_password=os.getenv("APEX_ADMIN_PASSWORD", os.getenv("DATABASE_PASSWORD", "SuperSecret1")),
            primary_schema=os.getenv("DATABASE_USER", "app"),
        )


class ApexInstaller:
    """Install/upgrade APEX via container SYSDBA, consuming Ch1 staged media."""

    def __init__(
        self,
        runtime: ContainerRuntime,
        db: OracleDatabase,
        media: ApexMedia,
        config: ApexInstallConfig | None = None,
        console: Console | None = None,
    ) -> None:
        self.runtime = runtime
        self.db = db
        self.media = media
        self.config = config or ApexInstallConfig()
        self.console = console or Console()

    def _exec_sysdba(self, sql: str, *, in_pdb: bool = True) -> str:
        """Run SQL inside the container as SYSDBA (optionally entering the PDB)."""
        preamble = f"ALTER SESSION SET CONTAINER={self.config.pdb};\n" if in_pdb else ""
        script = f"sqlplus -S -L / as sysdba <<'SQL'\n{preamble}{sql}\nexit\nSQL\n"
        _rc, stdout, _stderr = self.runtime.run_command(
            ["exec", self.db.config.container_name, "bash", "-c", script]
        )
        return stdout

    def installed_version(self) -> str | None:
        """Return the installed APEX version in the PDB, or None when absent."""
        output = self._exec_sysdba(
            "SET HEADING OFF FEEDBACK OFF PAGESIZE 0 VERIFY OFF;\nSELECT version FROM apex_release;"
        )
        text = output.strip()
        if "ORA-00942" in text:
            return None
        if "ORA-" in text:
            raise ApexInstallError(f"Failed to query APEX version in {self.config.pdb}: {text}")
        for line in text.splitlines():
            candidate = line.strip()
            if candidate and candidate[0].isdigit():
                return candidate
        return None
