# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Direct Vertex AI and Litestar gateway Generative AI Service provisioning for Oracle APEX 26.1."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import google.auth
import oracledb
from google.auth.transport.requests import Request as GoogleAuthRequest
from sqlspec.adapters.oracledb import extract_oracle_wallet_zip

from tools.oracle.adb import ADB_FREE_DEFAULT_SERVICE

__all__ = (
    "ApexVertexConfig",
    "ApexVertexConfigurator",
    "ApexVertexError",
    "ApexVertexMode",
    "ApexVertexResult",
    "mint_vertex_access_token",
)

_CLOUD_PLATFORM_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
_DEFAULT_DEV_SECRET = "SuperSecret1"  # ruff: ignore[hardcoded-password-string]
_DEFAULT_DIRECT_HOST = "aiplatform.googleapis.com"
_DEFAULT_GATEWAY_HOST = "host.docker.internal"
_DEFAULT_GATEWAY_URL = "http://host.docker.internal:8000/api/apex/ai/v1"
_DEFAULT_MODEL_NAME = "gemini-3.8-flash"
_DEFAULT_VERIFICATION_PROMPT = "Reply with a one-sentence specialty coffee greeting from Cymbal Coffee."
_HTTPS_DEFAULT_PORT = 443
_HTTP_DEFAULT_PORT = 80
_ORACLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]*$")
_APEX_SCHEMA_PATTERN = "^APEX_[0-9]{6}$"
_PLACEHOLDER_PROJECTS = frozenset({"", "demo-project", "your-project-id", "your-gcp-project-id", "placeholder"})


class ApexVertexError(Exception):
    """Raised when Vertex AI configuration, token minting, or Oracle PL/SQL provisioning fails."""


class ApexVertexMode(StrEnum):
    """Supported Vertex AI connectivity modes for Oracle APEX 26.1."""

    DIRECT = "direct"
    GATEWAY = "gateway"


@dataclass(frozen=True, slots=True)
class ApexVertexConfig:
    """Configuration for provisioning Vertex AI connectivity inside Oracle APEX 26.1."""

    mode: ApexVertexMode = ApexVertexMode.DIRECT
    project_id: str = ""
    location: str = "global"
    model: str = "google/gemini-3.8-flash"
    gateway_url: str = _DEFAULT_GATEWAY_URL
    gateway_api_key: str | None = None
    workspace_name: str = "COFFEE"
    app_schema: str = "APP"
    credential_static_id: str = "VERTEX_AI_CRED"
    credential_name: str = "Vertex AI OAuth2 Bearer"
    service_static_id: str = "COFFEE_VERTEX_AI"
    service_name_label: str = "Cymbal Coffee Vertex AI"
    wallet_dir: Path | None = Path(".envs/tns")
    wallet_password: str = _DEFAULT_DEV_SECRET
    admin_user: str = "ADMIN"
    admin_password: str = _DEFAULT_DEV_SECRET
    db_service_name: str = ADB_FREE_DEFAULT_SERVICE
    db_dsn: str | None = None

    @property
    def base_url(self) -> str:
        """Return the OpenAI-compatible Chat Completions base URL for the active mode."""
        if self.mode == ApexVertexMode.DIRECT:
            project = self.project_id.strip()
            if project.lower() in _PLACEHOLDER_PROJECTS:
                raise ApexVertexError(
                    "Google Cloud project ID is required for direct Vertex AI mode. "
                    "Set VERTEX_AI_PROJECT_ID or pass --project."
                )
            loc = (self.location or "global").strip() or "global"
            return f"https://aiplatform.googleapis.com/v1/projects/{project}/locations/{loc}/endpoints/openapi"
        url = self.gateway_url.strip().rstrip("/")
        if not url:
            raise ApexVertexError(
                "Gateway URL cannot be empty in gateway mode. Set APEX_GATEWAY_URL or pass --gateway-url."
            )
        return url

    @property
    def acl_host_and_port(self) -> tuple[str, int]:
        """Return the ``(host, port)`` pair required for ``DBMS_NETWORK_ACL_ADMIN``."""
        parsed = urlsplit(self.base_url)
        default_host = _DEFAULT_DIRECT_HOST if self.mode == ApexVertexMode.DIRECT else _DEFAULT_GATEWAY_HOST
        host = parsed.hostname or default_host
        default_port = _HTTPS_DEFAULT_PORT if parsed.scheme == "https" else _HTTP_DEFAULT_PORT
        return (host, parsed.port or default_port)

    @classmethod
    def from_env(
        cls,
        *,
        mode: ApexVertexMode | str = ApexVertexMode.DIRECT,
        project_id: str | None = None,
        location: str | None = None,
        model: str | None = None,
        gateway_url: str | None = None,
        workspace_name: str | None = None,
    ) -> ApexVertexConfig:
        """Resolve APEX Vertex AI provisioning settings from arguments and environment variables."""
        resolved_mode = mode if isinstance(mode, ApexVertexMode) else ApexVertexMode(mode.strip().lower())
        resolved_project = (
            project_id
            if project_id is not None
            else (
                os.getenv("VERTEX_AI_PROJECT_ID")
                or os.getenv("GOOGLE_CLOUD_PROJECT")
                or os.getenv("GOOGLE_PROJECT_ID")
                or ""
            )
        ).strip()
        resolved_location = (
            location
            if location is not None
            else (
                os.getenv("VERTEX_AI_LOCATION")
                or os.getenv("GOOGLE_CLOUD_LOCATION")
                or os.getenv("GOOGLE_LOCATION")
                or "global"
            )
        ).strip() or "global"
        resolved_gateway_url = (
            gateway_url if gateway_url is not None else (os.getenv("APEX_GATEWAY_URL") or _DEFAULT_GATEWAY_URL)
        ).strip()
        gateway_api_key = (os.getenv("APEX_GATEWAY_API_KEY") or "").strip() or None

        if model is not None and model.strip():
            resolved_model = model.strip()
        else:
            chat_model = (os.getenv("VERTEX_AI_CHAT_MODEL") or _DEFAULT_MODEL_NAME).strip() or _DEFAULT_MODEL_NAME
            if resolved_mode == ApexVertexMode.DIRECT:
                resolved_model = chat_model if chat_model.startswith("google/") else f"google/{chat_model}"
            else:
                resolved_model = chat_model.removeprefix("google/")

        wallet_dir, service_name, db_dsn = _resolve_wallet_and_dsn_from_env()
        admin_pw = (
            os.getenv("ORACLE_ADMIN_PASSWORD")
            or os.getenv("DATABASE_ADMIN_PASSWORD")
            or os.getenv("ORACLE_PASSWORD")
            or _DEFAULT_DEV_SECRET
        )
        resolved_workspace = (
            workspace_name if workspace_name is not None else (os.getenv("APEX_WORKSPACE") or "COFFEE")
        ).strip().upper() or "COFFEE"
        app_schema = (os.getenv("DATABASE_USER") or "APP").strip().upper() or "APP"
        admin_user = (os.getenv("ORACLE_ADMIN_USER") or os.getenv("DATABASE_ADMIN_USER") or "ADMIN").strip() or "ADMIN"

        return cls(
            mode=resolved_mode,
            project_id=resolved_project,
            location=resolved_location,
            model=resolved_model,
            gateway_url=resolved_gateway_url,
            gateway_api_key=gateway_api_key,
            workspace_name=resolved_workspace,
            app_schema=app_schema,
            wallet_dir=wallet_dir,
            wallet_password=os.getenv("WALLET_PASSWORD", _DEFAULT_DEV_SECRET),
            admin_user=admin_user,
            admin_password=admin_pw,
            db_service_name=service_name,
            db_dsn=db_dsn,
        )


@dataclass(frozen=True, slots=True)
class ApexVertexResult:
    """Summary of provisioned Oracle network ACLs, APEX credential, and Generative AI Service."""

    mode: ApexVertexMode
    base_url: str
    model: str
    workspace_name: str
    credential_static_id: str | None
    service_static_id: str
    apex_schema: str
    acl_host: str
    acl_port: int
    token_refreshed: bool
    verification_response: str | None = None
    verification_latency_ms: float | None = None


def mint_vertex_access_token() -> str:
    """Mint a Google Cloud OAuth2 access token via ``gcloud`` or ``google.auth.default``."""
    gcloud_token = _try_gcloud_access_token()
    if gcloud_token:
        return gcloud_token
    adc_token = _try_google_auth_access_token()
    if adc_token:
        return adc_token
    raise ApexVertexError(
        "Unable to obtain a Google Cloud OAuth2 access token. "
        "Run 'gcloud auth application-default login' or 'gcloud auth login' and retry."
    )


class ApexVertexConfigurator:
    """Provision Oracle network ACLs, ``VERTEX_AI_CRED``, and ``COFFEE_VERTEX_AI`` in APEX 26.1."""

    def __init__(
        self, config: ApexVertexConfig | None = None, *, token_provider: Callable[[], str] = mint_vertex_access_token
    ) -> None:
        """Initialize the configurator with explicit config and OAuth2 token provider."""
        self.config = config or ApexVertexConfig.from_env()
        self._token_provider = token_provider

    def configure(
        self,
        *,
        refresh_token_only: bool = False,
        verify: bool = False,
        verification_prompt: str = _DEFAULT_VERIFICATION_PROMPT,
    ) -> ApexVertexResult:
        """Idempotently configure APEX 26.1 Vertex AI credentials, network ACLs, and AI service."""
        resolved_base_url = self.config.base_url
        acl_host, acl_port = self.config.acl_host_and_port
        app_schema = self._validate_oracle_identifier(self.config.app_schema)
        workspace_name = self.config.workspace_name.strip().upper()
        if not workspace_name:
            raise ApexVertexError("APEX workspace_name cannot be empty.")

        bearer_secret = self._resolve_bearer_secret()
        use_credential = bearer_secret is not None
        credential_static_id = self.config.credential_static_id if use_credential else None

        try:
            apex_schema, token_refreshed, verification_response, verification_latency_ms = self._execute_provisioning(
                resolved_base_url=resolved_base_url,
                acl_host=acl_host,
                acl_port=acl_port,
                app_schema=app_schema,
                workspace_name=workspace_name,
                bearer_secret=bearer_secret,
                use_credential=use_credential,
                refresh_token_only=refresh_token_only,
                verify=verify,
                verification_prompt=verification_prompt,
            )
        except ApexVertexError:
            raise
        except Exception as exc:
            redacted = self._redact_secrets(str(exc), bearer_secret)
            raise ApexVertexError(f"Failed to configure APEX 26.1 Vertex AI integration: {redacted}") from None

        return ApexVertexResult(
            mode=self.config.mode,
            base_url=resolved_base_url,
            model=self.config.model,
            workspace_name=workspace_name,
            credential_static_id=credential_static_id,
            service_static_id=self.config.service_static_id,
            apex_schema=apex_schema,
            acl_host=acl_host,
            acl_port=acl_port,
            token_refreshed=token_refreshed,
            verification_response=verification_response,
            verification_latency_ms=verification_latency_ms,
        )

    def _execute_provisioning(
        self,
        *,
        resolved_base_url: str,
        acl_host: str,
        acl_port: int,
        app_schema: str,
        workspace_name: str,
        bearer_secret: str | None,
        use_credential: bool,
        refresh_token_only: bool,
        verify: bool,
        verification_prompt: str,
    ) -> tuple[str, bool, str | None, float | None]:
        """Connect as ``ADMIN`` and run the requested ACL, credential, service, and verification PL/SQL blocks."""
        token_refreshed = False
        verification_response: str | None = None
        verification_latency_ms: float | None = None
        conn_params = self._build_admin_connection_params()
        with oracledb.connect(**conn_params) as connection:
            with connection.cursor() as cursor:
                apex_schema = self._resolve_apex_schema(cursor)
                if not refresh_token_only:
                    self._grant_network_acls(
                        cursor, acl_host=acl_host, acl_port=acl_port, principals=(app_schema, apex_schema)
                    )
                if bearer_secret is not None:
                    self._upsert_credential(cursor, workspace_name=workspace_name, bearer_token=bearer_secret)
                    token_refreshed = True
                if not refresh_token_only:
                    self._upsert_generative_ai_service(
                        cursor,
                        apex_schema=apex_schema,
                        workspace_name=workspace_name,
                        base_url=resolved_base_url,
                        use_credential=use_credential,
                    )
                if verify:
                    verification_response, verification_latency_ms = self._verify_generation(
                        cursor, workspace_name=workspace_name, prompt=verification_prompt
                    )
            connection.commit()
        return (apex_schema, token_refreshed, verification_response, verification_latency_ms)

    def _resolve_bearer_secret(self) -> str | None:
        """Return the OAuth2 access token in direct mode or optional gateway API key in gateway mode."""
        if self.config.mode == ApexVertexMode.DIRECT:
            token = (self._token_provider() or "").strip()
            if not token:
                raise ApexVertexError(
                    "OAuth2 token provider returned an empty token. "
                    "Run 'gcloud auth application-default login' or 'gcloud auth login' and retry."
                )
            return token
        if self.config.gateway_api_key is None:
            return None
        cleaned = self.config.gateway_api_key.strip()
        return cleaned or None

    def _build_admin_connection_params(self) -> dict[str, Any]:
        """Build ``python-oracledb`` connection parameters for ``ADMIN``."""
        dsn = self.config.db_dsn or self.config.db_service_name
        params: dict[str, Any] = {"user": self.config.admin_user, "password": self.config.admin_password, "dsn": dsn}
        wallet_dir = self.config.wallet_dir
        if wallet_dir is not None:
            if wallet_dir.is_file() and wallet_dir.suffix.lower() == ".zip":
                resolved_wallet = extract_oracle_wallet_zip(wallet_dir, wallet_password=self.config.wallet_password)
                wallet_path = str(resolved_wallet)
                params["config_dir"] = wallet_path
                params["wallet_location"] = wallet_path
                if self.config.wallet_password:
                    params["wallet_password"] = self.config.wallet_password
            elif wallet_dir.exists():
                wallet_path = str(wallet_dir.resolve())
                params["config_dir"] = wallet_path
                params["wallet_location"] = wallet_path
                if self.config.wallet_password:
                    params["wallet_password"] = self.config.wallet_password
        return params

    def _resolve_apex_schema(self, cursor: Any) -> str:
        """Query ``ALL_USERS`` for the highest installed ``APEX_NNNNNN`` engine schema."""
        cursor.execute(
            "SELECT username FROM all_users "
            "WHERE REGEXP_LIKE(username, :apex_pattern) "
            "ORDER BY username DESC FETCH FIRST 1 ROWS ONLY",
            apex_pattern=_APEX_SCHEMA_PATTERN,
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            raise ApexVertexError("No Oracle APEX engine schema (APEX_NNNNNN) found in ALL_USERS.")
        return self._validate_oracle_identifier(str(row[0]))

    @staticmethod
    def _grant_network_acls(cursor: Any, *, acl_host: str, acl_port: int, principals: tuple[str, ...]) -> None:
        """Grant outbound ``http`` and ``connect`` host ACEs for ``APP`` and the APEX engine schema."""
        acl_plsql = (
            "BEGIN\n"
            "    DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(\n"
            "        host       => :acl_host,\n"
            "        lower_port => :acl_port,\n"
            "        upper_port => :acl_port,\n"
            "        ace        => xs$ace_type(\n"
            "            privilege_list => xs$name_list('http', 'connect'),\n"
            "            principal_name => :principal_name,\n"
            "            principal_type => xs_acl.ptype_db\n"
            "        )\n"
            "    );\n"
            "END;"
        )
        for principal in dict.fromkeys(principals):
            cursor.execute(acl_plsql, acl_host=acl_host, acl_port=acl_port, principal_name=principal)

    def _upsert_credential(self, cursor: Any, *, workspace_name: str, bearer_token: str) -> None:
        """Create or update the ``VERTEX_AI_CRED`` HTTP Header Bearer credential using bound parameters."""
        credential_plsql = (
            "DECLARE\n"
            "    v_ws_id NUMBER;\n"
            "    v_count NUMBER := 0;\n"
            "BEGIN\n"
            "    v_ws_id := APEX_UTIL.FIND_SECURITY_GROUP_ID(p_workspace => UPPER(:workspace_name));\n"
            "    IF v_ws_id IS NULL OR v_ws_id = 0 THEN\n"
            "        RAISE_APPLICATION_ERROR(-20001, 'APEX workspace not found: ' || UPPER(:workspace_name));\n"
            "    END IF;\n"
            "    APEX_UTIL.SET_SECURITY_GROUP_ID(p_security_group_id => v_ws_id);\n"
            "    SELECT COUNT(*)\n"
            "      INTO v_count\n"
            "      FROM apex_workspace_credentials\n"
            "     WHERE workspace = UPPER(:workspace_name)\n"
            "       AND static_id = :cred_id;\n"
            "    IF v_count = 0 THEN\n"
            "        APEX_CREDENTIAL.CREATE_CREDENTIAL(\n"
            "            p_credential_name      => :cred_name,\n"
            "            p_credential_static_id => :cred_id,\n"
            "            p_authentication_type  => APEX_CREDENTIAL.C_TYPE_HTTP_HEADER\n"
            "        );\n"
            "    END IF;\n"
            "    APEX_CREDENTIAL.SET_PERSISTENT_CREDENTIALS(\n"
            "        p_credential_static_id => :cred_id,\n"
            "        p_key                  => 'Authorization',\n"
            "        p_value                => 'Bearer ' || :bearer_token\n"
            "    );\n"
            "END;"
        )
        cursor.execute(
            credential_plsql,
            workspace_name=workspace_name,
            cred_id=self.config.credential_static_id,
            cred_name=self.config.credential_name,
            bearer_token=bearer_token,
        )

    def _upsert_generative_ai_service(
        self, cursor: Any, *, apex_schema: str, workspace_name: str, base_url: str, use_credential: bool
    ) -> None:
        """Create or replace the ``COFFEE_VERTEX_AI`` APEX 26.1 Generative AI Service."""
        validated_apex_schema = self._validate_oracle_identifier(apex_schema)
        service_plsql_template = (
            "DECLARE\n"
            "    v_ws_id      NUMBER;\n"
            "    v_cred_id    NUMBER := NULL;\n"
            "    v_api_compat VARCHAR2(30);\n"
            "BEGIN\n"
            "    v_ws_id := APEX_UTIL.FIND_SECURITY_GROUP_ID(p_workspace => UPPER(:workspace_name));\n"
            "    IF v_ws_id IS NULL OR v_ws_id = 0 THEN\n"
            "        RAISE_APPLICATION_ERROR(-20001, 'APEX workspace not found: ' || UPPER(:workspace_name));\n"
            "    END IF;\n"
            "    APEX_UTIL.SET_SECURITY_GROUP_ID(p_security_group_id => v_ws_id);\n"
            "    IF :use_cred = 1 THEN\n"
            "        SELECT MAX(workspace_credential_id)\n"
            "          INTO v_cred_id\n"
            "          FROM apex_workspace_credentials\n"
            "         WHERE workspace = UPPER(:workspace_name)\n"
            "           AND static_id = :cred_id;\n"
            "        IF v_cred_id IS NULL THEN\n"
            "            RAISE_APPLICATION_ERROR(-20002, 'APEX credential not found: ' || :cred_id);\n"
            "        END IF;\n"
            "    END IF;\n"
            "    SELECT COALESCE(MAX(api_compatibility), '2026.01.05')\n"
            "      INTO v_api_compat\n"
            "      FROM apex_release;\n"
            "    __APEX_SCHEMA__.wwv_flow_imp.import_begin(\n"
            "        p_version_yyyy_mm_dd   => v_api_compat,\n"
            "        p_default_workspace_id => v_ws_id\n"
            "    );\n"
            "    DELETE FROM __APEX_SCHEMA__.wwv_flow_remote_servers\n"
            "     WHERE security_group_id = v_ws_id\n"
            "       AND server_type = 'GENERATIVE_AI'\n"
            "       AND static_id = :service_id;\n"
            "    __APEX_SCHEMA__.wwv_imp_workspace.create_remote_server(\n"
            "        p_id                         => __APEX_SCHEMA__.wwv_flow_id.next_val,\n"
            "        p_server_type                => 'GENERATIVE_AI',\n"
            "        p_name                       => :service_name,\n"
            "        p_static_id                  => :service_id,\n"
            "        p_base_url                   => :base_url,\n"
            "        p_ai_provider_type           => 'GENERIC_OPENAI',\n"
            "        p_ai_model_name              => :model_name,\n"
            "        p_ai_is_builder_service      => 'Y',\n"
            "        p_ai_is_default_for_new_apps => 'Y',\n"
            "        p_credential_id              => v_cred_id\n"
            "    );\n"
            "    __APEX_SCHEMA__.wwv_flow_imp.import_end;\n"
            "END;"
        )
        service_plsql = service_plsql_template.replace("__APEX_SCHEMA__", validated_apex_schema)
        cursor.execute(
            service_plsql,
            workspace_name=workspace_name,
            use_cred=1 if use_credential else 0,
            cred_id=self.config.credential_static_id,
            service_id=self.config.service_static_id,
            service_name=self.config.service_name_label,
            base_url=base_url,
            model_name=self.config.model,
        )

    def _verify_generation(self, cursor: Any, *, workspace_name: str, prompt: str) -> tuple[str, float]:
        """Execute a live ``APEX_AI.GENERATE`` round-trip prompt and measure latency in milliseconds."""
        verify_plsql = (
            "DECLARE\n"
            "    v_ws_id NUMBER;\n"
            "BEGIN\n"
            "    v_ws_id := APEX_UTIL.FIND_SECURITY_GROUP_ID(p_workspace => UPPER(:workspace_name));\n"
            "    IF v_ws_id IS NULL OR v_ws_id = 0 THEN\n"
            "        RAISE_APPLICATION_ERROR(-20001, 'APEX workspace not found: ' || UPPER(:workspace_name));\n"
            "    END IF;\n"
            "    APEX_UTIL.SET_SECURITY_GROUP_ID(p_security_group_id => v_ws_id);\n"
            "    :resp := APEX_AI.GENERATE(\n"
            "        p_prompt            => :prompt,\n"
            "        p_service_static_id => :service_id\n"
            "    );\n"
            "END;"
        )
        response_var = cursor.var(oracledb.DB_TYPE_CLOB)
        started = time.perf_counter()
        cursor.execute(
            verify_plsql,
            workspace_name=workspace_name,
            prompt=prompt,
            service_id=self.config.service_static_id,
            resp=response_var,
        )
        latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
        text = self._read_clob_or_text(response_var.getvalue()).strip()
        if not text:
            raise ApexVertexError("APEX_AI.GENERATE returned an empty verification response.")
        return (text, latency_ms)

    @staticmethod
    def _read_clob_or_text(raw_value: Any) -> str:
        """Convert an ``oracledb.LOB`` or string bind output into a plain Python string."""
        if raw_value is None:
            return ""
        read_fn = getattr(raw_value, "read", None)
        if callable(read_fn):
            return str(read_fn())
        return str(raw_value)

    @staticmethod
    def _validate_oracle_identifier(value: str) -> str:
        """Validate and uppercase an Oracle schema identifier."""
        cleaned = value.strip()
        if not _ORACLE_IDENTIFIER_RE.fullmatch(cleaned):
            raise ApexVertexError(f"Invalid Oracle identifier: {value!r}")
        return cleaned.upper()

    def _redact_secrets(self, message: str, bearer_secret: str | None) -> str:
        """Scrub bearer tokens and passwords from any error string before raising."""
        redacted = message
        for secret in (
            bearer_secret,
            self.config.gateway_api_key,
            self.config.admin_password,
            self.config.wallet_password,
        ):
            if secret:
                redacted = redacted.replace(secret, "[REDACTED]")
        return redacted


def _try_gcloud_access_token() -> str | None:
    """Attempt to print a fresh access token via ``gcloud`` CLI commands."""
    gcloud_bin = shutil.which("gcloud")
    if not gcloud_bin:
        return None
    commands = (
        [gcloud_bin, "auth", "print-access-token"],
        [gcloud_bin, "auth", "application-default", "print-access-token"],
    )
    for cmd in commands:
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=True)
        except (OSError, subprocess.SubprocessError):
            continue
        if getattr(completed, "returncode", 0) == 0:
            token = (getattr(completed, "stdout", "") or "").strip()
            if token:
                return token
    return None


def _try_google_auth_access_token() -> str | None:
    """Attempt to obtain and refresh an ADC access token via ``google.auth.default``."""
    try:
        creds, _ = google.auth.default(scopes=_CLOUD_PLATFORM_SCOPES)
        token = _extract_or_refresh_creds_token(creds)
    except Exception:
        return None
    return token or None


def _extract_or_refresh_creds_token(creds: Any) -> str:
    """Read or refresh the OAuth2 access token from a ``google-auth`` credentials object."""
    token = (getattr(creds, "token", None) or "").strip()
    is_valid = bool(getattr(creds, "valid", False))
    if not token or not is_valid:
        creds.refresh(GoogleAuthRequest())
        token = (getattr(creds, "token", None) or "").strip()
    return token


def _resolve_wallet_and_dsn_from_env() -> tuple[Path | None, str, str | None]:
    """Resolve ``(wallet_dir, service_name, db_dsn)`` consistently with ADB-Free and external modes."""
    raw_wallet = (os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN") or "").strip()
    raw_host = (os.getenv("DATABASE_HOST") or "").strip()
    raw_dsn = (os.getenv("DATABASE_DSN") or "").strip()
    raw_flavor = (os.getenv("ORACLE_CONTAINER_FLAVOR") or "adb-free").strip().lower()

    if raw_wallet:
        wallet_dir: Path | None = Path(raw_wallet)
    elif raw_host or raw_dsn or raw_flavor == "free":
        wallet_dir = None
    else:
        wallet_dir = Path(".envs/tns")

    raw_url = (os.getenv("DATABASE_URL") or "").strip()
    default_service = "freepdb1" if (wallet_dir is None and raw_flavor == "free") else ADB_FREE_DEFAULT_SERVICE
    service_name = (
        raw_url
        if raw_url and "://" not in raw_url and ":" not in raw_url and "/" not in raw_url
        else os.getenv("DATABASE_SERVICE_NAME", default_service)
    )
    if wallet_dir is not None and service_name.lower() == "freepdb1":
        service_name = ADB_FREE_DEFAULT_SERVICE

    db_dsn: str | None = None
    if raw_dsn:
        db_dsn = raw_dsn
    elif wallet_dir is None:
        host = raw_host or "localhost"
        port = int((os.getenv("DATABASE_PORT") or "1521").strip())
        db_dsn = f"{host}:{port}/{service_name}"

    return (wallet_dir, service_name, db_dsn)
