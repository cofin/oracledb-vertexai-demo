# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Application configuration objects.

Public attributes are lazily initialized on first access via the
module-level ``__getattr__`` hook from PEP 562. Importing this module
performs no I/O and triggers no ``.env`` loading; tests can set
environment variables before any config object is materialized.

Use ``_reset()`` in tests to discard cached state so subsequent access
re-initializes from the current environment.

References:
    PEP 562 — Module ``__getattr__`` and ``__dir__``:
        https://peps.python.org/pep-0562/
    PEP 563 — Postponed Evaluation of Annotations
        (``from __future__ import annotations``):
        https://peps.python.org/pep-0563/
"""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, cast

import structlog
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.exceptions import NotAuthorizedException, NotFoundException, PermissionDeniedException
from litestar.logging.config import LoggingConfig, StructLoggingConfig, default_logger_factory
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.plugins.jinja import JinjaTemplateEngine
from litestar.plugins.problem_details import ProblemDetailsConfig
from litestar.plugins.structlog import StructlogConfig
from litestar.stores.registry import StoreRegistry
from litestar.template import TemplateConfig
from sqlspec.adapters.oracledb.litestar import OracleAsyncStore
from sqlspec.base import SQLSpec

from app.lib import log as log_conf
from app.lib import settings as app_settings
from app.lib.settings import BASE_DIR, Settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.stores.base import Store
    from litestar_queues import QueueConfig
    from litestar_vite import ViteConfig
    from sqlspec.adapters.oracledb import OracleAsyncConfig

__all__ = (
    "cors",
    "csrf",
    "db",
    "db_manager",
    "log",
    "problem_details",
    "queue",
    "queue_db",
    "register_reset_hook",
    "session_config",
    "setup_logging",
    "stores",
    "template",
    "vite",
)

_initialized: bool = False
_reset_hooks: list[Callable[[], None]] = []

_settings: Settings
db_manager: SQLSpec
db: OracleAsyncConfig
queue_db: OracleAsyncConfig
queue: QueueConfig
stores: StoreRegistry
session_config: ServerSideSessionConfig
csrf: CSRFConfig
cors: CORSConfig
problem_details: ProblemDetailsConfig
vite: ViteConfig
log: StructlogConfig
template: TemplateConfig


def __getattr__(name: str) -> object:
    """Lazily initialize configuration on first attribute access (PEP 562)."""
    if not _initialized:
        _initialize()
        try:
            return globals()[name]
        except KeyError:
            pass
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def register_reset_hook(hook: Callable[[], None]) -> None:
    """Register a callback invoked whenever ``_reset()`` clears cached configuration."""
    if hook not in _reset_hooks:
        _reset_hooks.append(hook)


def setup_logging() -> None:
    """Configure structlog and stdlib logging plus noise-suppression filters."""
    _install_warning_filters()

    if not _initialized:
        _initialize()

    structlog_config = cast("StructlogConfig", globals()["log"])
    settings = cast("Settings", globals()["_settings"])

    if structlog_config.structlog_logging_config.standard_lib_logging_config:
        structlog_config.structlog_logging_config.standard_lib_logging_config.configure()
    structlog_config.structlog_logging_config.configure()
    structlog.configure(
        cache_logger_on_first_use=True,
        logger_factory=structlog_config.structlog_logging_config.logger_factory,
        processors=structlog_config.structlog_logging_config.processors,
        wrapper_class=structlog.make_filtering_bound_logger(settings.log.LEVEL),
    )
    logging.captureWarnings(True)

    logging.getLogger("asyncio").addFilter(log_conf.SuppressAsyncioTaskExceptionFilter())
    logging.getLogger("_granian").addFilter(log_conf.SuppressGranianExcInfoFilter())


def _initialize() -> None:
    """Materialize every public attribute from the current environment."""
    global _initialized

    settings = app_settings.get_settings()
    log_as_json = not log_conf.is_tty()
    db_cfg = settings.db.create_config()
    queue_db_cfg = settings.db.get_queue_config()
    queue_cfg = settings.queue.get_config(queue_db_cfg)
    db_mgr = SQLSpec(observability_config=db_cfg.observability_config)
    db_mgr.add_config(db_cfg)
    db_mgr.load_sql_files(BASE_DIR / "db" / "sql")

    store_registry = StoreRegistry(stores={"sessions": cast("Store", OracleAsyncStore(config=db_cfg))})

    structlog_config = StructlogConfig(
        enable_middleware_logging=False,
        structlog_logging_config=StructLoggingConfig(
            disable_stack_trace={
                400,
                401,
                403,
                404,
                409,
                503,
                NotAuthorizedException,
                PermissionDeniedException,
                NotFoundException,
            },
            log_exceptions="always",
            processors=log_conf.structlog_processors(as_json=log_as_json),
            logger_factory=default_logger_factory(as_json=log_as_json),
            standard_lib_logging_config=LoggingConfig(
                log_exceptions="always",
                disable_stack_trace={
                    400,
                    401,
                    403,
                    404,
                    409,
                    503,
                    NotAuthorizedException,
                    PermissionDeniedException,
                    NotFoundException,
                },
                root={"level": logging.getLevelName(settings.log.LEVEL), "handlers": ["queue_listener"]},
                formatters={
                    "standard": {
                        "()": "structlog.stdlib.ProcessorFormatter",
                        "processors": log_conf.stdlib_logger_processors(as_json=log_as_json),
                    }
                },
                loggers={
                    "sqlspec": {
                        "propagate": False,
                        "level": settings.log.SQLSPEC_LEVEL,
                        "handlers": ["queue_listener"],
                    },
                    "sqlglot": {"propagate": False, "level": "ERROR", "handlers": ["queue_listener"]},
                    "_granian": {
                        "propagate": False,
                        "level": settings.log.GRANIAN_ERROR_LEVEL,
                        "handlers": ["queue_listener"],
                    },
                    "granian.server": {
                        "propagate": False,
                        "level": settings.log.GRANIAN_ERROR_LEVEL,
                        "handlers": ["queue_listener"],
                    },
                    "granian.access": {
                        "propagate": False,
                        "level": settings.log.GRANIAN_ACCESS_LEVEL,
                        "handlers": ["queue_listener"],
                    },
                    "google.genai": {"propagate": False, "level": settings.log.LEVEL, "handlers": ["queue_listener"]},
                    "google_genai": {"propagate": False, "level": settings.log.LEVEL, "handlers": ["queue_listener"]},
                    "google_genai.types": {
                        "propagate": False,
                        "level": settings.log.LEVEL,
                        "handlers": ["queue_listener"],
                    },
                },
            ),
        ),
        middleware_logging_config=LoggingMiddlewareConfig(
            request_log_fields=["method", "path", "path_params", "query"], response_log_fields=["status_code"]
        ),
    )

    g = globals()
    g["_settings"] = settings
    g["db_manager"] = db_mgr
    g["db"] = db_cfg
    g["queue_db"] = queue_db_cfg
    g["queue"] = queue_cfg
    g["stores"] = store_registry
    g["session_config"] = ServerSideSessionConfig(store="sessions")
    g["csrf"] = CSRFConfig(
        secret=settings.app.SECRET_KEY,
        cookie_secure=settings.app.CSRF_COOKIE_SECURE,
        cookie_name=settings.app.CSRF_COOKIE_NAME,
        header_name=settings.app.CSRF_HEADER_NAME,
    )
    g["cors"] = CORSConfig(allow_origins=settings.app.ALLOWED_CORS_ORIGINS)
    g["problem_details"] = ProblemDetailsConfig(enable_for_all_http_exceptions=True)
    g["vite"] = settings.vite.get_config()
    g["log"] = structlog_config
    g["template"] = TemplateConfig(engine=JinjaTemplateEngine, directory=BASE_DIR / "domain" / "web" / "templates")
    _initialized = True


def _reset() -> None:
    """Discard cached configuration so the next access re-initializes from env."""
    global _initialized

    lazy_names = (
        "_settings",
        "db_manager",
        "db",
        "queue_db",
        "queue",
        "stores",
        "session_config",
        "csrf",
        "cors",
        "problem_details",
        "vite",
        "log",
        "template",
    )
    g = globals()
    for name in lazy_names:
        g.pop(name, None)

    Settings.from_env.cache_clear()
    _initialized = False

    for hook in tuple(_reset_hooks):
        hook()


def _install_warning_filters() -> None:
    """Suppress known noisy third-party warnings before app imports trigger them."""
    warnings.filterwarnings(
        "ignore",
        message=r".*non-text parts in the response.*function_call.*",
        category=Warning,
        module=r"google_(?:genai|generativeai)(?:\..*)?$",
    )
    warnings.filterwarnings(
        "ignore",
        message=r".*authlib\.jose module is deprecated.*",
        category=Warning,
        module=r"authlib\._joserfc_helpers",
    )
