# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Private helpers for ``coffee run``."""

from __future__ import annotations

from typing import Any

import rich_click as click
from litestar.cli._utils import LitestarEnv
from litestar_granian.cli import run_command as litestar_run_command


def create_run_command() -> click.Command:
    """Build the ``run`` command by copying granian's params and wrapping its callback."""
    original_command = litestar_run_command

    @click.pass_context  # type: ignore[arg-type]
    def wrapped_run(ctx: click.Context, **kwargs: Any) -> None:
        from app.server.asgi import create_app

        env = LitestarEnv.from_env("app.server.asgi:create_app")
        env.app = create_app()
        ctx.obj = env

        if original_command.callback is not None:
            original_command.callback(app=env.app, ctx=ctx, **kwargs)

    new_command = click.command(name="run", help=original_command.help)(wrapped_run)
    new_command.params = original_command.params.copy()
    return new_command
