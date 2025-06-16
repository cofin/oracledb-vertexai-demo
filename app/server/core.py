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
        from litestar.plugins.htmx import HTMXRequest
        from litestar.static_files import create_static_files_router
        from oracledb import AsyncConnection, AsyncConnectionPool, Connection, ConnectionPool

        from app import config, schemas, services
        from app.lib import log
        from app.lib.settings import BASE_DIR, get_settings
        from app.server import plugins, startup
        from app.server.controllers import CoffeeChatController
        from app.server.exception_handlers import exception_handlers
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
                plugins.granian,
                plugins.oracle,
                plugins.structlog,
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
        # startup hooks
        app_config.on_startup.append(startup.on_startup)
        # exception handlers
        app_config.exception_handlers.update(exception_handlers)  # type: ignore[arg-type]
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
                "schemas": schemas,
                "services": services,
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
        from app.cli import (
            bulk_embed,
            clear_cache,
            dump_data,
            embed_new,
            load_fixtures,
            load_vectors,
            model_info,
            truncate_tables,
        )

        cli.add_command(model_info, name="model-info")
        cli.add_command(load_fixtures, name="load-fixtures")
        cli.add_command(load_vectors, name="load-vectors")
        cli.add_command(bulk_embed, name="bulk-embed")
        cli.add_command(embed_new, name="embed-new")
        cli.add_command(clear_cache, name="clear-cache")
        cli.add_command(truncate_tables, name="truncate-tables")
        cli.add_command(dump_data, name="dump-data")
