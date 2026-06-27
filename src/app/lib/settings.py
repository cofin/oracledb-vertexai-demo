# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import binascii
import json
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from litestar.utils.module_loader import module_to_os_path
from sqlspec.adapters.oracledb import OracleAsyncConfig

if TYPE_CHECKING:
    from litestar.data_extractors import RequestExtractorField, ResponseExtractorField
    from litestar_vite import ViteConfig


DEFAULT_MODULE_NAME = "app"
BASE_DIR: Final[Path] = module_to_os_path(DEFAULT_MODULE_NAME)

_TRUE_VALUES: Final[frozenset[str]] = frozenset({"true", "1", "yes", "y", "t", "on"})


def _env_bool(name: str, default: bool) -> bool:
    """Parse an environment variable as a boolean using a single truth table."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def _env_int(name: str, default: int) -> int:
    """Parse an environment variable as an integer, falling back to the default."""
    raw = os.getenv(name)
    if not raw:
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    """Parse an environment variable as a float, falling back to the default."""
    raw = os.getenv(name)
    if not raw:
        return default
    return float(raw)


def _env_str(name: str, default: str) -> str:
    """Read an environment variable as a string with a default."""
    return os.getenv(name, default)


def _env_cors(name: str, default: str) -> list[str]:
    """Parse an env value into a CORS origin list.

    Accepts a JSON list (``["*"]``) or a comma-separated string (``a.com,b.com``)
    and always returns a ``list[str]``.

    Raises:
        ValueError: If a bracketed value is not valid JSON.
    """
    raw = os.getenv(name, default)
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
        except (SyntaxError, ValueError):
            msg = "ALLOWED_CORS_ORIGINS is not a valid list representation."
            raise ValueError(msg) from None
        return [str(host) for host in parsed]
    return [host.strip() for host in raw.split(",")]


@dataclass(frozen=True)
class DatabaseSettings:
    """Oracle Database connection settings."""

    # Autonomous Database fields (new)
    URL: str | None = field(default_factory=lambda: os.getenv("DATABASE_URL"))
    """Oracle Database URL (for Autonomous DB). Format: oracle+oracledb://user:password@service_name"""
    WALLET_PASSWORD: str | None = field(default_factory=lambda: os.getenv("WALLET_PASSWORD"))
    """Oracle Database Wallet Password (for Autonomous DB)."""
    WALLET_LOCATION: str | None = field(default_factory=lambda: os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN"))
    """Oracle Database Wallet Location (for Autonomous DB). Falls back to TNS_ADMIN if set."""

    USER: str = field(default_factory=lambda: os.getenv("DATABASE_USER", "app"))
    """Oracle Database User."""
    PASSWORD: str = field(default_factory=lambda: os.getenv("DATABASE_PASSWORD", "SuperSecret1"))
    """Oracle Database Password."""
    HOST: str = field(default_factory=lambda: os.getenv("DATABASE_HOST", "localhost"))
    """Oracle Database Host."""
    PORT: str = field(default_factory=lambda: os.getenv("DATABASE_PORT", "1521"))
    """Oracle Database Port."""
    SERVICE_NAME: str = field(default_factory=lambda: os.getenv("DATABASE_SERVICE_NAME", "freepdb1"))
    """Oracle Database Service Name."""
    DSN: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_DSN",
            f"{os.getenv('DATABASE_HOST', 'localhost')}:{os.getenv('DATABASE_PORT', '1521')}/{os.getenv('DATABASE_SERVICE_NAME', 'freepdb1')}",
        )
    )
    """Oracle Database DSN."""
    POOL_MIN_SIZE: int = field(default_factory=lambda: _env_int("DATABASE_POOL_MIN_SIZE", 5))
    """Minimum pool size."""
    POOL_MAX_SIZE: int = field(default_factory=lambda: _env_int("DATABASE_POOL_MAX_SIZE", 20))
    """Maximum pool size."""
    ADK_IN_MEMORY: bool = field(default_factory=lambda: _env_bool("ORACLE_ADK_IN_MEMORY", True))
    """Enable Oracle INMEMORY for ADK session/event tables when licensed."""
    ADK_ENABLE_MEMORY: bool = field(default_factory=lambda: _env_bool("ADK_ENABLE_MEMORY", True))
    """Include SQLSpec ADK memory table migrations."""
    LITESTAR_SESSION_IN_MEMORY: bool = field(
        default_factory=lambda: _env_bool("ORACLE_LITESTAR_SESSION_IN_MEMORY", True)
    )
    """Enable Oracle INMEMORY for the Litestar server-side session table when licensed."""
    MIGRATION_PATH: str = field(
        default_factory=lambda: os.getenv("DATABASE_MIGRATION_PATH", str(BASE_DIR / "db" / "migrations"))
    )
    """Database migration path."""
    FIXTURE_PATH: str = f"{BASE_DIR}/db/fixtures"
    """The path to JSON fixture files to load into tables."""

    @property
    def is_autonomous(self) -> bool:
        """Detect if we're using Autonomous Database based on presence of URL and wallet password."""
        return self.URL is not None and self.WALLET_PASSWORD is not None

    def get_connection_params(self) -> dict[str, Any]:
        """Extract connection parameters based on connection mode (autonomous vs local).

        Returns:
            Oracle connection parameters for the configured deployment mode.
        """
        if self.is_autonomous:
            from urllib.parse import urlparse

            parsed = urlparse(self.URL)
            return {
                "user": parsed.username or self.USER,
                "password": parsed.password or self.PASSWORD,
                "dsn": parsed.hostname or "",
                "wallet_password": self.WALLET_PASSWORD or "",
            }
        return {"user": self.USER, "password": self.PASSWORD, "dsn": self.DSN}

    def create_config(self) -> OracleAsyncConfig:
        """Create Oracle database configuration based on connection mode (autonomous vs local).

        Returns:
            SQLSpec Oracle async configuration for the app.

        Raises:
            ValueError: If Autonomous Database is enabled without a wallet location.
        """
        conn_params = self.get_connection_params()

        if self.is_autonomous:
            # Autonomous Database with wallet
            if not self.WALLET_LOCATION:
                msg = "WALLET_LOCATION or TNS_ADMIN environment variable must be set for Autonomous Database"
                raise ValueError(msg)

            wallet_path = Path(self.WALLET_LOCATION).resolve()
            absolute_wallet_path = str(wallet_path)
            os.environ["TNS_ADMIN"] = absolute_wallet_path

            import ssl

            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            pem_path = wallet_path / "ewallet.pem"
            if pem_path.exists():
                ssl_ctx.load_verify_locations(cafile=str(pem_path))

            pool_config = {
                "user": conn_params["user"],
                "password": conn_params["password"],
                "dsn": conn_params["dsn"],
                "wallet_location": absolute_wallet_path,
                "config_dir": absolute_wallet_path,
                "wallet_password": conn_params["wallet_password"],
                "ssl_context": ssl_ctx,
                "min": self.POOL_MIN_SIZE,
                "max": self.POOL_MAX_SIZE,
            }
        else:
            # Local/Standard Database
            pool_config = {
                "user": conn_params["user"],
                "password": conn_params["password"],
                "dsn": conn_params["dsn"],
                "min": self.POOL_MIN_SIZE,
                "max": self.POOL_MAX_SIZE,
            }

        return OracleAsyncConfig(
            connection_config=pool_config,
            migration_config={
                "version_table_name": "migrations",
                "script_location": self.MIGRATION_PATH,
                "project_root": BASE_DIR,
                "include_extensions": ["adk", "litestar"],
            },
            extension_config={
                "adk": {
                    "enable_memory": self.ADK_ENABLE_MEMORY,
                    "include_memory_migration": self.ADK_ENABLE_MEMORY,
                    "in_memory": self.ADK_IN_MEMORY,
                },
                "litestar": {"session_table": "app_session", "in_memory": self.LITESTAR_SESSION_IN_MEMORY},
            },
        )


@dataclass(frozen=True)
class LogSettings:
    """Logger configuration"""

    # https://stackoverflow.com/a/1845097/6560549
    EXCLUDE_PATHS: str = (
        r"^/health|^/static/|^/assets/|^/favicon\.ico|^/@vite|^/@fs|^/node_modules|"
        r"\.(?:js|css|ico|png|jpg|svg|woff2?)$"
    )
    """Regex to exclude paths from logging."""
    INCLUDE_COMPRESSED_BODY: bool = False
    """Include 'body' of compressed responses in log output."""
    LEVEL: int = field(
        default_factory=lambda: (
            int(os.getenv("LOG_LEVEL", "0"))
            if os.getenv("LOG_LEVEL", "").isdigit()
            else logging.getLevelNamesMapping().get(os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
        )
    )
    """Stdlib log level as int. Accepts numeric (e.g. '20') or named (e.g. 'INFO') via LOG_LEVEL env var."""
    SQLSPEC_LEVEL: int = field(default_factory=lambda: _env_int("SQLSPEC_LOG_LEVEL", 20))
    """SQLSpec driver log level (default: INFO=20)."""
    OBFUSCATE_COOKIES: set[str] = field(default_factory=lambda: {"session", "XSRF-TOKEN"})
    """Request cookie keys to obfuscate."""
    OBFUSCATE_HEADERS: set[str] = field(default_factory=lambda: {"Authorization", "X-API-KEY", "X-XSRF-TOKEN"})
    """Request header keys to obfuscate."""
    REQUEST_FIELDS: list[RequestExtractorField] = field(
        default_factory=lambda: ["path", "method", "query", "path_params"]
    )
    """Attributes of the [Request][litestar.connection.request.Request] to be
    logged."""
    RESPONSE_FIELDS: list[ResponseExtractorField] = field(default_factory=lambda: ["status_code"])
    """Attributes of the [Response][litestar.response.Response] to be
    logged."""
    GRANIAN_ACCESS_LEVEL: int = 30
    """Level to log ASGI access logs."""
    GRANIAN_ERROR_LEVEL: int = 20
    """Level to log ASGI error logs."""


@dataclass(frozen=True)
class AppSettings:
    """Application configuration"""

    DEBUG: bool = field(default_factory=lambda: _env_bool("LITESTAR_DEBUG", False))
    """Run `Litestar` with `debug=True`."""
    SECRET_KEY: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY", binascii.hexlify(os.urandom(32)).decode(encoding="utf-8"))
    )
    """Application secret key."""
    NAME: str = field(default_factory=lambda: "app")
    """Application name."""
    ALLOWED_CORS_ORIGINS: list[str] = field(default_factory=lambda: _env_cors("ALLOWED_CORS_ORIGINS", '["*"]'))
    """Allowed CORS Origins"""
    CSRF_COOKIE_NAME: str = field(default_factory=lambda: "XSRF-TOKEN")
    """CSRF Cookie Name"""
    CSRF_HEADER_NAME: str = field(default_factory=lambda: "X-CSRFToken")
    """CSRF header name forwarded by HTMX requests; must match the JS helper default."""
    CSRF_COOKIE_SECURE: bool = field(default_factory=lambda: False)
    """CSRF Secure Cookie"""


@dataclass(frozen=True)
class MapsSettings:
    """Google Maps integration settings."""

    ENABLE_EMBED: bool = field(default_factory=lambda: _env_bool("MAPS_ENABLE_EMBED", False))
    """Enable optional Google Maps Embed iframe rendering."""
    EMBED_API_KEY: str = field(default_factory=lambda: os.getenv("GOOGLE_MAPS_EMBED_API_KEY", ""))
    """Restricted Google Maps Embed API key. Do not reuse Gemini or Vertex keys."""

    @property
    def embed_enabled(self) -> bool:
        """True only when embed rendering is explicitly enabled and keyed."""
        return self.ENABLE_EMBED and bool(self.EMBED_API_KEY.strip())


@dataclass(frozen=True)
class AISettings:
    """Vertex AI / Google GenAI configuration settings."""

    project_id: str = field(
        default_factory=lambda: os.getenv("VERTEX_AI_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or ""
    )
    """Google Cloud Project ID for Vertex AI."""
    location: str = field(
        default_factory=lambda: (
            os.getenv("VERTEX_AI_LOCATION")
            or os.getenv("GOOGLE_CLOUD_LOCATION")
            or os.getenv("GOOGLE_LOCATION")
            or "us-central1"
        )
    )
    """Vertex AI location/region."""
    api_key: str | None = field(default_factory=lambda: os.getenv("VERTEX_AI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    """Optional API key for Google AI clients."""
    chat_model: str = field(default_factory=lambda: os.getenv("VERTEX_AI_CHAT_MODEL", "gemini-3.1-flash-lite"))
    """Vertex AI chat model."""
    intent_model_override: str | None = field(default_factory=lambda: os.getenv("VERTEX_AI_INTENT_MODEL"))
    """Optional override for the single-call intent-classification model."""
    embedding_model: str = field(default_factory=lambda: os.getenv("VERTEX_AI_EMBEDDING_MODEL", "gemini-embedding-2"))
    """Vertex AI embedding model."""
    embedding_dimensions: int = 3072
    """Embedding vector dimensions (gemini-embedding-2 native output)."""

    @property
    def intent_model(self) -> str:
        """Intent-classification model, falling back to the chat model."""
        return self.intent_model_override or self.chat_model


@dataclass(frozen=True)
class ChatSettings:
    """Chat-workflow runtime constants."""

    session_app_name: str = field(default_factory=lambda: os.getenv("CHAT_SESSION_APP_NAME", "coffee_assistant"))
    """ADK app name used for session lookups and the per-request Runner."""
    response_cache_version: str = field(
        default_factory=lambda: os.getenv("CHAT_RESPONSE_CACHE_VERSION", "menu-grounded-v2")
    )
    """Cache-key namespace bumped to invalidate stale grounded responses."""
    response_cache_ttl_minutes: int = field(default_factory=lambda: _env_int("CHAT_RESPONSE_CACHE_TTL_MINUTES", 60))
    """Response-cache time-to-live in minutes."""
    product_search_limit: int = field(default_factory=lambda: _env_int("CHAT_PRODUCT_SEARCH_LIMIT", 5))
    """Default product vector-search result limit."""
    product_search_threshold: float = field(
        default_factory=lambda: float(os.getenv("CHAT_PRODUCT_SEARCH_THRESHOLD", "0.7"))
    )
    """Default product vector-search similarity threshold."""
    grounded_answer_timeout_seconds: float = field(
        default_factory=lambda: _env_float("CHAT_GROUNDED_ANSWER_TIMEOUT_SECONDS", 2.5)
    )
    """Maximum time allowed for Product RAG structured selection before falling back."""
    display_history_limit: int = field(default_factory=lambda: _env_int("CHAT_DISPLAY_HISTORY_LIMIT", 40))
    """Maximum number of display-history messages retained per session."""


@dataclass(frozen=True)
class ViteSettings:
    """Vite configuration settings."""

    DEV_MODE: bool = field(default_factory=lambda: _env_bool("VITE_DEV_MODE", False))
    """Enable Vite dev server mode."""
    BUNDLE_DIR: Path = field(
        default_factory=lambda: Path(os.getenv("VITE_BUNDLE_DIR", str(BASE_DIR / "domain" / "web" / "static")))
    )
    """Vite bundle directory."""

    def get_config(self) -> ViteConfig:
        """Build the Vite plugin configuration.

        Returns:
            A ``ViteConfig`` whose paths match ``src/resources/vite.config.ts``.
        """
        from litestar_vite import PathConfig, TypeGenConfig, ViteConfig

        return ViteConfig(
            mode="htmx",
            dev_mode=self.DEV_MODE,
            types=TypeGenConfig(
                output=Path("generated"),
                generate_sdk=False,
                generate_routes=False,
                generate_schemas=False,
                generate_page_props=False,
            ),
            paths=PathConfig(
                root=BASE_DIR.parent / "resources",
                resource_dir=Path(),
                bundle_dir=self.BUNDLE_DIR,
                static_dir=Path("public"),
                asset_url="/static/",
            ),
        )


@dataclass(frozen=True)
class Settings:
    app: AppSettings = field(default_factory=AppSettings)
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    log: LogSettings = field(default_factory=LogSettings)
    ai: AISettings = field(default_factory=AISettings)
    chat: ChatSettings = field(default_factory=ChatSettings)
    vite: ViteSettings = field(default_factory=ViteSettings)
    maps: MapsSettings = field(default_factory=MapsSettings)

    def setup_litestar_env(self) -> None:
        """Set Litestar and Granian defaults expected by the app server."""
        app_url = os.getenv("APP_URL") or f"http://localhost:{os.getenv('LITESTAR_PORT', '8000')}"
        os.environ.setdefault("APP_URL", app_url)
        os.environ.setdefault("LITESTAR_APP", "app.server.asgi:create_app")
        os.environ.setdefault("LITESTAR_APP_NAME", self.app.NAME)
        os.environ.setdefault("LITESTAR_GRANIAN_IN_SUBPROCESS", "false")
        os.environ.setdefault("LITESTAR_GRANIAN_USE_LITESTAR_LOGGER", "true")

    def configure_genai_env(self) -> None:
        """Synchronize Google client env vars when project-based Vertex AI is configured.

        Project-based Vertex AI and API keys are mutually exclusive in the genai
        client, so a configured project clears any API key from the environment.
        Run at startup rather than during dataclass construction to keep
        ``AISettings`` immutable.
        """
        if self.ai.project_id:
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ.pop("VERTEX_AI_API_KEY", None)
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
            os.environ["GOOGLE_CLOUD_PROJECT"] = self.ai.project_id
            os.environ["GOOGLE_CLOUD_LOCATION"] = self.ai.location

    @classmethod
    @lru_cache(maxsize=1, typed=True)
    def from_env(cls, dotenv_filename: str = ".env") -> Settings:
        env_file = Path(dotenv_filename)
        if not env_file.is_absolute():
            env_file = Path(os.curdir) / env_file
        if env_file.is_file():
            from dotenv import load_dotenv

            # override=False so shell env wins over .env — exported shell values
            # take precedence and the factory stays predictable across processes.
            load_dotenv(env_file, override=False)

        for k, v in list(os.environ.items()):
            if "$" in v:
                os.environ[k] = os.path.expandvars(v)

        settings = Settings()
        settings.setup_litestar_env()
        settings.configure_genai_env()
        return settings


def get_settings() -> Settings:
    return Settings.from_env()
