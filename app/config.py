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

import os
from pathlib import Path
from typing import cast

import structlog
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.exceptions import NotFoundException
from litestar.logging.config import (
    LoggingConfig,
    StructLoggingConfig,
    default_logger_factory,
    default_structlog_processors,
    default_structlog_standard_lib_processors,
)
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.structlog import StructlogConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.registry import StoreRegistry
from litestar.template import TemplateConfig
from sqlspec.adapters.oracledb import OracleAsyncConfig
from sqlspec.adapters.oracledb.litestar import OracleAsyncStore
from sqlspec.base import SQLSpec

from app.lib.settings import BASE_DIR, get_settings

_settings = get_settings()

csrf = CSRFConfig(
    secret=_settings.app.SECRET_KEY,
    cookie_secure=_settings.app.CSRF_COOKIE_SECURE,
    cookie_name=_settings.app.CSRF_COOKIE_NAME,
    header_name=_settings.app.CSRF_HEADER_NAME,
)
cors = CORSConfig(allow_origins=cast("list[str]", _settings.app.ALLOWED_CORS_ORIGINS))

templates = TemplateConfig(directory=BASE_DIR / "server" / "templates", engine=JinjaTemplateEngine)


def create_oracle_config() -> OracleAsyncConfig:
    """Create Oracle database configuration based on connection mode (autonomous vs local)."""
    conn_params = _settings.db.get_connection_params()

    if _settings.db.is_autonomous:
        # Autonomous Database with wallet
        if not _settings.db.WALLET_LOCATION:
            msg = "WALLET_LOCATION or TNS_ADMIN environment variable must be set for Autonomous Database"
            raise ValueError(msg)

        # Set TNS_ADMIN for wallet location
        os.environ["TNS_ADMIN"] = _settings.db.WALLET_LOCATION

        pool_config = {
            "user": conn_params["user"],
            "password": conn_params["password"],
            "dsn": conn_params["dsn"],
            "wallet_password": conn_params["wallet_password"],
            "min": _settings.db.POOL_MIN_SIZE,
            "max": _settings.db.POOL_MAX_SIZE,
        }
    else:
        # Local/Standard Database
        pool_config = {
            "user": conn_params["user"],
            "password": conn_params["password"],
            "dsn": conn_params["dsn"],
            "min": _settings.db.POOL_MIN_SIZE,
            "max": _settings.db.POOL_MAX_SIZE,
        }

    return OracleAsyncConfig(
        pool_config=pool_config,
        migration_config={
            "version_table_name": "migrations",
            "script_location": _settings.db.MIGRATION_PATH,
            "project_root": Path(__file__).parent.parent,
            "include_extensions": ["adk", "litestar"],
        },
        extension_config={
            "adk": {
                "session_table": "adk_sessions",
                "events_table": "adk_events",
            },
            "litestar": {
                "session_table": "app_session",
                "commit_mode": "autocommit",
                "connection_key": "db_connection",
                "pool_key": "db_pool",
                "session_key": "db_session",
            },
        },
    )


# SQLSpec database manager
sqlspec = SQLSpec()
db = sqlspec.add_config(create_oracle_config())

# Litestar session store using Oracle
stores = StoreRegistry(stores={"sessions": OracleAsyncStore(config=db)})  # type: ignore[dict-item]
session_config = ServerSideSessionConfig(store="sessions")


log = StructlogConfig(
    enable_middleware_logging=False,
    structlog_logging_config=StructLoggingConfig(
        disable_stack_trace={NotFoundException, 404},
        log_exceptions="always",
        processors=default_structlog_processors(as_json=False),
        logger_factory=default_logger_factory(as_json=False),
        standard_lib_logging_config=LoggingConfig(
            root={"level": _settings.log.LEVEL, "handlers": ["queue_listener"]},
            formatters={
                "standard": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": default_structlog_standard_lib_processors(as_json=False),
                },
            },
            loggers={
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
            },
        ),
    ),
    middleware_logging_config=LoggingMiddlewareConfig(
        request_log_fields=["method", "path", "path_params", "query"],
        response_log_fields=["status_code"],
    ),
)

# Intent routing configuration
INTENT_THRESHOLDS = {
    "PRODUCT_RAG": 0.60,  # Lower threshold for product queries (more inclusive)
    "GENERAL_CONVERSATION": 0.70,
}

# Vector search configuration
VECTOR_SEARCH_CONFIG = {
    "min_vector_threshold": 0.5,
    "final_top_k": 5,
}
