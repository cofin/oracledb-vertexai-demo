# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin the public ``coffee`` CLI surface."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

import app.cli as cli_package
from app.cli.main import cli


def test_coffee_cli_keeps_end_user_upgrade_but_not_downgrade() -> None:
    from app.cli import commands

    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert Path(commands.__file__).name == "commands.py"
    assert "upgrade" in result.output
    assert "upgrade" in cli.commands
    assert "downgrade" not in cli.commands
    assert "database" not in cli.commands
    assert "assets" not in cli.commands


def test_cli_helpers_only_keep_substantial_workflow_modules() -> None:
    helper_files = {path.name for path in (Path(cli_package.__file__).parent / "_helpers").glob("*.py")}

    assert helper_files == {"__init__.py", "embeddings.py", "fixtures.py"}
