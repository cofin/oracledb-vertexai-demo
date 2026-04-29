# Copyright 2026 Google LLC
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

from litestar.plugins import InitPluginProtocol
from litestar.plugins.problem_details import ProblemDetailsPlugin
from litestar.plugins.structlog import StructlogPlugin
from litestar_granian import GranianPlugin
from litestar_vite import VitePlugin
from sqlspec.extensions.litestar import SQLSpecPlugin as _SQLSpecPlugin

from app import config
from app.__metadata__ import __version__
from app.lib.settings import get_settings
from app.utils.domains import DomainPlugin, DomainPluginConfig

if TYPE_CHECKING:
    from click import Group
    from litestar.config.app import AppConfig


class SQLSpecPlugin(_SQLSpecPlugin):
    """SQLSpec plugin variant that does NOT auto-mount the ``db`` CLI group.

    Migrations are reachable only via ``python manage.py database <cmd>`` per
    ``[tool.sqlspec] config = "app.config.db"`` in pyproject.toml. The
    ``coffee`` CLI is hand-rolled (see ``app.cli.main``) and never invokes
    ``litestar_group()``, so suppressing the auto-mount here keeps the CLI
    surfaces aligned even if a future caller does build a litestar CLI tree
    against this plugin.
    """

    def on_cli_init(self, cli: Group) -> None:
        return None


class ApplicationCore(InitPluginProtocol):
    """Application core configuration plugin.

    Configures the Litestar application with routes, guards, and plugins.
    """

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure application

        Args:
            app_config: The :class:`AppConfig <.config.app.AppConfig>` instance.

        Returns:
            The updated application config.
        """
        from litestar.contrib.jinja import JinjaTemplateEngine
        from litestar.openapi import OpenAPIConfig
        from litestar.openapi.plugins import ScalarRenderPlugin
        from litestar.plugins.flash import FlashConfig, FlashPlugin
        from litestar.plugins.htmx import HTMXPlugin
        from litestar.template import TemplateConfig

        from app.lib import log
        from app.lib.settings import BASE_DIR

        settings = get_settings()

        # Logging
        app_config.middleware.insert(0, log.StructlogMiddleware)
        app_config.after_exception.append(log.after_exception_hook_handler)
        app_config.before_send.append(log.BeforeSendHandler())

        # Security
        app_config.cors_config = config.cors
        if not settings.app.DEBUG:
            app_config.csrf_config = config.csrf

        # Session
        app_config.stores = config.stores
        app_config.middleware.append(config.session_config.middleware)

        # Templates — owned by Litestar, scanned by the FlashPlugin Jinja globals
        # and the litestar-vite plugin's ``vite()``/``vite_hmr()`` helpers.
        app_config.template_config = TemplateConfig(
            engine=JinjaTemplateEngine,
            directory=BASE_DIR / "domain" / "web" / "templates",
        )

        # Plugins
        app_config.plugins.extend(
            [
                GranianPlugin(),
                SQLSpecPlugin(config.db_manager),
                StructlogPlugin(config=config.log),
                ProblemDetailsPlugin(config=config.problem_details),
                VitePlugin(config=config.vite),
                HTMXPlugin(),
                FlashPlugin(config=FlashConfig(template_config=app_config.template_config)),
                DomainPlugin(
                    DomainPluginConfig(
                        domain_packages=["app.domain"],
                        discover_controllers=True,
                        use_dishka_router=True,
                    )
                ),
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
