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
    from litestar.plugins.htmx import HTMXPlugin
    from litestar.plugins.problem_details import ProblemDetailsPlugin
    from litestar.plugins.structlog import StructlogPlugin
    from litestar_granian import GranianPlugin
    from litestar_vite import VitePlugin
    from sqlspec.extensions.litestar import SQLSpecPlugin as _SQLSpecBase

    from app.utils.domains import DomainPlugin


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


class _SQLSpecPlugin:
    """SQLSpec plugin variant that does not register the ``db`` CLI group.

    Migrations are reachable only through ``python manage.py database <cmd>``
    so the ``coffee`` CLI never auto-mounts a Litestar CLI tree.
    """


_initialized: bool = False

structlog: StructlogPlugin
granian: GranianPlugin
problem_details: ProblemDetailsPlugin
db: _SQLSpecBase
vite: VitePlugin
htmx: HTMXPlugin
flash: FlashPlugin
domain: DomainPlugin


def _initialize() -> None:
    """Materialize every plugin instance from the resolved configuration."""
    global _initialized  # noqa: PLW0603

    from litestar.plugins.flash import FlashConfig as _FlashConfig
    from litestar.plugins.flash import FlashPlugin as _FlashPlugin
    from litestar.plugins.htmx import HTMXPlugin as _HTMXPlugin
    from litestar.plugins.problem_details import ProblemDetailsPlugin as _ProblemDetailsPlugin
    from litestar.plugins.structlog import StructlogPlugin as _StructlogPlugin
    from litestar_granian import GranianPlugin as _GranianPlugin
    from litestar_vite import VitePlugin as _VitePlugin
    from sqlspec.extensions.litestar import SQLSpecPlugin as _SQLSpecPluginBase

    from app import config
    from app.utils.domains import DomainPlugin as _DomainPlugin
    from app.utils.domains import DomainPluginConfig as _DomainPluginConfig

    class SQLSpecPlugin(_SQLSpecPluginBase):
        """SQLSpec plugin that suppresses the ``db`` CLI group auto-mount."""

        def on_cli_init(self, cli: Group) -> None:
            return None

    g = globals()
    g["structlog"] = _StructlogPlugin(config=config.log)
    g["granian"] = _GranianPlugin()
    g["problem_details"] = _ProblemDetailsPlugin(config=config.problem_details)
    g["db"] = SQLSpecPlugin(config.db_manager)
    g["vite"] = _VitePlugin(config=config.vite)
    g["htmx"] = _HTMXPlugin()
    g["flash"] = _FlashPlugin(config=_FlashConfig(template_config=config.template))
    g["domain"] = _DomainPlugin(
        _DomainPluginConfig(
            domain_packages=["app.domain"],
            discover_controllers=True,
            use_dishka_router=True,
        ),
    )
    _initialized = True


def _reset() -> None:
    """Discard cached plugin instances so they are re-created on next access."""
    global _initialized  # noqa: PLW0603

    lazy_names = (
        "structlog",
        "granian",
        "problem_details",
        "db",
        "vite",
        "htmx",
        "flash",
        "domain",
    )
    g = globals()
    for name in lazy_names:
        g.pop(name, None)
    _initialized = False
