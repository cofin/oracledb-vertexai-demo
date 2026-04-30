# Copyright 2026 Google LLC
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

TRUE_VALUES = {"True", "true", "1", "yes", "Y", "T"}


@dataclass
class DatabaseSettings:
    """Oracle Database connection settings."""

    # Autonomous Database fields (new)
    URL: str | None = field(default_factory=lambda: os.getenv("DATABASE_URL"))
    """Oracle Database URL (for Autonomous DB). Format: oracle+oracledb://user:password@service_name"""
    WALLET_PASSWORD: str | None = field(default_factory=lambda: os.getenv("WALLET_PASSWORD"))
    """Oracle Database Wallet Password (for Autonomous DB)."""
    WALLET_LOCATION: str | None = field(default_factory=lambda: os.getenv("WALLET_LOCATION") or os.getenv("TNS_ADMIN"))
    """Oracle Database Wallet Location (for Autonomous DB). Falls back to TNS_ADMIN if set."""

    # Standard/Local Database fields (existing)
    USER: str = field(
        default_factory=lambda: os.getenv("DATABASE_USER", "app"),
    )
    """Oracle Database User."""
    PASSWORD: str = field(
        default_factory=lambda: os.getenv("DATABASE_PASSWORD", "super-secret"),
    )
    """Oracle Database Password."""
    HOST: str = field(
        default_factory=lambda: os.getenv("DATABASE_HOST", "localhost"),
    )
    """Oracle Database Host."""
    PORT: str = field(
        default_factory=lambda: os.getenv("DATABASE_PORT", "1521"),
    )
    """Oracle Database Port."""
    SERVICE_NAME: str = field(
        default_factory=lambda: os.getenv("DATABASE_SERVICE_NAME", "FREEPDB1"),
    )
    """Oracle Database Service Name."""
    DSN: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_DSN",
            f"{os.getenv('DATABASE_HOST', 'localhost')}:{os.getenv('DATABASE_PORT', '1521')}/{os.getenv('DATABASE_SERVICE_NAME', 'FREEPDB1')}",
        ),
    )
    """Oracle Database DSN."""
    POOL_MIN_SIZE: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_MIN_SIZE", "5")))
    """Minimum pool size."""
    POOL_MAX_SIZE: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_MAX_SIZE", "20")))
    """Maximum pool size."""
    POOL_TIMEOUT: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_TIMEOUT", "30")))
    """Pool timeout in seconds."""
    POOL_RECYCLE: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_RECYCLE", "300")))
    """Pool recycle time in seconds."""
    ECHO: bool = field(default_factory=lambda: os.getenv("DATABASE_ECHO", "False") in TRUE_VALUES)
    """Echo SQL statements to log output."""
    ADK_IN_MEMORY: bool = field(default_factory=lambda: os.getenv("ORACLE_ADK_IN_MEMORY", "False") in TRUE_VALUES)
    """Enable Oracle INMEMORY for ADK session/event tables when licensed."""
    ADK_ENABLE_MEMORY: bool = field(default_factory=lambda: os.getenv("ADK_ENABLE_MEMORY", "True") in TRUE_VALUES)
    """Include SQLSpec ADK memory table migrations."""
    LITESTAR_SESSION_IN_MEMORY: bool = field(
        default_factory=lambda: os.getenv("ORACLE_LITESTAR_SESSION_IN_MEMORY", "False") in TRUE_VALUES
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
        return {
            "user": self.USER,
            "password": self.PASSWORD,
            "dsn": self.DSN,
        }

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

            # Set TNS_ADMIN for wallet location
            os.environ["TNS_ADMIN"] = self.WALLET_LOCATION

            pool_config = {
                "user": conn_params["user"],
                "password": conn_params["password"],
                "dsn": conn_params["dsn"],
                "wallet_password": conn_params["wallet_password"],
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
                    "session_table": "adk_sessions",
                    "events_table": "adk_events",
                    "memory_table": "adk_memory_entries",
                    "enable_memory": self.ADK_ENABLE_MEMORY,
                    "include_memory_migration": self.ADK_ENABLE_MEMORY,
                    "in_memory": self.ADK_IN_MEMORY,
                },
                "litestar": {
                    "session_table": "app_session",
                    "in_memory": self.LITESTAR_SESSION_IN_MEMORY,
                },
            },
        )


@dataclass
class ServerSettings:
    """Server configurations."""

    APP_LOC: str = "app.asgi:app"
    """Path to app executable, or factory."""
    HOST: str = field(default_factory=lambda: os.getenv("LITESTAR_HOST", "0.0.0.0"))  # noqa: S104
    """Server network host."""
    PORT: int = field(default_factory=lambda: int(os.getenv("LITESTAR_PORT", "8000")))
    """Server port."""
    KEEPALIVE: int = field(default_factory=lambda: int(os.getenv("LITESTAR_KEEPALIVE", "65")))
    """Seconds to hold connections open (65 is > AWS lb idle timeout)."""
    RELOAD: bool = field(
        default_factory=lambda: os.getenv("LITESTAR_RELOAD", "False") in TRUE_VALUES,
    )
    """Turn on hot reloading."""
    RELOAD_DIRS: list[str] = field(default_factory=lambda: [f"{BASE_DIR}"])
    """Directories to watch for reloading."""
    HTTP_WORKERS: int | None = field(
        default_factory=lambda: int(os.getenv("WEB_CONCURRENCY")) if os.getenv("WEB_CONCURRENCY") is not None else None,  # type: ignore[arg-type]
    )
    """Number of HTTP Worker processes to be spawned by Uvicorn."""


@dataclass
class LogSettings:
    """Logger configuration"""

    # https://stackoverflow.com/a/1845097/6560549
    EXCLUDE_PATHS: str = r"\A(?!x)x"
    """Regex to exclude paths from logging."""
    HTTP_EVENT: str = "HTTP"
    """Log event name for logs from Litestar handlers."""
    INCLUDE_COMPRESSED_BODY: bool = False
    """Include 'body' of compressed responses in log output."""
    LEVEL: int = field(
        default_factory=lambda: (
            int(os.getenv("LOG_LEVEL", "0"))
            if os.getenv("LOG_LEVEL", "").isdigit()
            else logging.getLevelNamesMapping().get(os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
        ),
    )
    """Stdlib log level as int. Accepts numeric (e.g. '20') or named (e.g. 'INFO') via LOG_LEVEL env var."""
    SQLSPEC_LEVEL: int = field(default_factory=lambda: int(os.getenv("SQLSPEC_LOG_LEVEL", "20")))
    """SQLSpec driver log level (default: INFO=20)."""
    OBFUSCATE_COOKIES: set[str] = field(default_factory=lambda: {"session", "XSRF-TOKEN"})
    """Request cookie keys to obfuscate."""
    OBFUSCATE_HEADERS: set[str] = field(default_factory=lambda: {"Authorization", "X-API-KEY", "X-XSRF-TOKEN"})
    """Request header keys to obfuscate."""
    REQUEST_FIELDS: list[RequestExtractorField] = field(
        default_factory=lambda: [
            "path",
            "method",
            "query",
            "path_params",
        ],
    )
    """Attributes of the [Request][litestar.connection.request.Request] to be
    logged."""
    RESPONSE_FIELDS: list[ResponseExtractorField] = field(
        default_factory=lambda: [
            "status_code",
        ],
    )
    """Attributes of the [Response][litestar.response.Response] to be
    logged."""
    GRANIAN_ACCESS_LEVEL: int = 30
    """Level to log uvicorn access logs."""
    GRANIAN_ERROR_LEVEL: int = 20
    """Level to log uvicorn error logs."""


@dataclass
class AppSettings:
    """Application configuration"""

    URL: str = field(default_factory=lambda: os.getenv("APP_URL", "http://localhost:8000"))
    """The frontend base URL"""
    DEBUG: bool = field(default_factory=lambda: os.getenv("LITESTAR_DEBUG", "False") in TRUE_VALUES)
    """Run `Litestar` with `debug=True`."""
    SECRET_KEY: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY", binascii.hexlify(os.urandom(32)).decode(encoding="utf-8")),
    )
    """Application secret key."""
    NAME: str = field(default_factory=lambda: "app")
    """Application name."""
    ALLOWED_CORS_ORIGINS: list[str] | str = field(default_factory=lambda: os.getenv("ALLOWED_CORS_ORIGINS", '["*"]'))
    """Allowed CORS Origins"""
    CSRF_COOKIE_NAME: str = field(default_factory=lambda: "XSRF-TOKEN")
    """CSRF Cookie Name"""
    CSRF_HEADER_NAME: str = field(default_factory=lambda: "X-CSRFToken")
    """CSRF header name forwarded by HTMX requests; must match the JS helper default."""
    CSRF_COOKIE_SECURE: bool = field(default_factory=lambda: False)
    """CSRF Secure Cookie"""

    def __post_init__(self) -> None:
        # Check if the ALLOWED_CORS_ORIGINS is a string.
        if isinstance(self.ALLOWED_CORS_ORIGINS, str):
            # Check if the string starts with "[" and ends with "]", indicating a list.
            if self.ALLOWED_CORS_ORIGINS.startswith("[") and self.ALLOWED_CORS_ORIGINS.endswith("]"):
                try:
                    # Safely evaluate the string as a Python list.
                    self.ALLOWED_CORS_ORIGINS = json.loads(self.ALLOWED_CORS_ORIGINS)
                except (SyntaxError, ValueError):
                    # Handle potential errors if the string is not a valid Python literal.
                    msg = "ALLOWED_CORS_ORIGINS is not a valid list representation."
                    raise ValueError(msg) from None
            else:
                # Split the string by commas into a list if it is not meant to be a list representation.
                self.ALLOWED_CORS_ORIGINS = [host.strip() for host in self.ALLOWED_CORS_ORIGINS.split(",")]


@dataclass
class VertexAISettings:
    """Vertex AI configuration settings."""

    PROJECT_ID: str = field(
        default_factory=lambda: os.getenv("VERTEX_AI_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or ""
    )
    """Google Cloud Project ID for Vertex AI."""
    LOCATION: str = field(
        default_factory=lambda: (
            os.getenv("VERTEX_AI_LOCATION")
            or os.getenv("GOOGLE_CLOUD_LOCATION")
            or os.getenv("GOOGLE_LOCATION")
            or "us-central1"
        )
    )
    """Vertex AI location/region."""
    API_KEY: str | None = field(default_factory=lambda: os.getenv("VERTEX_AI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    """Optional API key for Google AI clients."""
    EMBEDDING_MODEL: str = field(default_factory=lambda: os.getenv("VERTEX_AI_EMBEDDING_MODEL", "gemini-embedding-001"))
    """Vertex AI embedding model."""
    EMBEDDING_DIMENSIONS: int = 3072
    """Embedding vector dimensions (gemini-embedding-001 native output)."""
    CHAT_MODEL: str = field(default_factory=lambda: os.getenv("VERTEX_AI_CHAT_MODEL", "gemini-3-flash-latest"))
    """Vertex AI chat model."""
    INTENT_MODEL: str = field(default_factory=lambda: os.getenv("VERTEX_AI_INTENT_MODEL", "gemini-2.5-flash-lite"))
    """Vertex AI model for single-call intent classification with text/x.enum."""

    def __post_init__(self) -> None:
        """Handle environment variable synchronization and conflict resolution."""
        if self.PROJECT_ID:
            # When using Vertex AI (project-based), API key must NOT be set in environment
            # as it causes mutual exclusivity errors in the genai client.
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ.pop("VERTEX_AI_API_KEY", None)
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
            os.environ["GOOGLE_CLOUD_PROJECT"] = self.PROJECT_ID
            os.environ["GOOGLE_CLOUD_LOCATION"] = self.LOCATION
            self.API_KEY = None

    # Context Caching Settings
    CACHE_TTL_SECONDS: int = field(default_factory=lambda: int(os.getenv("VERTEX_AI_CACHE_TTL_SECONDS", "3600")))
    """Context cache TTL in seconds (default: 1 hour)."""
    CACHE_PREFIX: str = field(default_factory=lambda: os.getenv("VERTEX_AI_CACHE_PREFIX", "cymbal-coffee"))
    """Prefix for cache names."""

    # Streaming Settings
    STREAM_BUFFER_SIZE: int = field(default_factory=lambda: int(os.getenv("VERTEX_AI_STREAM_BUFFER_SIZE", "1024")))
    """Buffer size for streaming responses."""
    STREAM_TIMEOUT_SECONDS: int = field(
        default_factory=lambda: int(os.getenv("VERTEX_AI_STREAM_TIMEOUT_SECONDS", "30"))
    )
    """Timeout for streaming responses."""


@dataclass
class AgentSettings:
    """Agent system configuration."""

    INTENT_THRESHOLD: float = field(default_factory=lambda: float(os.getenv("AGENT_INTENT_THRESHOLD", "0.8")))
    """Intent detection confidence threshold."""
    VECTOR_SEARCH_THRESHOLD: float = field(
        default_factory=lambda: float(os.getenv("AGENT_VECTOR_SEARCH_THRESHOLD", "0.7"))
    )
    """Vector search similarity threshold."""
    VECTOR_SEARCH_LIMIT: int = field(default_factory=lambda: int(os.getenv("AGENT_VECTOR_SEARCH_LIMIT", "5")))
    """Maximum number of vector search results."""
    CONVERSATION_HISTORY_LIMIT: int = field(
        default_factory=lambda: int(os.getenv("AGENT_CONVERSATION_HISTORY_LIMIT", "10"))
    )
    """Maximum conversation history to maintain."""
    SESSION_EXPIRE_HOURS: int = field(default_factory=lambda: int(os.getenv("AGENT_SESSION_EXPIRE_HOURS", "24")))
    """Session expiration in hours."""


@dataclass
class CacheSettings:
    """Caching configuration."""

    RESPONSE_TTL_MINUTES: int = field(default_factory=lambda: int(os.getenv("CACHE_RESPONSE_TTL_MINUTES", "5")))
    """Response cache TTL in minutes."""
    EMBEDDING_CACHE_ENABLED: bool = field(
        default_factory=lambda: os.getenv("CACHE_EMBEDDING_ENABLED", "True") in TRUE_VALUES
    )
    """Enable embedding caching."""


@dataclass
class ViteSettings:
    """Vite configuration settings."""

    DEV_MODE: bool = field(default_factory=lambda: os.getenv("VITE_DEV_MODE", "False") in TRUE_VALUES)
    """Enable Vite dev server mode."""
    USE_SERVER_LIFESPAN: bool = field(
        default_factory=lambda: os.getenv("VITE_USE_SERVER_LIFESPAN", "True") in TRUE_VALUES
    )
    """Use server lifespan to manage Vite process."""
    PORT: int = field(default_factory=lambda: int(os.getenv("VITE_PORT", "5173")))
    """Vite dev server port."""
    HOST: str = field(default_factory=lambda: os.getenv("VITE_HOST", "0.0.0.0"))  # noqa: S104
    """Vite dev server host."""
    BUNDLE_DIR: Path = field(
        default_factory=lambda: Path(
            os.getenv("VITE_BUNDLE_DIR", str(BASE_DIR / "domain" / "web" / "static" / "dist")),
        ),
    )
    """Vite bundle directory.

    Vite emits ``manifest.json`` + hashed bundles here; ``dist/hot`` is the
    HMR marker written when ``DEV_MODE`` is true. Lives inside the ``web``
    domain peer-package so templates and bundle output stay co-located.
    """
    ASSET_URL: str = field(default_factory=lambda: os.getenv("VITE_ASSET_URL", "/static/dist/"))
    """Vite asset URL."""

    @property
    def set_static_files(self) -> bool:
        """Whether to serve static files locally."""
        return self.ASSET_URL.startswith("/")

    def get_config(self) -> ViteConfig:
        """Build the Vite plugin configuration.

        Returns:
            A ``ViteConfig`` whose paths match the repo-root ``vite.config.ts``.
        """
        from litestar_vite import PathConfig, RuntimeConfig, TypeGenConfig, ViteConfig

        return ViteConfig(
            mode="template",
            dev_mode=self.DEV_MODE,
            types=TypeGenConfig(
                output=Path("src/resources/generated"),
                generate_sdk=False,
                generate_routes=False,
                generate_schemas=False,
                generate_page_props=False,
            ),
            paths=PathConfig(
                root=BASE_DIR.parents[1],
                resource_dir=Path("src/resources"),
                bundle_dir=self.BUNDLE_DIR,
                asset_url=self.ASSET_URL,
            ),
            runtime=RuntimeConfig(executor="node", host=self.HOST, port=self.PORT),
        )


@dataclass
class Settings:
    app: AppSettings = field(default_factory=AppSettings)
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    log: LogSettings = field(default_factory=LogSettings)
    vertex_ai: VertexAISettings = field(default_factory=VertexAISettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    cache: CacheSettings = field(default_factory=CacheSettings)
    vite: ViteSettings = field(default_factory=ViteSettings)

    @classmethod
    @lru_cache(maxsize=1, typed=True)
    def from_env(cls, dotenv_filename: str = ".env") -> Settings:
        from litestar.cli._utils import console

        env_file = Path(f"{os.curdir}/{dotenv_filename}")
        if env_file.is_file():
            from dotenv import load_dotenv

            console.print(f"[yellow]Loading environment configuration from {dotenv_filename}[/]")

            load_dotenv(env_file, override=True)
        return Settings()


def get_settings() -> Settings:
    return Settings.from_env()
