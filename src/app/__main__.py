# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Console-script entry point for the ``coffee`` CLI."""

from __future__ import annotations


def run_cli() -> None:
    """Entry point for the ``coffee`` CLI."""
    from app.cli.main import main

    main()


if __name__ == "__main__":
    run_cli()
