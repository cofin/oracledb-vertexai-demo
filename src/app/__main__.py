# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Console-script entry point for the ``coffee`` CLI."""

from __future__ import annotations

from app.cli.main import main

__all__ = ("run_cli",)


def run_cli() -> None:
    """Entry point for the ``coffee`` CLI."""
    main()


if __name__ == "__main__":
    run_cli()
