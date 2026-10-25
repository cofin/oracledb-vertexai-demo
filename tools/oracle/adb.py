# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle Autonomous AI Database Free 26ai wallet export and ADMIN bootstrap."""

from __future__ import annotations

import http.client
import os
import re
import ssl
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import oracledb
from rich.console import Console
from sqlspec.adapters.oracledb import extract_oracle_wallet_zip, parse_tnsnames_ora

if TYPE_CHECKING:
    from tools.oracle.container import ContainerRuntime

__all__ = (
    "ADB_FREE_CONTAINER_NAME",
    "ADB_FREE_DATA_VOLUME",
    "ADB_FREE_DEFAULT_IMAGE",
    "ADB_FREE_DEFAULT_SERVICE",
    "ADB_FREE_WALLET_CONTAINER_PATH",
    "AdbBootstrap",
    "AdbBootstrapConfig",
    "AdbBootstrapError",
    "AdbBootstrapResult",
)

ADB_FREE_DEFAULT_IMAGE = "container-registry.oracle.com/database/adb-free:latest-26ai"
ADB_FREE_CONTAINER_NAME = "cymbal-adb-free"
ADB_FREE_DATA_VOLUME = "cymbal-adb-data"
ADB_FREE_DEFAULT_SERVICE = "myatp_low"
ADB_FREE_WALLET_CONTAINER_PATH = "/u01/app/oracle/wallets/tls_wallet"
_DEFAULT_DEV_SECRET = "SuperSecret1"  # ruff: ignore[hardcoded-password-string]
_HTTP_OK_MIN = 200
_HTTP_SERVER_ERROR_MIN = 500

_ORACLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]*$")
_TNS_HOST_RE = re.compile(r"\(\s*HOST\s*=\s*[^)]+\)", flags=re.IGNORECASE)
_TNS_PORT_RE = re.compile(r"\(\s*PORT\s*=\s*\d+\s*\)", flags=re.IGNORECASE)
_SQLNET_DIR_RE = re.compile(r'DIRECTORY\s*=\s*"?[^")]+"?', flags=re.IGNORECASE)


class AdbBootstrapError(Exception):
    """Raised when ADB-Free wallet export or ADMIN schema provisioning fails."""


@dataclass(frozen=True, slots=True)
class AdbBootstrapConfig:
    """Configuration for ADB-Free 26ai wallet export and schema provisioning."""

    container_name: str = ADB_FREE_CONTAINER_NAME
    wallet_dir: Path = Path(".envs/tns")
    wallet_password: str = _DEFAULT_DEV_SECRET
    admin_password: str = _DEFAULT_DEV_SECRET
    app_user: str = "app"
    app_password: str = _DEFAULT_DEV_SECRET
    service_name: str = ADB_FREE_DEFAULT_SERVICE
    tls_port: int = 1522
    https_port: int = 8443
    workspace_name: str = "COFFEE"

    @classmethod
    def from_env(cls) -> AdbBootstrapConfig:
        """Build bootstrap configuration from environment variables."""
        wallet_loc = os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN") or ".envs/tns"
        raw_url = (os.getenv("DATABASE_URL") or "").strip()
        service_name = (
            raw_url
            if raw_url and "://" not in raw_url and ":" not in raw_url and "/" not in raw_url
            else os.getenv("DATABASE_SERVICE_NAME", ADB_FREE_DEFAULT_SERVICE)
        )
        if service_name.lower() == "freepdb1":
            service_name = ADB_FREE_DEFAULT_SERVICE
        admin_pw = (
            os.getenv("ORACLE_ADMIN_PASSWORD")
            or os.getenv("DATABASE_ADMIN_PASSWORD")
            or os.getenv("ORACLE_PASSWORD")
            or "SuperSecret1"
        )
        return cls(
            container_name=os.getenv("ORACLE_CONTAINER_NAME", ADB_FREE_CONTAINER_NAME),
            wallet_dir=Path(wallet_loc),
            wallet_password=os.getenv("WALLET_PASSWORD", "SuperSecret1"),
            admin_password=admin_pw,
            app_user=os.getenv("DATABASE_USER", "app"),
            app_password=os.getenv("DATABASE_PASSWORD", "SuperSecret1"),
            service_name=service_name,
            tls_port=int(os.getenv("ORACLE_TLS_PORT", "1522")),
            https_port=int(os.getenv("ORACLE_HTTPS_PORT", "8443")),
            workspace_name=os.getenv("APEX_WORKSPACE", "COFFEE"),
        )


@dataclass(frozen=True, slots=True)
class AdbBootstrapResult:
    """Summary of exported mTLS wallet and provisioned APEX/ORDS endpoints."""

    wallet_dir: Path
    services: tuple[str, ...]
    app_user: str
    workspace_name: str
    ords_url: str
    apex_url: str
    sql_developer_url: str


class AdbBootstrap:
    """Export the ADB-Free mTLS wallet and provision the Cymbal Coffee schema and APEX workspace."""

    def __init__(
        self, runtime: ContainerRuntime, config: AdbBootstrapConfig | None = None, console: Console | None = None
    ) -> None:
        """Initialize the bootstrap orchestrator."""
        self.runtime = runtime
        self.config = config or AdbBootstrapConfig.from_env()
        self.console = console or Console()

    def export_wallet(self, source: Path | None = None) -> tuple[Path, list[str]]:
        """Export or extract the mTLS wallet into ``config.wallet_dir`` and validate TNS aliases.

        Args:
            source: Optional local wallet ``.zip`` archive or directory. When omitted,
                copies ``/u01/app/oracle/wallets/tls_wallet`` from the running container.

        Returns:
            Tuple of ``(resolved_wallet_dir, sorted_service_names)``.

        Raises:
            AdbBootstrapError: If wallet files are missing or ``tnsnames.ora`` has no services.
        """
        target_dir = self.config.wallet_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            if source is not None:
                resolved_dir = extract_oracle_wallet_zip(
                    source, target_dir, wallet_password=self.config.wallet_password
                )
            else:
                self.runtime.copy_from_container(
                    self.config.container_name, f"{ADB_FREE_WALLET_CONTAINER_PATH}/.", target_dir
                )
                resolved_dir = extract_oracle_wallet_zip(
                    target_dir, target_dir, wallet_password=self.config.wallet_password
                )
        except Exception as exc:
            raise AdbBootstrapError(f"Failed to export ADB-Free wallet to {target_dir}: {exc}") from exc

        tnsnames_path = resolved_dir / "tnsnames.ora"
        if not tnsnames_path.is_file():
            raise AdbBootstrapError(f"Wallet directory {resolved_dir} is missing tnsnames.ora")

        self._normalize_wallet_network_files(resolved_dir)
        parsed = parse_tnsnames_ora(tnsnames_path)
        services = sorted(parsed)
        if not services:
            raise AdbBootstrapError(f"No TNS service aliases found in {tnsnames_path}")
        return resolved_dir, services

    def wait_for_ready(self, timeout: int = 360) -> bool:
        """Poll until the container wallet, mTLS listener, and ORDS HTTPS endpoint are ready."""
        deadline = time.monotonic() + timeout
        wallet_exported = False
        while time.monotonic() < deadline:
            if not wallet_exported and self._container_wallet_exists():
                try:
                    self.export_wallet()
                    wallet_exported = True
                except AdbBootstrapError:
                    wallet_exported = False
            if wallet_exported and self._can_connect_as_admin() and self._is_ords_https_ready():
                return True
            time.sleep(5)
        return False

    def provision_schema_and_workspace(self) -> None:
        """Idempotently provision user ``APP``, ORDS REST access, and the ``COFFEE`` APEX workspace."""
        app_user = _validate_oracle_identifier(self.config.app_user)
        wallet_path = str(self.config.wallet_dir.resolve())
        try:
            self._execute_admin_provisioning(app_user=app_user, wallet_path=wallet_path)
        except Exception as exc:
            raise AdbBootstrapError(f"Failed to provision ADB-Free schema and APEX workspace: {exc}") from exc

    def bootstrap(self, *, timeout: int = 360) -> AdbBootstrapResult:
        """Wait for container readiness, export the wallet, and provision ``APP`` + ``COFFEE``."""
        if not self.wait_for_ready(timeout=timeout):
            raise AdbBootstrapError(
                f"Timed out after {timeout}s waiting for {self.config.container_name} wallet and ORDS readiness."
            )
        wallet_dir, services = self.export_wallet()
        self.provision_schema_and_workspace()
        ords_base = f"https://localhost:{self.config.https_port}/ords"
        return AdbBootstrapResult(
            wallet_dir=wallet_dir,
            services=tuple(services),
            app_user=self.config.app_user,
            workspace_name=self.config.workspace_name,
            ords_url=f"{ords_base}/",
            apex_url=f"{ords_base}/apex",
            sql_developer_url=f"{ords_base}/sql-developer",
        )

    def _execute_admin_provisioning(self, *, app_user: str, wallet_path: str) -> None:
        """Run user, grant, ORDS, and APEX workspace PL/SQL blocks as ``ADMIN``."""
        create_or_update_user_plsql = (
            "DECLARE\n"
            "    v_user   VARCHAR2(128) := DBMS_ASSERT.SIMPLE_SQL_NAME(:schema_name);\n"
            "    v_quoted VARCHAR2(512) := '\"' || REPLACE(:app_password, '\"', '\"\"') || '\"';\n"
            "    v_count  NUMBER := 0;\n"
            "BEGIN\n"
            "    SELECT COUNT(*) INTO v_count FROM dba_users WHERE username = UPPER(v_user);\n"
            "    IF v_count = 0 THEN\n"
            "        EXECUTE IMMEDIATE 'CREATE USER ' || v_user || ' IDENTIFIED BY ' || v_quoted\n"
            "            || ' DEFAULT TABLESPACE DATA TEMPORARY TABLESPACE TEMP QUOTA UNLIMITED ON DATA';\n"
            "    ELSE\n"
            "        EXECUTE IMMEDIATE 'ALTER USER ' || v_user || ' IDENTIFIED BY ' || v_quoted || ' ACCOUNT UNLOCK';\n"
            "    END IF;\n"
            "    EXECUTE IMMEDIATE 'GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO ' || v_user;\n"
            "    EXECUTE IMMEDIATE 'GRANT CREATE MINING MODEL TO ' || v_user;\n"
            "    FOR rec IN (\n"
            "        SELECT COLUMN_VALUE AS grant_clause\n"
            "          FROM TABLE(SYS.ODCIVARCHAR2LIST(\n"
            "              'CONSOLE_DEVELOPER',\n"
            "              'DWROLE',\n"
            "              'DB_DEVELOPER_ROLE',\n"
            "              'SELECT ON V_$TRANSACTION',\n"
            "              'EXECUTE ON DBMS_CLOUD_AI'\n"
            "          ))\n"
            "    ) LOOP\n"
            "        BEGIN\n"
            "            EXECUTE IMMEDIATE 'GRANT ' || rec.grant_clause || ' TO ' || v_user;\n"
            "        EXCEPTION\n"
            "            WHEN OTHERS THEN\n"
            "                IF SQLCODE NOT IN (-1919, -4042, -942) THEN\n"
            "                    RAISE;\n"
            "                END IF;\n"
            "        END;\n"
            "    END LOOP;\n"
            "END;"
        )

        enable_ords_plsql = (
            "BEGIN\n"
            "    ORDS.ENABLE_SCHEMA(\n"
            "        p_enabled             => TRUE,\n"
            "        p_schema              => :schema_name,\n"
            "        p_url_mapping_type    => 'BASE_PATH',\n"
            "        p_url_mapping_pattern => LOWER(:schema_name),\n"
            "        p_auto_rest_auth      => FALSE\n"
            "    );\n"
            "END;"
        )

        provision_workspace_plsql = (
            "DECLARE\n"
            "    v_ws_count   NUMBER := 0;\n"
            "    v_ws_id      NUMBER;\n"
            "    v_user_count NUMBER := 0;\n"
            "BEGIN\n"
            "    SELECT COUNT(*)\n"
            "      INTO v_ws_count\n"
            "      FROM apex_workspaces\n"
            "     WHERE workspace = UPPER(:workspace_name);\n"
            "    IF v_ws_count = 0 THEN\n"
            "        APEX_INSTANCE_ADMIN.ADD_WORKSPACE(\n"
            "            p_workspace      => UPPER(:workspace_name),\n"
            "            p_primary_schema => UPPER(:schema_name)\n"
            "        );\n"
            "    ELSE\n"
            "        BEGIN\n"
            "            APEX_INSTANCE_ADMIN.ADD_SCHEMA(\n"
            "                p_workspace => UPPER(:workspace_name),\n"
            "                p_schema    => UPPER(:schema_name)\n"
            "            );\n"
            "        EXCEPTION\n"
            "            WHEN OTHERS THEN\n"
            "                NULL;\n"
            "        END;\n"
            "    END IF;\n"
            "    v_ws_id := APEX_UTIL.FIND_SECURITY_GROUP_ID(p_workspace => UPPER(:workspace_name));\n"
            "    IF v_ws_id IS NOT NULL THEN\n"
            "        APEX_UTIL.SET_SECURITY_GROUP_ID(p_security_group_id => v_ws_id);\n"
            "        SELECT COUNT(*)\n"
            "          INTO v_user_count\n"
            "          FROM apex_workspace_apex_users\n"
            "         WHERE workspace_name = UPPER(:workspace_name)\n"
            "           AND user_name = UPPER(:schema_name);\n"
            "        IF v_user_count = 0 THEN\n"
            "            APEX_UTIL.CREATE_USER(\n"
            "                p_user_name                    => UPPER(:schema_name),\n"
            "                p_web_password                 => :app_password,\n"
            "                p_email_address                => LOWER(:schema_name) || '@cymbalcoffee.example',\n"
            "                p_developer_privs              => 'ADMIN:CREATE:DATA_LOADER:EDIT:HELP:MONITOR:SQL',\n"
            "                p_default_schema               => UPPER(:schema_name),\n"
            "                p_change_password_on_first_use => 'N'\n"
            "            );\n"
            "        ELSE\n"
            "            APEX_UTIL.RESET_PASSWORD(\n"
            "                p_user_name           => UPPER(:schema_name),\n"
            "                p_new_password        => :app_password,\n"
            "                p_change_on_first_use => FALSE\n"
            "            );\n"
            "        END IF;\n"
            "    END IF;\n"
            "END;"
        )

        with oracledb.connect(
            user="ADMIN",
            password=self.config.admin_password,
            dsn=self.config.service_name,
            config_dir=wallet_path,
            wallet_location=wallet_path,
            wallet_password=self.config.wallet_password,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(create_or_update_user_plsql, schema_name=app_user, app_password=self.config.app_password)
                cursor.execute(enable_ords_plsql, schema_name=app_user)
                cursor.execute(
                    provision_workspace_plsql,
                    workspace_name=self.config.workspace_name,
                    schema_name=app_user,
                    app_password=self.config.app_password,
                )
            connection.commit()

    def _normalize_wallet_network_files(self, wallet_dir: Path) -> None:
        """Rewrite container-internal hostnames in ``tnsnames.ora`` and wallet directory in ``sqlnet.ora``."""
        tnsnames_path = wallet_dir / "tnsnames.ora"
        raw_tns = tnsnames_path.read_text(encoding="utf-8")
        normalized_tns = _TNS_HOST_RE.sub("(HOST=localhost)", raw_tns)
        normalized_tns = _TNS_PORT_RE.sub(f"(PORT={self.config.tls_port})", normalized_tns)
        tnsnames_path.write_text(normalized_tns, encoding="utf-8")

        sqlnet_path = wallet_dir / "sqlnet.ora"
        if sqlnet_path.is_file():
            raw_sqlnet = sqlnet_path.read_text(encoding="utf-8")
            normalized_sqlnet = _SQLNET_DIR_RE.sub(f'DIRECTORY="{wallet_dir.resolve()}"', raw_sqlnet)
            sqlnet_path.write_text(normalized_sqlnet, encoding="utf-8")

    def _container_wallet_exists(self) -> bool:
        """Return True once ``adb-free`` has generated ``tnsnames.ora`` inside the container."""
        returncode, _, _ = self.runtime.run_command(
            ["exec", self.config.container_name, "test", "-f", f"{ADB_FREE_WALLET_CONTAINER_PATH}/tnsnames.ora"],
            check=False,
        )
        return returncode == 0

    def _can_connect_as_admin(self) -> bool:
        """Return True when ``ADMIN`` can execute ``SELECT 1 FROM DUAL`` over mTLS."""
        wallet_path = str(self.config.wallet_dir.resolve())
        try:
            with (
                oracledb.connect(
                    user="ADMIN",
                    password=self.config.admin_password,
                    dsn=self.config.service_name,
                    config_dir=wallet_path,
                    wallet_location=wallet_path,
                    wallet_password=self.config.wallet_password,
                ) as connection,
                connection.cursor() as cursor,
            ):
                cursor.execute("SELECT 1 FROM DUAL")
                cursor.fetchone()
        except Exception:
            return False
        return True

    def _is_ords_https_ready(self) -> bool:
        """Return True when ORDS responds on ``https://localhost:<https_port>/ords/``."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        conn = http.client.HTTPSConnection("localhost", self.config.https_port, timeout=5, context=ssl_context)
        try:
            conn.request("GET", "/ords/")
            response = conn.getresponse()
            return _HTTP_OK_MIN <= response.status < _HTTP_SERVER_ERROR_MIN
        except Exception:
            return False
        finally:
            conn.close()


def _validate_oracle_identifier(value: str) -> str:
    """Validate and uppercase an Oracle identifier before passing it to DDL provisioning."""
    if not _ORACLE_IDENTIFIER_RE.fullmatch(value):
        raise AdbBootstrapError(f"Invalid Oracle identifier: {value!r}")
    return value.upper()
