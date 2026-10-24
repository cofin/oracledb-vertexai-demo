# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Modular application settings package."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from app.lib.settings._ai import PLACEHOLDER_VALUES, AISettings, ChatSettings
from app.lib.settings._app import AppSettings
from app.lib.settings._database import DatabaseSettings
from app.lib.settings._env import BASE_DIR, DEFAULT_MODULE_NAME, _env_bool, _env_cors, _env_float, _env_int, _env_str
from app.lib.settings._log import LogSettings
from app.lib.settings._maps import MapsSettings
from app.lib.settings._otel import OpenTelemetrySettings
from app.lib.settings._queue import QueueBackendMode, QueueExecutionMode, QueueSettings, QueueWakeupMode
from app.lib.settings._server import ServerSettings, ViteSettings

__all__ = (
    "BASE_DIR",
    "DEFAULT_MODULE_NAME",
    "PLACEHOLDER_VALUES",
    "AISettings",
    "AppSettings",
    "ChatSettings",
    "DatabaseSettings",
    "LogSettings",
    "MapsSettings",
    "OpenTelemetrySettings",
    "QueueBackendMode",
    "QueueExecutionMode",
    "QueueSettings",
    "QueueWakeupMode",
    "ServerSettings",
    "Settings",
    "ViteSettings",
    "_env_bool",
    "_env_cors",
    "_env_float",
    "_env_int",
    "_env_str",
    "get_settings",
    "reload_settings",
)


@dataclass(frozen=True, slots=True)
class Settings:
    """Root application settings container."""

    app: AppSettings = field(default_factory=AppSettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    log: LogSettings = field(default_factory=LogSettings)
    ai: AISettings = field(default_factory=AISettings)
    chat: ChatSettings = field(default_factory=ChatSettings)
    vite: ViteSettings = field(default_factory=ViteSettings)
    maps: MapsSettings = field(default_factory=MapsSettings)
    otel: OpenTelemetrySettings = field(default_factory=OpenTelemetrySettings)
    queue: QueueSettings = field(default_factory=QueueSettings)

    @classmethod
    @lru_cache(maxsize=1, typed=True)
    def from_env(cls, dotenv_filename: str = ".env") -> Settings:
        """Load settings from the environment and optional ``.env`` file.

        Shell environment variables take precedence over ``.env`` entries
        (``override=False``).
        """
        env_file = Path(dotenv_filename)
        if not env_file.is_absolute():
            env_file = Path(os.curdir) / env_file
        if env_file.is_file():
            load_dotenv(env_file, override=False)

        for k, v in list(os.environ.items()):
            if "$" in v:
                os.environ[k] = os.path.expandvars(v)

        settings = Settings()
        settings.setup_litestar_env()
        settings.configure_genai_env()
        return settings

    def setup_litestar_env(self) -> None:
        """Set Litestar and Granian defaults expected by the app server."""
        port = os.getenv("LITESTAR_PORT") or str(self.server.PORT)
        os.environ.setdefault("LITESTAR_PORT", port)
        app_url = os.getenv("APP_URL") or f"http://localhost:{port}"
        os.environ.setdefault("APP_URL", app_url)
        os.environ.setdefault("LITESTAR_APP", "app.server.asgi:create_app")
        os.environ.setdefault("LITESTAR_APP_NAME", self.app.NAME)
        os.environ.setdefault("OTEL_SERVICE_NAME", self.otel.SERVICE_NAME)

    def configure_genai_env(self) -> None:
        """Synchronize Google client env vars when project-based Vertex AI is configured.

        Project-based Vertex AI and API keys are mutually exclusive in the genai
        client, so a configured project clears any API key from the environment.
        Run at startup rather than during dataclass construction to keep
        ``AISettings`` immutable.
        """
        if self.ai.has_valid_project_id():
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ.pop("VERTEX_AI_API_KEY", None)
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
            os.environ["GOOGLE_CLOUD_PROJECT"] = self.ai.project_id.strip()
            os.environ["GOOGLE_CLOUD_LOCATION"] = self.ai.resolve_location(self.ai.gcp_region)
        elif self.ai.has_valid_api_key():
            os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)
            if self.ai.api_key:
                os.environ.setdefault("GOOGLE_API_KEY", self.ai.api_key.strip())


def get_settings() -> Settings:
    """Return the cached ``Settings`` instance."""
    return Settings.from_env()


def reload_settings(dotenv_filename: str = ".env") -> Settings:
    """Clear the settings cache and reload from the environment."""
    Settings.from_env.cache_clear()
    return Settings.from_env(dotenv_filename)
