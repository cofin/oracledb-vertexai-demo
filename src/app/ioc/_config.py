# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka provider for application settings."""

from dishka import Provider, Scope, provide
from sqlspec.loader import SQLFileLoader

from app.lib.service import default_sql_loader
from app.lib.settings import (
    AISettings,
    AppSettings,
    ChatSettings,
    DatabaseSettings,
    LogSettings,
    MapsSettings,
    OpenTelemetrySettings,
    QueueSettings,
    ServerSettings,
    Settings,
    ViteSettings,
)

__all__ = ("ConfigProvider",)


class ConfigProvider(Provider):
    """APP-scoped provider for cached settings objects and SQL file loader."""

    scope = Scope.APP

    @provide
    def provide_settings(self) -> Settings:
        """Provide the root Settings object."""
        return Settings.from_env()

    @provide
    def provide_app_settings(self, settings: Settings) -> AppSettings:
        """Provide application identity settings."""
        return settings.app

    @provide
    def provide_server_settings(self, settings: Settings) -> ServerSettings:
        """Provide HTTP server settings."""
        return settings.server

    @provide
    def provide_database_settings(self, settings: Settings) -> DatabaseSettings:
        """Provide Oracle database settings."""
        return settings.db

    @provide
    def provide_ai_settings(self, settings: Settings) -> AISettings:
        """Provide Vertex AI and Gemini settings."""
        return settings.ai

    @provide
    def provide_chat_settings(self, settings: Settings) -> ChatSettings:
        """Provide chat response-caching settings."""
        return settings.chat

    @provide
    def provide_vite_settings(self, settings: Settings) -> ViteSettings:
        """Provide Vite asset settings."""
        return settings.vite

    @provide
    def provide_maps_settings(self, settings: Settings) -> MapsSettings:
        """Provide Google Maps settings."""
        return settings.maps

    @provide
    def provide_log_settings(self, settings: Settings) -> LogSettings:
        """Provide structured logging settings."""
        return settings.log

    @provide
    def provide_otel_settings(self, settings: Settings) -> OpenTelemetrySettings:
        """Provide OpenTelemetry settings."""
        return settings.otel

    @provide
    def provide_queue_settings(self, settings: Settings) -> QueueSettings:
        """Provide background queue settings."""
        return settings.queue

    @provide
    def provide_sql_loader(self) -> SQLFileLoader:
        """Provide the shared named-SQL file loader."""
        return default_sql_loader()
