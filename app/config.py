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
import warnings
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
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.plugins.problem_details import ProblemDetailsConfig
from litestar.plugins.structlog import StructlogConfig
from litestar.stores.registry import StoreRegistry
from litestar.template import TemplateConfig
from sqlspec.adapters.oracledb.litestar import OracleAsyncStore
from sqlspec.base import SQLSpec

from app.lib import log as log_conf
from app.lib.settings import BASE_DIR, get_settings

_settings = get_settings()
settings = _settings  # Alias for compatibility

csrf = CSRFConfig(
    secret=_settings.app.SECRET_KEY,
    cookie_secure=_settings.app.CSRF_COOKIE_SECURE,
    cookie_name=_settings.app.CSRF_COOKIE_NAME,
    header_name=_settings.app.CSRF_HEADER_NAME,
)
cors = CORSConfig(allow_origins=cast("list[str]", _settings.app.ALLOWED_CORS_ORIGINS))
problem_details = ProblemDetailsConfig(enable_for_all_http_exceptions=True)

templates = TemplateConfig(directory=BASE_DIR / "server" / "templates", engine=JinjaTemplateEngine)

db_manager = SQLSpec()
db = _settings.db.create_config()
db_manager.add_config(db)
db_manager.load_sql_files(BASE_DIR / "db" / "sql")

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
                "sqlspec": {
                    "propagate": False,
                    "level": "INFO",
                    "handlers": ["queue_listener"],
                },
                "sqlglot": {
                    "propagate": False,
                    "level": "ERROR",
                    "handlers": ["queue_listener"],
                },
                "_granian": {
                    "propagate": False,
                    "level": _settings.log.GRANIAN_ERROR_LEVEL,
                    "handlers": ["queue_listener"],
                },
                "granian.server": {
                    "propagate": False,
                    "level": _settings.log.GRANIAN_ERROR_LEVEL,
                    "handlers": ["queue_listener"],
                },
                "granian.access": {
                    "propagate": False,
                    "level": _settings.log.GRANIAN_ACCESS_LEVEL,
                    "handlers": ["queue_listener"],
                },
                "google.adk": {
                    "propagate": False,
                    "level": _settings.log.LEVEL,
                    "handlers": ["queue_listener"],
                },
                "google.genai": {
                    "propagate": False,
                    "level": _settings.log.LEVEL,
                    "handlers": ["queue_listener"],
                },
                "google_genai": {
                    "propagate": False,
                    "level": _settings.log.LEVEL,
                    "handlers": ["queue_listener"],
                },
                "google_genai.types": {
                    "propagate": False,
                    "level": _settings.log.LEVEL,
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


def setup_logging() -> None:
    """Return a configured logger for the given name.

    Args:
        args: positional arguments to pass to the bound logger instance
        kwargs: keyword arguments to pass to the bound logger instance

    """
    if log.structlog_logging_config.standard_lib_logging_config:
        log.structlog_logging_config.standard_lib_logging_config.configure()
    log.structlog_logging_config.configure()
    structlog.configure(
        cache_logger_on_first_use=True,
        logger_factory=log.structlog_logging_config.logger_factory,
        processors=log.structlog_logging_config.processors,
        wrapper_class=structlog.make_filtering_bound_logger(settings.log.LEVEL),
    )

    # Capture Python warnings into logging so we can filter them
    logging.captureWarnings(True)

    # Add filter to suppress specific ADK/GenAI warnings
    adk_warning_filter = log_conf.SuppressADKWarningsFilter()

    # Apply to py.warnings logger (where Python warnings get captured)
    py_warnings_logger = logging.getLogger("py.warnings")
    py_warnings_logger.addFilter(adk_warning_filter)

    # Apply to specific Google loggers
    for logger_name in ["google.adk", "google.genai", "google_genai", "google_genai.types"]:
        logger = logging.getLogger(logger_name)
        logger.addFilter(adk_warning_filter)

    # Also apply to root logger and queue_listener handlers to catch in listener thread
    logging.root.addFilter(adk_warning_filter)

    # Suppress at Python warnings level too (belt and suspenders)
    warnings.filterwarnings(
        "ignore",
        message=r".*non-text parts in the response.*function_call.*",
        category=Warning,
        module=r"google_(?:genai|generativeai)(?:\..*)?$",
    )
