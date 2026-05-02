# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""``coffee`` CLI package.

The CLI surface is built by importing ``app.cli.main`` (defines the ``cli``
group) and ``app.cli.commands`` (side-effect registers every subcommand).
This package intentionally exposes neither — callers should invoke
``app.__main__:run_cli`` (the entry point) or ``app.cli.main:main`` directly.
"""
