# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""APEXlang source lifecycle wrapper for SQLcl."""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from tools.oracle.adb import ADB_FREE_DEFAULT_SERVICE
from tools.oracle.database import PDB_SERVICE_NAME, ContainerFlavor, DatabaseConfig
from tools.oracle.sqlcl_installer import SQLclInstaller

__all__ = (
    "DEFAULT_APEX_ALIAS",
    "MINIMUM_APEXLANG_SQLCL",
    "SQLCL_FATAL_OUTPUT_MARKERS",
    "ApexLang",
    "ApexLangConfig",
    "ApexLangError",
    "ApexLangResult",
)

DEFAULT_APEX_ALIAS = "cymbal-coffee-ops"
MINIMUM_APEXLANG_SQLCL = "26.1.2"
SQLCL_FATAL_OUTPUT_MARKERS = (
    "APEXLang Compile Errors:",
    "APEXLang Import Errors:",
    "Connection failed",
    "SP2-0640: Not connected",
)
_DEFAULT_DEV_SECRET = "SuperSecret1"  # ruff: ignore[hardcoded-password-string]


class ApexLangError(RuntimeError):
    """Raised when an APEXlang lifecycle command cannot complete."""


@dataclass(slots=True)
class ApexLangConfig:
    """Configuration for local APEXlang lifecycle commands."""

    src_root: Path = Path("src/apex")
    host: str = "localhost"
    port: int = 1521
    service_name: str = PDB_SERVICE_NAME
    user: str = "app"
    password: str = _DEFAULT_DEV_SECRET
    wallet_location: Path | None = None
    tns_alias: str | None = None
    minimum_sqlcl: str = MINIMUM_APEXLANG_SQLCL

    @classmethod
    def from_env(cls) -> ApexLangConfig:
        """Build config from the local Oracle container or wallet environment."""
        db = DatabaseConfig.from_env()
        raw_wallet = (os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN") or "").strip()
        raw_host = (os.getenv("DATABASE_HOST") or "").strip()
        raw_url = (os.getenv("DATABASE_URL") or "").strip()
        url_alias = raw_url if raw_url and "://" not in raw_url and ":" not in raw_url and "/" not in raw_url else None

        wallet_location: Path | None = None
        if raw_wallet:
            wallet_location = Path(raw_wallet)
        elif db.flavor == ContainerFlavor.ADB_FREE and (url_alias is not None or not raw_host):
            wallet_location = db.wallet_dir

        tns_alias: str | None = None
        service_name = db.service_name
        if wallet_location is not None:
            tns_alias = url_alias or db.service_name or ADB_FREE_DEFAULT_SERVICE
            service_name = tns_alias

        return cls(
            host=raw_host or "localhost",
            port=db.host_port,
            service_name=service_name,
            user=db.app_user,
            password=db.app_user_password,
            wallet_location=wallet_location,
            tns_alias=tns_alias,
        )


@dataclass(frozen=True, slots=True)
class ApexLangResult:
    """Result from an APEXlang SQLcl command."""

    command: str
    target_path: Path
    stdout: str
    stderr: str


class ApexLang:
    """Run SQLcl APEXlang generate/export/validate/import commands."""

    def __init__(
        self,
        *,
        installer: SQLclInstaller | None = None,
        config: ApexLangConfig | None = None,
        console: Console | None = None,
    ) -> None:
        self.installer = installer or SQLclInstaller()
        self.config = config or ApexLangConfig.from_env()
        self.console = console or Console()

    def generate(
        self,
        *,
        alias: str = DEFAULT_APEX_ALIAS,
        app_name: str | None = None,
        app_id: int | None = None,
        workspace: str | None = None,
        schema: str | None = None,
        force: bool = False,
    ) -> ApexLangResult:
        """Generate starter APEXlang files."""
        target = self.target_path(alias)
        parts = ["generate", "-dir", str(self.config.src_root), "-alias", alias]
        if app_name:
            parts.extend(["-name", app_name])
        if app_id is not None:
            parts.extend(["-id", str(app_id)])
        if workspace:
            parts.extend(["-workspace", workspace])
        if schema:
            parts.extend(["-schema", schema])
        if force:
            parts.append("-force")
        return self._run_apex(parts, target_path=target)

    def export(self, *, app_id: int, alias: str = DEFAULT_APEX_ALIAS, clean: bool = True) -> ApexLangResult:
        """Export an APEX application as APEXlang source."""
        target = self.target_path(alias)
        parts = ["export", "-applicationid", str(app_id), "-exptype", "APEXLANG", "-dir", str(self.config.src_root)]
        if clean:
            parts.append("-force")
        return self._run_apex(parts, target_path=target)

    def validate(
        self,
        *,
        alias: str = DEFAULT_APEX_ALIAS,
        input_path: Path | None = None,
        workspace: str | None = None,
        deployment: str | None = None,
        debug: bool = False,
    ) -> ApexLangResult:
        """Validate APEXlang source."""
        target = input_path or self.target_path(alias)
        parts = ["validate", "-input", str(target)]
        if workspace:
            parts.extend(["-workspace", workspace])
        if deployment:
            parts.extend(["-deployment", deployment])
        if debug:
            parts.append("-debug")
        return self._run_apex(parts, target_path=target, connect=False)

    def import_app(
        self,
        *,
        alias: str = DEFAULT_APEX_ALIAS,
        input_path: Path | None = None,
        workspace: str | None = None,
        schema: str | None = None,
        app_id: int | None = None,
        app_name: str | None = None,
        deployment: str | None = None,
        debug: bool = False,
    ) -> ApexLangResult:
        """Import APEXlang source into APEX."""
        target = input_path or self.target_path(alias)
        parts = ["import", "-input", str(target)]
        if workspace:
            parts.extend(["-workspace", workspace])
        if schema:
            parts.extend(["-schema", schema])
        if app_id is not None:
            parts.extend(["-id", str(app_id)])
        if app_name:
            parts.extend(["-name", app_name])
        if deployment:
            parts.extend(["-deployment", deployment])
        if debug:
            parts.append("-debug")
        return self._run_apex(parts, target_path=target)

    def target_path(self, alias: str) -> Path:
        """Return the local APEXlang source directory for an app alias."""
        return self.config.src_root / alias

    def _sql_path(self) -> Path:
        """Resolve SQLcl and enforce APEXlang support."""
        status = self.installer.apexlang_status(minimum=self.config.minimum_sqlcl)
        if not status.capable:
            raise ApexLangError(status.message)
        sql_path = self.installer.sql_path()
        if sql_path is None:
            raise ApexLangError("SQLcl is not installed. Run: uv run python manage.py install sqlcl")
        return sql_path

    def _connect_line(self) -> str:
        """Build the SQLcl connection command sent over stdin."""
        escaped_pw = self.config.password.replace('"', '""')
        if self.config.wallet_location is not None:
            alias = self.config.tns_alias or ADB_FREE_DEFAULT_SERVICE
            return f'connect {self.config.user}/"{escaped_pw}"@{alias}'
        dsn = f"//{self.config.host}:{self.config.port}/{self.config.service_name}"
        return f'connect {self.config.user}/"{escaped_pw}"@{dsn}'

    def _run_apex(self, parts: list[str], *, target_path: Path, connect: bool = True) -> ApexLangResult:
        """Run one SQLcl APEX command."""
        sql_path = self._sql_path()
        command = "apex " + " ".join(shlex.quote(part) for part in parts)
        script = f"{self._connect_line()}\n{command}\nexit\n" if connect else f"{command}\nexit\n"
        run_env = (
            {**os.environ, "TNS_ADMIN": str(self.config.wallet_location.resolve())}
            if self.config.wallet_location is not None
            else None
        )
        result = subprocess.run(
            [str(sql_path), "-S", "/nolog"], input=script, capture_output=True, text=True, check=False, env=run_env
        )
        output = f"{result.stdout}\n{result.stderr}"
        if result.returncode != 0 or self._has_sqlcl_fatal_output(output):
            raise ApexLangError(result.stderr.strip() or result.stdout.strip() or "SQLcl APEXlang command failed")
        return ApexLangResult(command=command, target_path=target_path, stdout=result.stdout, stderr=result.stderr)

    @staticmethod
    def _has_sqlcl_fatal_output(output: str) -> bool:
        """Return true for SQLcl errors that can still exit with status zero."""
        return any(marker in output for marker in SQLCL_FATAL_OUTPUT_MARKERS)
