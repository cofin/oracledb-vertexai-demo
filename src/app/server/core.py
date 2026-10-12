# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Litestar ApplicationCore plugin wiring middleware, plugins, and signature namespace."""

from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.middleware import ASGIMiddleware
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.plugins import InitPluginProtocol

from app import config
from app.__metadata__ import __version__
from app.lib.di import request_container_var
from app.server import plugins

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.types import ASGIApp, Receive, Scope, Send


class _RequestContainerMiddleware(ASGIMiddleware):
    """Bind the active Dishka request container to request_container_var."""

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        """Set request_container_var from the active request scope state."""
        state = scope.get("state")
        container = state.get("dishka_container") if isinstance(state, dict) else None
        token = request_container_var.set(container) if container is not None else None
        try:
            await next_app(scope, receive, send)
        finally:
            if token is not None:
                request_container_var.reset(token)


class ApplicationCore(InitPluginProtocol):
    """Wires routes, middleware, and plugins onto the Litestar app."""

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Initialize application middleware, plugins, and OpenAPI config."""
        from app.lib import log
        from app.lib.settings import get_settings

        settings = get_settings()

        app_config.middleware.insert(0, log.StructlogMiddleware)
        app_config.middleware.insert(1, _RequestContainerMiddleware())
        app_config.after_exception.append(log.after_exception_hook_handler)
        app_config.before_send.append(log.BeforeSendHandler())

        app_config.cors_config = config.cors
        if not settings.app.DEBUG:
            app_config.csrf_config = config.csrf

        app_config.stores = config.stores
        app_config.middleware.append(config.session_config.middleware)
        app_config.template_config = config.template

        app_plugins = [
            plugins.granian,
            plugins.db,
            plugins.structlog,
            plugins.problem_details,
            plugins.security,
            plugins.vite,
            plugins.htmx,
            plugins.flash,
            plugins.queue,
            plugins.autowire,
            plugins.mcp,
            plugins.a2a,
        ]

        if settings.otel.ENABLED:
            app_plugins.append(plugins.opentelemetry)
        app_config.plugins.extend(app_plugins)

        app_config.openapi_config = OpenAPIConfig(
            title=settings.app.NAME,
            version=__version__,
            use_handler_docstrings=True,
            render_plugins=[ScalarRenderPlugin(version="latest")],
        )

        from sqlspec.adapters.oracledb import OracleAsyncDriver

        from app.domain.ai.services import AgentOrchestrationService
        from app.domain.products.services import OracleVectorSearchService, ProductService
        from app.domain.system.services import CacheService, MetricsService

        app_config.signature_namespace.update({
            "OracleAsyncDriver": OracleAsyncDriver,
            "ProductService": ProductService,
            "CacheService": CacheService,
            "MetricsService": MetricsService,
            "OracleVectorSearchService": OracleVectorSearchService,
            "AgentOrchestrationService": AgentOrchestrationService,
        })

        return app_config
