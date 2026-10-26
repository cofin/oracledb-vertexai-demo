# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Litestar plugin instances.

Plugin objects are lazily created on first attribute access (PEP 562)
to avoid triggering configuration I/O at module import time.

References:
    PEP 562 — https://peps.python.org/pep-0562/
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from litestar.plugins.flash import FlashConfig, FlashPlugin
from litestar.plugins.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin
from litestar.plugins.problem_details import ProblemDetailsPlugin
from litestar.plugins.structlog import StructlogPlugin
from litestar_autowire import AutowireConfig, AutowirePlugin
from litestar_granian import GranianPlugin
from litestar_htmx import HTMXPlugin
from litestar_mcp import A2AConfig, LitestarA2A, LitestarMCP
from litestar_queues import QueuePlugin
from litestar_security import SecurityPlugin
from litestar_vite import VitePlugin
from sqlspec.extensions.litestar import SQLSpecPlugin as _SQLSpecPluginBase

from app import config
from app.domain.ai.a2a import CoffeeAgentExecutor, build_a2a_call_context, build_agent_card
from app.lib import settings as app_settings
from app.lib.security import build_security_config
from app.server.mcp import build_mcp_config, build_mcp_route_opt

if TYPE_CHECKING:
    from click import Group

__all__ = (
    "a2a",
    "autowire",
    "db",
    "flash",
    "granian",
    "htmx",
    "mcp",
    "opentelemetry",
    "problem_details",
    "queue",
    "security",
    "structlog",
    "vite",
)


def __getattr__(name: str) -> object:
    """Lazily initialize plugins on first attribute access (PEP 562)."""
    if not _initialized:
        _initialize()
        try:
            return globals()[name]
        except KeyError:
            pass
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


class _SQLSpecPlugin(_SQLSpecPluginBase):
    """SQLSpec plugin that suppresses the ``db`` CLI group auto-mount."""

    def on_cli_init(self, cli: Group) -> None:
        del cli


_initialized: bool = False

structlog: StructlogPlugin
granian: GranianPlugin
problem_details: ProblemDetailsPlugin
db: _SQLSpecPluginBase
vite: VitePlugin
htmx: HTMXPlugin
flash: FlashPlugin
queue: QueuePlugin
autowire: AutowirePlugin
opentelemetry: OpenTelemetryPlugin
security: SecurityPlugin
mcp: LitestarMCP
a2a: LitestarA2A


def _initialize() -> None:
    """Materialize every plugin instance from the resolved configuration."""
    global _initialized

    settings = app_settings.get_settings()
    agent_card = build_agent_card(settings.app.URL)

    g = globals()
    g["structlog"] = StructlogPlugin(config=config.log)
    g["granian"] = GranianPlugin()
    g["problem_details"] = ProblemDetailsPlugin(config=config.problem_details)
    g["db"] = _SQLSpecPlugin(config.db_manager)
    g["vite"] = VitePlugin(config=config.vite)
    g["htmx"] = HTMXPlugin()
    g["flash"] = FlashPlugin(config=FlashConfig(template_config=config.template))
    g["queue"] = QueuePlugin(config=config.queue)
    g["autowire"] = AutowirePlugin(AutowireConfig(domain_packages=["app.domain"], integrations=["dishka", "queues"]))
    g["security"] = SecurityPlugin(config=build_security_config(settings))
    g["mcp"] = LitestarMCP(build_mcp_config(settings))
    g["a2a"] = LitestarA2A(
        agent_card=agent_card,
        request_handler=DefaultRequestHandler(
            agent_executor=CoffeeAgentExecutor(), task_store=InMemoryTaskStore(), agent_card=agent_card
        ),
        config=A2AConfig(
            path="/a2a",
            agent_card_path="/.well-known/agent-card.json",
            context_builder=build_a2a_call_context,
            route_opt=build_mcp_route_opt(settings),
        ),
    )
    if settings.otel.ENABLED:
        g["opentelemetry"] = OpenTelemetryPlugin(config=OpenTelemetryConfig(exclude=settings.otel.EXCLUDE_PATHS))
    _initialized = True


def _reset() -> None:
    """Discard cached plugin instances so they are re-created on next access."""
    global _initialized

    lazy_names = (
        "structlog",
        "granian",
        "problem_details",
        "db",
        "vite",
        "htmx",
        "flash",
        "queue",
        "autowire",
        "opentelemetry",
        "security",
        "mcp",
        "a2a",
    )
    g = globals()
    for name in lazy_names:
        g.pop(name, None)
    _initialized = False


config.register_reset_hook(_reset)
