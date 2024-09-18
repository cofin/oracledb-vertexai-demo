# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import binascii
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Final

from advanced_alchemy.utils.text import slugify
from litestar.utils.module_loader import module_to_os_path
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

if TYPE_CHECKING:
    from litestar.data_extractors import RequestExtractorField, ResponseExtractorField


DEFAULT_MODULE_NAME = "app"
BASE_DIR: Final[Path] = module_to_os_path(DEFAULT_MODULE_NAME)

TRUE_VALUES = {"True", "true", "1", "yes", "Y", "T"}


@dataclass
class DatabaseSettings:
    ECHO: bool = field(
        default_factory=lambda: os.getenv("DATABASE_ECHO", "False") in TRUE_VALUES,
    )
    """Enable SQLAlchemy engine logs."""
    ECHO_POOL: bool = field(
        default_factory=lambda: os.getenv("DATABASE_ECHO_POOL", "False") in TRUE_VALUES,
    )
    """Enable SQLAlchemy connection pool logs."""
    POOL_DISABLED: bool = field(
        default_factory=lambda: os.getenv("DATABASE_POOL_DISABLED", "False") in TRUE_VALUES,
    )
    """Disable SQLAlchemy pool configuration."""
    POOL_MAX_OVERFLOW: int = field(default_factory=lambda: int(os.getenv("DATABASE_MAX_POOL_OVERFLOW", "10")))
    """Max overflow for SQLAlchemy connection pool"""
    POOL_SIZE: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_SIZE", "5")))
    """Pool size for SQLAlchemy connection pool"""
    POOL_TIMEOUT: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_TIMEOUT", "30")))
    """Time in seconds for timing connections out of the connection pool."""
    POOL_RECYCLE: int = field(default_factory=lambda: int(os.getenv("DATABASE_POOL_RECYCLE", "300")))
    """Amount of time to wait before recycling connections."""
    POOL_PRE_PING: bool = field(
        default_factory=lambda: os.getenv("DATABASE_PRE_POOL_PING", "False") in TRUE_VALUES,
    )
    """Optionally ping database before fetching a session from the connection pool."""
    USER: str = field(
        default_factory=lambda: os.getenv("DATABASE_USER", "scott"),
    )
    """SQLAlchemy Database User."""
    PASSWORD: str = field(
        default_factory=lambda: os.getenv("DATABASE_PASSWORD", "tiger"),
    )
    """SQLAlchemy Database Password."""
    HOST: str = field(
        default_factory=lambda: os.getenv("DATABASE_HOST", "localhost"),
    )
    PORT: str = field(
        default_factory=lambda: os.getenv("DATABASE_PORT", "1521"),
    )
    SERVICE_NAME: str = field(
        default_factory=lambda: os.getenv("DATABASE_SERVICE_NAME", "FREEPDB1"),
    )
    DSN: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_DSN",
            f"{os.getenv('DATABASE_HOST', 'localhost')}:{os.getenv('DATABASE_PORT', '1521')}/{os.getenv('DATABASE_SERVICE_NAME', 'FREEPDB1')}",
        ),
    )
    """SQLAlchemy Database DSN."""
    URL: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "oracle+oracledb://:@",
        ),
    )
    """SQLAlchemy Database URL."""
    MIGRATION_CONFIG: str = f"{BASE_DIR}/db/migrations/alembic.ini"
    """The path to the `alembic.ini` configuration file."""
    MIGRATION_PATH: str = f"{BASE_DIR}/db/migrations"
    """The path to the `alembic` database migrations."""
    MIGRATION_DDL_VERSION_TABLE: str = "ddl_version"
    """The name to use for the `alembic` versions table name."""
    FIXTURE_PATH: str = f"{BASE_DIR}/db/fixtures"
    """The path to JSON fixture files to load into tables."""
    _engine_instance: AsyncEngine | None = None
    """SQLAlchemy engine instance generated from settings."""

    @property
    def engine(self) -> AsyncEngine:
        return self.get_engine()

    def get_engine(self) -> AsyncEngine:
        if self._engine_instance is not None:
            return self._engine_instance

        if self.URL == "oracle+oracledb://:@":
            engine = create_async_engine(
                url=self.URL,
                thick_mode=False,
                connect_args={
                    "user": self.USER,
                    "password": self.PASSWORD,
                    "host": self.HOST,
                    "port": self.PORT,
                    "service_name": self.SERVICE_NAME,
                },
                future=True,
                echo=self.ECHO,
                echo_pool=self.ECHO_POOL,
                max_overflow=self.POOL_MAX_OVERFLOW,
                pool_size=self.POOL_SIZE,
                pool_timeout=self.POOL_TIMEOUT,
                pool_recycle=self.POOL_RECYCLE,
                pool_pre_ping=self.POOL_PRE_PING,
            )
            self._engine_instance = engine
        else:
            engine = create_async_engine(
                url=self.URL,
                future=True,
                echo=self.ECHO,
                echo_pool=self.ECHO_POOL,
                max_overflow=self.POOL_MAX_OVERFLOW,
                pool_size=self.POOL_SIZE,
                pool_timeout=self.POOL_TIMEOUT,
                pool_recycle=self.POOL_RECYCLE,
                pool_pre_ping=self.POOL_PRE_PING,
            )
            self._engine_instance = engine
        return self._engine_instance


@dataclass
class ServerSettings:
    """Server configurations."""

    APP_LOC: str = "app.asgi:app"
    """Path to app executable, or factory."""
    APP_LOC_IS_FACTORY: bool = False
    """Indicate if APP_LOC points to an executable or factory."""
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
    LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "ERROR"))
    """Stdlib log levels.

    Only emit logs at this level, or higher.
    """
    OBFUSCATE_COOKIES: set[str] = field(default_factory=lambda: {"session", "XSRF-TOKEN"})
    """Request cookie keys to obfuscate."""
    OBFUSCATE_HEADERS: set[str] = field(default_factory=lambda: {"Authorization", "X-API-KEY", "X-XSRF-TOKEN"})
    """Request header keys to obfuscate."""
    JOB_FIELDS: list[str] = field(
        default_factory=lambda: [
            "function",
            "kwargs",
            "key",
            "scheduled",
            "attempts",
            "completed",
            "queued",
            "started",
            "result",
            "error",
        ],
    )
    """Attributes of the SAQ.

    [`Job`](https://github.com/tobymao/saq/blob/master/saq/job.py) to be
    logged.
    """
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
    WORKER_EVENT: str = "Worker"
    """Log event name for logs from SAQ worker."""
    SAQ_LEVEL: int = 50
    """Level to log SAQ logs."""
    SQLALCHEMY_LEVEL: int = 30
    """Level to log SQLAlchemy logs."""
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
    CSRF_HEADER_NAME: str = field(default_factory=lambda: "X-XSRF-TOKEN")
    """CSRF Header Name"""
    CSRF_COOKIE_SECURE: bool = field(default_factory=lambda: False)
    """CSRF Secure Cookie"""
    GOOGLE_PROJECT_ID: str = field(default_factory=lambda: os.getenv("GOOGLE_PROJECT_ID", ""))
    """Google Project ID"""
    GOOGLE_API_KEY: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    """Google API Key"""
    EMBEDDING_MODEL_TYPE: str = "textembedding-gecko@003"

    @property
    def slug(self) -> str:
        """Return a slugified name.

        Returns:
            `self.NAME`, all lowercase and hyphens instead of spaces.
        """
        return slugify(self.NAME)

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
class ViteSettings:
    """Server configurations."""

    DEV_MODE: bool = field(
        default_factory=lambda: os.getenv("VITE_DEV_MODE", "False") in TRUE_VALUES,
    )
    """Start `vite` development server."""
    USE_SERVER_LIFESPAN: bool = field(
        default_factory=lambda: os.getenv("VITE_USE_SERVER_LIFESPAN", "True") in TRUE_VALUES,
    )
    """Auto start and stop `vite` processes when running in development mode.."""
    HOST: str = field(default_factory=lambda: os.getenv("VITE_HOST", "0.0.0.0"))  # noqa: S104
    """The host the `vite` process will listen on.  Defaults to `0.0.0.0`"""
    PORT: int = field(default_factory=lambda: int(os.getenv("VITE_PORT", "5173")))
    """The port to start vite on.  Default to `5173`"""
    HOT_RELOAD: bool = field(
        default_factory=lambda: os.getenv("VITE_HOT_RELOAD", "True") in TRUE_VALUES,
    )
    """Start `vite` with HMR enabled."""
    ENABLE_REACT_HELPERS: bool = field(
        default_factory=lambda: os.getenv("VITE_ENABLE_REACT_HELPERS", "True") in TRUE_VALUES,
    )
    """Enable React support in HMR."""
    BUNDLE_DIR: Path = field(default_factory=lambda: Path(f"{BASE_DIR}/domain/coffee/public"))
    """Bundle directory"""
    RESOURCE_DIR: Path = field(default_factory=lambda: Path("resources"))
    """Resource directory"""
    TEMPLATE_DIR: Path = field(default_factory=lambda: Path(f"{BASE_DIR}/domain/coffee/templates"))
    """Template directory."""
    ASSET_URL: str = field(default_factory=lambda: os.getenv("ASSET_URL", "/static/"))
    """Base URL for assets"""

    @property
    def set_static_files(self) -> bool:
        """Serve static assets."""
        return self.ASSET_URL.startswith("/")


@dataclass
class Settings:
    app: AppSettings = field(default_factory=AppSettings)
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    vite: ViteSettings = field(default_factory=ViteSettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    log: LogSettings = field(default_factory=LogSettings)

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
