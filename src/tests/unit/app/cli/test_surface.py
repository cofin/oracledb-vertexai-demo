# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin the public ``coffee`` CLI surface."""

from __future__ import annotations

from click.testing import CliRunner

from app.cli.main import cli


def test_coffee_cli_keeps_end_user_upgrade_but_not_downgrade() -> None:
    from app.cli import commands as _commands  # noqa: F401

    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "upgrade" in result.output
    assert "upgrade" in cli.commands
    assert "downgrade" not in cli.commands
    assert "database" not in cli.commands
    assert "assets" not in cli.commands
