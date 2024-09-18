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

    __slots__ = ("app_slug",)
    app_slug: str

    def __init__(self) -> None:
        """Initialize ``ApplicationConfigurator``.

        Args:
            config: configure and start SAQ.
        """

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application

        Args:
            app_config: The :class:`AppConfig <.config.app.AppConfig>` instance.
        """
        from langchain_community.chat_message_histories import ChatMessageHistory
        from langchain_community.vectorstores.oraclevs import OracleVS
        from langchain_core.embeddings import Embeddings
        from langchain_core.runnables import Runnable
        from langchain_core.vectorstores import VectorStore
        from litestar import WebSocket
        from litestar.channels import ChannelsPlugin
        from litestar.datastructures import State
        from litestar.enums import RequestEncodingType
        from litestar.openapi.config import OpenAPIConfig
        from litestar.openapi.plugins import ScalarRenderPlugin, SwaggerRenderPlugin
        from litestar.params import Body
        from oracledb import AsyncConnection, AsyncConnectionPool, Connection, ConnectionPool

        from app import config
        from app.__metadata__ import __version__ as current_version
        from app.domain.coffee.controllers import CoffeeChatController
        from app.lib import log
        from app.lib.dependencies import create_collection_dependencies
        from app.lib.settings import get_settings
        from app.server import plugins

        settings = get_settings()
        self.app_slug = settings.app.slug

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
                plugins.vite,
                plugins.inertia,
            ],
        )
        # openapi
        app_config.openapi_config = OpenAPIConfig(
            title=settings.app.NAME,
            version=current_version,
            use_handler_docstrings=True,
            render_plugins=[ScalarRenderPlugin(version="1.24.46"), SwaggerRenderPlugin()],
        )
        # routes
        app_config.route_handlers.extend(
            [
                CoffeeChatController,
            ],
        )
        # deps
        app_config.dependencies.update(create_collection_dependencies())
        # signatures
        app_config.signature_namespace.update(
            {
                "ChatMessageHistory": ChatMessageHistory,
                "Embeddings": Embeddings,
                "VectorStore": VectorStore,
                "OracleVS": OracleVS,
                "AsyncConnection": AsyncConnection,
                "Connection": Connection,
                "AsyncConnectionPool": AsyncConnectionPool,
                "ConnectionPool": ConnectionPool,
                "Runnable": Runnable,
                "RequestEncodingType": RequestEncodingType,
                "Body": Body,
                "State": State,
                "ChannelsPlugin": ChannelsPlugin,
                "WebSocket": WebSocket,
            },
        )
        return app_config

    def on_cli_init(self, cli: Group) -> None:
        from app.cli.commands import recommend
        from app.lib.settings import get_settings

        settings = get_settings()
        self.app_slug = settings.app.slug
        cli.add_command(recommend, name="recommend")
