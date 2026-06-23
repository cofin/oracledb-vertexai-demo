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

    def _exec_sysdba(self, sql: str, *, in_pdb: bool = True, workdir: str | None = None) -> str:
        """Run SQL inside the container as SYSDBA (optionally entering the PDB)."""
        preamble = f"ALTER SESSION SET CONTAINER={self.config.pdb};\n" if in_pdb else ""
        command = f"sqlplus -S -L / as sysdba <<'SQL'\n{preamble}{sql}\nexit\nSQL\n"
        if workdir is not None:
            command = f"cd {workdir} && {command}"
        _rc, stdout, _stderr = self.runtime.run_command(["exec", self.db.config.container_name, "bash", "-c", command])
        return stdout

    @staticmethod
    def _satisfies(installed: str, target: str) -> bool:
        """True when ``installed`` is in the ``target`` line (26.1.x satisfies 26.1)."""
        arity = len(target.split("."))
        truncated = ".".join(installed.split(".")[:arity])
        return compare_versions(truncated, target) == 0

    def _decide_action(self, installed: str | None, target: str, *, force: bool) -> str:
        """Decide skip / install / upgrade from the installed vs target versions."""
        if force or installed is None:
            return "install"
        arity = len(target.split("."))
        truncated = ".".join(installed.split(".")[:arity])
        comparison = compare_versions(truncated, target)
        if comparison == 0:
            return "skip"
        if comparison < 0:
            return "upgrade"
        # Installed is on a newer line than requested. Default: leave it (apexins
        # cannot downgrade). Flip to `raise ApexInstallError(...)` to make a
        # newer-than-target database a hard error instead.
        return "skip"

    def install(self, *, force: bool = False) -> str:
        """Install or upgrade APEX into the PDB, idempotently; return the version."""
        target = self.media.config.version
        installed = self.installed_version()
        action = self._decide_action(installed, target, force=force)
        if action == "skip":
            # _decide_action only returns "skip" for a known (non-None) installed version.
            current = installed or target
            self.console.print(f"[green]✓[/green] APEX {current} already satisfies target {target}; skipping.")
            return current

        verb = "Upgrading" if action == "upgrade" else "Installing"
        self.console.print(f"[cyan]{verb} APEX {target} into {self.config.pdb}...[/cyan]")
        self.stage_media(force=force)
        self._run_apexins()
        self._configure_rest()
        self.provision_workspace()

        result = self.installed_version()
        if result is None or not self._satisfies(result, target):
            raise ApexInstallError(f"APEX did not reach target {target} after install (got {result!r})")
        self.console.print(f"[green]✓[/green] APEX {result} ready in {self.config.pdb}.")
        return result

    def _run_apexins(self) -> None:
        """Run the APEX installer script as SYSDBA from the staged media dir."""
        apexins = f"{self.config.container_apex_dir}/apexins.sql"
        self._exec_sysdba(
            f"@{apexins} SYSAUX SYSAUX TEMP {self.config.images_url_path}", workdir=self.config.container_apex_dir
        )

    def _configure_rest(self) -> None:
        """Configure the ORDS/REST listener users non-interactively."""
        rest_script = f"{self.config.container_apex_dir}/apex_rest_config_core.sql"
        self._exec_sysdba(
            f"@{rest_script} {self.config.admin_password} {self.config.admin_password}",
            workdir=self.config.container_apex_dir,
        )

    def stage_media(self, *, force: bool = False) -> None:
        """Stage host APEX media into the container via ``docker cp`` (see Task 2.4)."""
        paths = self.media.ensure(force=force)
        container = self.db.config.container_name
        self.runtime.run_command(["exec", container, "mkdir", "-p", self.config.container_apex_dir])
        self.runtime.run_command(["cp", f"{paths.apex_dir}/.", f"{container}:{self.config.container_apex_dir}"])

    def provision_workspace(self) -> None:
        """Provision the COFFEE workspace + ADMIN dev user idempotently.

        Ported from the removed ``on_init/02_create_apex_workspace.sh``; idempotency
        is enforced in-DB via existence checks on ``apex_workspaces`` /
        ``apex_workspace_apex_users``, so re-running is a no-op.
        """
        workspace = self.config.workspace
        schema = self.config.primary_schema.upper()
        admin = self.config.admin_user
        password = self.config.admin_password
        privs = "ADMIN:CREATE:DATA_LOADER:EDIT:RUN:CONVERT"
        # Identifiers/passwords are config-controlled demo values, not external input (S608 N/A).
        ws_query = f"SELECT COUNT(*) INTO v_ws FROM apex_workspaces WHERE workspace = '{workspace}'"  # noqa: S608
        id_query = f"SELECT workspace_id INTO v_sgid FROM apex_workspaces WHERE workspace = '{workspace}'"  # noqa: S608
        user_query = f"SELECT COUNT(*) INTO v_user FROM apex_workspace_apex_users WHERE workspace_name = '{workspace}' AND user_name = '{admin}'"  # noqa: S608
        plsql = (
            "DECLARE\n"
            "  v_ws NUMBER; v_user NUMBER; v_sgid NUMBER;\n"
            "BEGIN\n"
            f"  {ws_query};\n"
            "  IF v_ws = 0 THEN\n"
            "    apex_instance_admin.add_workspace(\n"
            "      p_workspace_id   => NULL,\n"
            f"      p_workspace      => '{workspace}',\n"
            f"      p_primary_schema => '{schema}');\n"
            "    COMMIT;\n"
            "  END IF;\n"
            f"  {id_query};\n"
            "  apex_util.set_security_group_id(p_security_group_id => v_sgid);\n"
            f"  {user_query};\n"
            "  IF v_user = 0 THEN\n"
            "    apex_util.create_user(\n"
            f"      p_user_name                 => '{admin}',\n"
            f"      p_web_password              => '{password}',\n"
            f"      p_developer_privs           => '{privs}',\n"
            f"      p_default_schema            => '{schema}',\n"
            "      p_allow_app_building_yn     => 'Y',\n"
            "      p_allow_sql_workshop_yn     => 'Y',\n"
            "      p_allow_team_development_yn => 'Y');\n"
            "    COMMIT;\n"
            "  END IF;\n"
            "END;\n/\n"
        )
        output = self._exec_sysdba(plsql)
        if "ORA-" in output or "PLS-" in output:
            raise ApexInstallError(f"COFFEE workspace provisioning failed: {output.strip()}")

    def installed_version(self) -> str | None:
        """Return the installed APEX version in the PDB, or None when absent."""
        output = self._exec_sysdba(
            "SET HEADING OFF FEEDBACK OFF PAGESIZE 0 VERIFY OFF;\nSELECT version_no FROM apex_release;"
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
