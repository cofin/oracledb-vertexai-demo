# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""``coffee run`` — wraps ``litestar_granian.cli:run_command`` lazily."""

from __future__ import annotations

from app.cli._helpers.server import create_run_command
from app.cli.main import cli

cli.add_command(create_run_command())
