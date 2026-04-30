# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""``coffee`` CLI entry point."""

from __future__ import annotations

import os
import sys

import rich_click as click
import structlog
from rich.console import Console

from app.__metadata__ import __version__

console = Console()
logger = structlog.get_logger()


def _setup_environment() -> None:
    """Configure environment variables shared by every ``coffee`` invocation."""
    from app import config
    from app.lib.settings import get_settings

    _ = config.log.structlog_logging_config.configure()()
    config.setup_logging()
    settings = get_settings()
    os.environ.setdefault("LITESTAR_APP", "app.server.asgi:create_app")
    os.environ.setdefault("LITESTAR_APP_NAME", settings.app.NAME)
    os.environ.setdefault("LITESTAR_GRANIAN_IN_SUBPROCESS", "false")
    os.environ.setdefault("LITESTAR_GRANIAN_USE_LITESTAR_LOGGER", "true")


# rich-click presentation knobs.
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "yellow italic"
click.rich_click.ERRORS_SUGGESTION = "Try running the '--help' flag for more information."
click.rich_click.STYLE_COMMANDS_PANEL_BOX = "BLANK"
click.rich_click.STYLE_OPTIONS_PANEL_BOX = "BLANK"
click.rich_click.STYLE_COMMANDS_PANEL_BORDER = "none"
click.rich_click.STYLE_OPTIONS_PANEL_BORDER = "none"


@click.group(
    name="coffee",
    help=(
        "[bold cyan]Cymbal Coffee[/bold cyan] — Oracle 23ai + Vertex AI demo CLI.\n\n"
        "Production-app commands only. Database migrations, asset pipelines, and "
        "infrastructure live on [bold]python manage.py[/bold]."
    ),
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.version_option(version=__version__, prog_name="coffee")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """``coffee`` top-level entry point."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def main() -> None:
    """Entry point exposed via ``[project.scripts] coffee = app.__main__:run_cli``.

    Imports the commands sub-package (which side-effects ``@cli.command(...)``
    registration), then dispatches to the click group. Errors that escape are
    logged and re-raised as a non-zero exit so subprocess callers see the
    failure cleanly.
    """
    _setup_environment()

    # Side-effect: importing app.cli.commands registers every command on `cli`.
    from app.cli import commands as _commands  # noqa: F401

    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
