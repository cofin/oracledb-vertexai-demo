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

from collections.abc import AsyncGenerator
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
        from sqlspec import AsyncDriverAdapterBase
        from sqlspec.adapters.oracledb import OracleAsyncDriver

        from app import config, schemas, services
        from app.lib import log
        from app.lib.settings import BASE_DIR, get_settings
        from app.server import plugins, startup
        from app.server.controllers import CoffeeChatController
        from app.server.exception_handlers import exception_handlers
        from app.services import (
            CacheService,
            ExemplarService,
            MetricsService,
            OracleVectorSearchService,
            ProductService,
            VertexAIService,
        )
        from app.services._adk.runner import ADKRunner
        from app.utils.serialization import general_dec_hook, numpy_array_enc_hook, numpy_array_predicate

        settings = get_settings()
        # logging
        app_config.middleware.insert(0, log.StructlogMiddleware)
        app_config.after_exception.append(log.after_exception_hook_handler)
        app_config.before_send.append(log.BeforeSendHandler())
        # security
        app_config.cors_config = config.cors
        app_config.csrf_config = config.csrf
        # session
        app_config.stores = config.stores
        app_config.middleware.append(config.session_config.middleware)
        # plugins
        app_config.plugins.extend(
            [
                plugins.granian,
                plugins.sqlspec,
                plugins.structlog,
                plugins.htmx,
            ],
        )
        # Set HTMXRequest as the default request class
        app_config.request_class = HTMXRequest
        app_config.template_config = config.templates
        # type encoders for numpy arrays (vector embeddings)
        import numpy as np

        app_config.type_encoders = {np.ndarray: numpy_array_enc_hook}
        app_config.type_decoders = [(numpy_array_predicate, general_dec_hook)]
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
                    html_mode=False,
                    send_as_attachment=False,
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
                # SQLSpec Oracle driver
                "OracleAsyncDriver": OracleAsyncDriver,
                "RequestEncodingType": RequestEncodingType,
                "Body": Body,
                "State": State,
                "ChannelsPlugin": ChannelsPlugin,
                "WebSocket": WebSocket,
                "AsyncGenerator": AsyncGenerator,
                "schemas": schemas,
                "services": services,
                "ProductService": ProductService,
                "CacheService": CacheService,
                "MetricsService": MetricsService,
                "ExemplarService": ExemplarService,
                "VertexAIService": VertexAIService,
                "OracleVectorSearchService": OracleVectorSearchService,
                "ADKRunner": ADKRunner,
                "Request": Request,
                "HTMXRequest": HTMXRequest,
                "AsyncDriverAdapterBase": AsyncDriverAdapterBase,
            },
        )
        return app_config

    def on_cli_init(self, cli: Group) -> None:
        from sqlspec.extensions.litestar.cli import database_group

        from app.cli import coffee_demo_group
        from app.cli.commands import export_fixtures_cmd, load_fixtures_cmd

        # Register custom database commands to the database group
        database_group.add_command(load_fixtures_cmd)
        database_group.add_command(export_fixtures_cmd)

        # Register groups
        cli.add_command(database_group)
        cli.add_command(coffee_demo_group)
