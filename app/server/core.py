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

# pylint: disable=[invalid-name,import-outside-toplevel]
from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.plugins import CLIPluginProtocol, InitPluginProtocol

if TYPE_CHECKING:
    from click import Group
    from litestar.config.app import AppConfig


class ApplicationCore(InitPluginProtocol, CLIPluginProtocol):
    """Application core configuration plugin.

    This class is responsible for configuring the main Litestar application with our routes, guards, and various plugins
    """

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application

        Args:
            app_config: The :class:`AppConfig <.config.app.AppConfig>` instance.
        """
        from litestar import WebSocket
        from litestar.channels import ChannelsPlugin
        from litestar.connection import Request
        from litestar.datastructures import State
        from litestar.enums import RequestEncodingType
        from litestar.openapi import OpenAPIConfig
        from litestar.openapi.plugins import ScalarRenderPlugin
        from litestar.params import Body
        from litestar.static_files import create_static_files_router
        from litestar_htmx import HTMXRequest
        from oracledb import AsyncConnection, AsyncConnectionPool, Connection, ConnectionPool

        from app import config, schemas, services
        from app.db import models as m
        from app.lib import log
        from app.lib.settings import BASE_DIR, get_settings
        from app.server import plugins
        from app.server.controllers import CoffeeChatController
        from app.services import (
            ChatConversationService,
            CompanyService,
            InventoryService,
            OracleVectorSearchService,
            ProductService,
            RecommendationService,
            ResponseCacheService,
            SearchMetricsService,
            ShopService,
            UserSessionService,
            VertexAIService,
        )

        settings = get_settings()
        app_config.middleware.insert(0, config.session.middleware)
        # logging
        app_config.middleware.insert(0, log.StructlogMiddleware)
        app_config.after_exception.append(log.after_exception_hook_handler)
        app_config.before_send.append(log.BeforeSendHandler())
        # security
        app_config.cors_config = config.cors
        app_config.csrf_config = config.csrf
        # plugins
        app_config.plugins.extend(
            [
                plugins.flasher,
                plugins.granian,
                plugins.oracle,
                plugins.structlog,
                plugins.alchemy,
                plugins.htmx,
            ],
        )
        # Set HTMXRequest as the default request class
        app_config.request_class = HTMXRequest
        app_config.template_config = config.templates
        # openapi
        app_config.openapi_config = OpenAPIConfig(
            title=settings.app.NAME,
            version="0.2.0",
            use_handler_docstrings=True,
            render_plugins=[ScalarRenderPlugin(version="latest")],
        )
        # routes
        app_config.route_handlers.extend(
            [
                CoffeeChatController,
                create_static_files_router(
                    path="/static",
                    directories=[str(BASE_DIR / "server" / "static")],
                    name="static",
                ),
            ],
        )
        # signatures
        app_config.signature_namespace.update(
            {
                # Oracle types
                "AsyncConnection": AsyncConnection,
                "Connection": Connection,
                "AsyncConnectionPool": AsyncConnectionPool,
                "ConnectionPool": ConnectionPool,
                "RequestEncodingType": RequestEncodingType,
                "Body": Body,
                "State": State,
                "ChannelsPlugin": ChannelsPlugin,
                "WebSocket": WebSocket,
                "m": m,
                "schemas": schemas,
                "services": services,
                # Service types
                "ProductService": ProductService,
                "ShopService": ShopService,
                "RecommendationService": RecommendationService,
                "CompanyService": CompanyService,
                "InventoryService": InventoryService,
                "VertexAIService": VertexAIService,
                "OracleVectorSearchService": OracleVectorSearchService,
                "UserSessionService": UserSessionService,
                "ChatConversationService": ChatConversationService,
                "ResponseCacheService": ResponseCacheService,
                "SearchMetricsService": SearchMetricsService,
                "Request": Request,
                "HTMXRequest": HTMXRequest,
            },
        )
        return app_config

    def on_cli_init(self, cli: Group) -> None:
        from advanced_alchemy.extensions.litestar.cli import database_group

        from app.cli import bulk_embed, clear_cache, embed_new, load_fixtures, load_vectors, model_info, recommend
        from app.lib.settings import get_settings

        settings = get_settings()
        self.app_slug = settings.app.slug
        cli.add_command(recommend, name="recommend")
        cli.add_command(model_info, name="model-info")

        # Add our custom database commands
        database_group.add_command(load_fixtures, name="load-fixtures")  # type: ignore[arg-type]
        database_group.add_command(load_vectors, name="load-vectors")  # type: ignore[arg-type]

        # Add bulk embedding commands
        database_group.add_command(bulk_embed, name="bulk-embed")  # type: ignore[arg-type]
        database_group.add_command(embed_new, name="embed-new")  # type: ignore[arg-type]

        # Add cache management command
        database_group.add_command(clear_cache, name="clear-cache")  # type: ignore[arg-type]
