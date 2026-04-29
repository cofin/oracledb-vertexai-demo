# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=[invalid-name,import-outside-toplevel]
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.plugins import InitPluginProtocol

from app import config
from app.__metadata__ import __version__
from app.lib.settings import get_settings
from app.server import plugins

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


class ApplicationCore(InitPluginProtocol):
    """Wires routes, middleware, and plugins onto the Litestar app."""

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        from app.lib import log

        settings = get_settings()

        app_config.middleware.insert(0, log.StructlogMiddleware)
        app_config.after_exception.append(log.after_exception_hook_handler)
        app_config.before_send.append(log.BeforeSendHandler())

        app_config.cors_config = config.cors
        if not settings.app.DEBUG:
            app_config.csrf_config = config.csrf

        app_config.stores = config.stores
        app_config.middleware.append(config.session_config.middleware)
        app_config.template_config = config.template

        app_config.plugins.extend(
            [
                plugins.granian,
                plugins.db,
                plugins.structlog,
                plugins.problem_details,
                plugins.vite,
                plugins.htmx,
                plugins.flash,
                plugins.domain,
            ],
        )

        app_config.openapi_config = OpenAPIConfig(
            title=settings.app.NAME,
            version=__version__,
            use_handler_docstrings=True,
            render_plugins=[ScalarRenderPlugin(version="latest")],
        )

        from sqlspec.adapters.oracledb import OracleAsyncDriver

        from app.domain.chat.services import ADKRunner
        from app.domain.products.services import OracleVectorSearchService, ProductService
        from app.domain.system.services import CacheService, MetricsService

        app_config.signature_namespace.update(
            {
                "OracleAsyncDriver": OracleAsyncDriver,
                "ProductService": ProductService,
                "CacheService": CacheService,
                "MetricsService": MetricsService,
                "OracleVectorSearchService": OracleVectorSearchService,
                "ADKRunner": ADKRunner,
            }
        )

        return app_config
