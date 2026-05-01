# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Contracts for the hand-rolled ``coffee`` CLI surface."""

from __future__ import annotations

from pathlib import Path


def test_coffee_keeps_fixture_lifecycle_commands() -> None:
    import app.cli.commands  # noqa: F401
    from app.cli.main import cli

    assert "bulk-embed" in cli.commands
    assert "export-fixtures" in cli.commands
    assert "load-fixtures" in cli.commands


def test_manage_cli_commands_use_async_inject_instead_of_local_run_wrappers() -> None:
    source = Path("src/app/cli/commands/manage.py").read_text(encoding="utf-8")

    assert "sqlspec.utils.sync_tools" not in source
    assert "run_(" not in source
    assert "async def _load_fixtures" not in source
    assert "async def _export_fixtures" not in source


def test_public_cli_modules_keep_implementation_helpers_private() -> None:
    command_paths = [
        Path("src/app/cli/main.py"),
        Path("src/app/cli/commands/manage.py"),
        Path("src/app/cli/commands/server.py"),
    ]

    for path in command_paths:
        source = path.read_text(encoding="utf-8")
        assert "\ndef _" not in source, path
        assert "\nasync def _" not in source, path


def test_data_ops_helper_is_a_small_compatibility_surface() -> None:
    source = Path("src/app/cli/_helpers/data_ops.py").read_text(encoding="utf-8")

    assert len(source.splitlines()) <= 80
    assert "from app.cli._helpers.embeddings import" in source
    assert "from app.cli._helpers.fixtures import" in source
    assert "from app.cli._helpers.database import" in source
