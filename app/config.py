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

import logging
import sys
from functools import lru_cache
from typing import cast

import structlog
from advanced_alchemy.extensions.litestar import (
    AlembicAsyncConfig,
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    async_autocommit_handler_maker,
)
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.logging.config import (
    LoggingConfig,
    StructLoggingConfig,
    default_logger_factory,
    default_structlog_processors,
    default_structlog_standard_lib_processors,
)
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.plugins.structlog import StructlogConfig
from litestar_oracledb import SyncOracleDatabaseConfig, SyncOraclePoolConfig
from litestar_vite import ViteConfig
from litestar_vite.inertia import InertiaConfig

from app.lib.settings import get_settings

_settings = get_settings()

csrf = CSRFConfig(
    secret=_settings.app.SECRET_KEY,
    cookie_secure=_settings.app.CSRF_COOKIE_SECURE,
    cookie_name=_settings.app.CSRF_COOKIE_NAME,
    header_name=_settings.app.CSRF_HEADER_NAME,
)
cors = CORSConfig(allow_origins=cast("list[str]", _settings.app.ALLOWED_CORS_ORIGINS))


alchemy = SQLAlchemyAsyncConfig(
    engine_instance=_settings.db.get_engine(),
    before_send_handler=async_autocommit_handler_maker(  # note: change the session scope key if using multiple engines
        commit_on_redirect=True,
    ),
    session_config=AsyncSessionConfig(expire_on_commit=False),
    alembic_config=AlembicAsyncConfig(
        render_as_batch=False,
        version_table_name=_settings.db.MIGRATION_DDL_VERSION_TABLE,
        script_config=_settings.db.MIGRATION_CONFIG,
        script_location=_settings.db.MIGRATION_PATH,
    ),
)
oracle = SyncOracleDatabaseConfig(
    pool_config=SyncOraclePoolConfig(user=_settings.db.USER, password=_settings.db.PASSWORD, dsn=_settings.db.DSN),
)
vite = ViteConfig(
    bundle_dir=_settings.vite.BUNDLE_DIR,
    resource_dir=_settings.vite.RESOURCE_DIR,
    template_dir=_settings.vite.TEMPLATE_DIR,
    use_server_lifespan=_settings.vite.USE_SERVER_LIFESPAN,
    dev_mode=_settings.vite.DEV_MODE,
    hot_reload=_settings.vite.HOT_RELOAD,
    is_react=_settings.vite.ENABLE_REACT_HELPERS,
    port=_settings.vite.PORT,
    host=_settings.vite.HOST,
)
inertia = InertiaConfig(
    root_template="index.html.j2",
)
session = CookieBackendConfig(secret=_settings.app.SECRET_KEY.encode("utf-8"))


@lru_cache
def _is_tty() -> bool:
    return bool(sys.stderr.isatty() or sys.stdout.isatty())


_structlog_processors = default_structlog_processors(as_json=not _is_tty())
log_level = getattr(logging, _settings.log.LEVEL)
log = StructlogConfig(
    enable_middleware_logging=False,
    structlog_logging_config=StructLoggingConfig(
        log_exceptions="always",
        processors=_structlog_processors,
        logger_factory=default_logger_factory(as_json=not _is_tty()),
        standard_lib_logging_config=LoggingConfig(
            root={"level": _settings.log.LEVEL, "handlers": ["queue_listener"]},
            formatters={
                "standard": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": default_structlog_standard_lib_processors(as_json=not _is_tty()),
                },
            },
            loggers={
                "saq": {
                    "propagate": False,
                    "level": _settings.log.SAQ_LEVEL,
                    "handlers": ["queue_listener"],
                },
                "_granian": {
                    "propagate": False,
                    "level": _settings.log.GRANIAN_ERROR_LEVEL,
                    "handlers": ["queue_listener"],
                },
                "granian.access": {
                    "propagate": False,
                    "level": _settings.log.GRANIAN_ACCESS_LEVEL,
                    "handlers": ["queue_listener"],
                },
                "sqlalchemy.engine": {
                    "propagate": False,
                    "level": _settings.log.SQLALCHEMY_LEVEL,
                    "handlers": ["queue_listener"],
                },
                "sqlalchemy.pool": {
                    "propagate": False,
                    "level": _settings.log.SQLALCHEMY_LEVEL,
                    "handlers": ["queue_listener"],
                },
                "urllib3": {
                    "propagate": False,
                    "level": _settings.log.SQLALCHEMY_LEVEL,
                    "handlers": ["queue_listener"],
                },
            },
        ),
    ),
    middleware_logging_config=LoggingMiddlewareConfig(
        request_log_fields=["method", "path", "path_params", "query"],
        response_log_fields=["status_code"],
    ),
)
