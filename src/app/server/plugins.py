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

if TYPE_CHECKING:
    from click import Group
    from litestar.plugins.flash import FlashPlugin
    from litestar.plugins.opentelemetry import OpenTelemetryPlugin
    from litestar.plugins.problem_details import ProblemDetailsPlugin
    from litestar.plugins.structlog import StructlogPlugin
    from litestar_autowire import AutowirePlugin
    from litestar_granian import GranianPlugin
    from litestar_htmx import HTMXPlugin
    from litestar_mcp import LitestarA2A, LitestarMCP
    from litestar_security import SecurityPlugin
    from litestar_vite import VitePlugin
    from sqlspec.extensions.litestar import SQLSpecPlugin as _SQLSpecBase


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


_initialized: bool = False

structlog: StructlogPlugin
granian: GranianPlugin
problem_details: ProblemDetailsPlugin
db: _SQLSpecBase
vite: VitePlugin
htmx: HTMXPlugin
flash: FlashPlugin
autowire: AutowirePlugin
opentelemetry: OpenTelemetryPlugin
security: SecurityPlugin
mcp: LitestarMCP
a2a: LitestarA2A


def _initialize() -> None:
    """Materialize every plugin instance from the resolved configuration."""
    global _initialized

    from pathlib import Path

    from a2a.server.request_handlers import DefaultRequestHandler as _DefaultRequestHandler
    from a2a.server.tasks import InMemoryTaskStore as _InMemoryTaskStore
    from litestar.plugins.flash import FlashConfig as _FlashConfig
    from litestar.plugins.flash import FlashPlugin as _FlashPlugin
    from litestar.plugins.opentelemetry import OpenTelemetryConfig as _OpenTelemetryConfig
    from litestar.plugins.opentelemetry import OpenTelemetryPlugin as _OpenTelemetryPlugin
    from litestar.plugins.problem_details import ProblemDetailsPlugin as _ProblemDetailsPlugin
    from litestar.plugins.structlog import StructlogPlugin as _StructlogPlugin
    from litestar_autowire import AutowireConfig as _AutowireConfig
    from litestar_autowire import AutowirePlugin as _AutowirePlugin
    from litestar_granian import GranianPlugin as _GranianPlugin
    from litestar_htmx import HTMXPlugin as _HTMXPlugin
    from litestar_mcp import A2AConfig as _A2AConfig
    from litestar_mcp import LitestarA2A as _LitestarA2A
    from litestar_mcp import LitestarMCP as _LitestarMCP
    from litestar_mcp import MCPConfig as _MCPConfig
    from litestar_mcp import MCPSkillsConfig as _MCPSkillsConfig
    from litestar_security import SecurityConfig as _SecurityConfig
    from litestar_security import SecurityHeadersConfig as _SecurityHeadersConfig
    from litestar_security import SecurityPlugin as _SecurityPlugin
    from litestar_security import public as _public
    from litestar_vite import VitePlugin as _VitePlugin
    from sqlspec.extensions.litestar import SQLSpecPlugin as _SQLSpecPluginBase

    from app import config
    from app.domain.ai.a2a.card import COFFEE_AGENT_CARD
    from app.domain.ai.a2a.executor import CoffeeAgentExecutor
    from app.lib.settings import get_settings

    class SQLSpecPlugin(_SQLSpecPluginBase):
        """SQLSpec plugin that suppresses the ``db`` CLI group auto-mount."""

        def on_cli_init(self, cli: Group) -> None:
            return None

    settings = get_settings()

    skill_paths = [p for p in (Path(".agents/skills"), Path("skills")) if p.is_dir()]
    skills_config = _MCPSkillsConfig(paths=skill_paths, directory_read=True) if skill_paths else None

    g = globals()
    g["structlog"] = _StructlogPlugin(config=config.log)
    g["granian"] = _GranianPlugin()
    g["problem_details"] = _ProblemDetailsPlugin(config=config.problem_details)
    g["db"] = SQLSpecPlugin(config.db_manager)
    g["vite"] = _VitePlugin(config=config.vite)
    g["htmx"] = _HTMXPlugin()
    g["flash"] = _FlashPlugin(config=_FlashConfig(template_config=config.template))
    g["autowire"] = _AutowirePlugin(_AutowireConfig(domain_packages=["app.domain"], integrations=["dishka"]))
    g["security"] = _SecurityPlugin(
        config=_SecurityConfig(headers=_SecurityHeadersConfig.hardened(), exclude=[r"^/static"])
    )
    g["mcp"] = _LitestarMCP(
        _MCPConfig(
            name="Cymbal Coffee MCP",
            instructions="Exposes coffee product catalog, vector search, store inventory, and skills.",
            skills=skills_config,
            route_opt={"auth": _public()},
        )
    )
    g["a2a"] = _LitestarA2A(
        agent_card=COFFEE_AGENT_CARD,
        request_handler=_DefaultRequestHandler(
            agent_executor=CoffeeAgentExecutor(), task_store=_InMemoryTaskStore(), agent_card=COFFEE_AGENT_CARD
        ),
        config=_A2AConfig(path="/a2a", agent_card_path="/.well-known/agent-card.json", route_opt={"auth": _public()}),
    )
    if settings.otel.ENABLED:
        g["opentelemetry"] = _OpenTelemetryPlugin(config=_OpenTelemetryConfig(exclude=settings.otel.EXCLUDE_PATHS))
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
