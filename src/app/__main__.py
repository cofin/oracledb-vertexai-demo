"""Console-script entry point for ``coffee``.

Defined in ``pyproject.toml`` as ``coffee = "app.__main__:run_cli"``. We delegate
to the hand-rolled ``app.cli.main:main`` so this module stays a thin shim. The
old implementation called ``litestar_group()``; that's gone — Ch 4 Phase 1B
replaced it with an explicit rich_click group to keep ``coffee --help`` from
booting the Litestar app.
"""

from __future__ import annotations


def run_cli() -> None:
    """Application entry point — delegates to ``app.cli.main:main``."""
    from app.cli.main import main

    main()


if __name__ == "__main__":
    run_cli()
