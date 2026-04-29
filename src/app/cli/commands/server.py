"""``coffee run`` — wraps ``litestar_granian.cli:run_command`` lazily.

Mirrors ``dma/accelerator/src/py/dma/cli/commands/server.py``: we don't call
``litestar_group()``, but we DO reuse the granian run command's parameter
shape. The wrapper materializes ``LitestarEnv`` and ``create_app`` only when
``run`` is invoked — never at help-text render time. That's the architectural
guarantee Phase 1B's ``test_coffee_help_does_not_construct_db_config`` exists
to enforce.
"""

from __future__ import annotations

from typing import Any

import rich_click as click
from litestar.cli._utils import LitestarEnv
from litestar_granian.cli import run_command as litestar_run_command

from app.cli.main import cli


def _create_run_command() -> click.Command:
    """Build the ``run`` command by copying granian's params and wrapping its callback.

    Construction details cribbed from ``dma/cli/commands/server.py:_create_run_command``:
    we keep the parameter list intact (so ``--host``, ``--port``, ``--reload`` etc.
    behave identically to ``litestar run``), but the callback constructs the
    Litestar app on demand instead of relying on a parent group having done it.
    """
    original_command = litestar_run_command

    @click.pass_context  # type: ignore[arg-type]
    def wrapped_run(ctx: click.Context, **kwargs: Any) -> None:
        """Run the API server using litestar-granian.

        Only at this point does the Litestar app actually get constructed —
        ``coffee --help`` never reaches this code path.
        """
        from app.server.asgi import create_app

        env = LitestarEnv.from_env("app.server.asgi:create_app")
        env.app = create_app()
        ctx.obj = env

        if original_command.callback is not None:
            original_command.callback(app=env.app, ctx=ctx, **kwargs)

    new_command = click.command(name="run", help=original_command.help)(wrapped_run)
    new_command.params = original_command.params.copy()
    return new_command


cli.add_command(_create_run_command())
