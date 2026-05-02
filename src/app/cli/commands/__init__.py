# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Side-effecting registration of every ``coffee`` subcommand.

Importing this package mounts:
- ``server`` — ``coffee run`` (wraps granian)
- ``manage`` — bulk-embed / clear-cache / model-info / load-fixtures / export-fixtures

The two modules import ``cli`` from ``app.cli.main`` and use
``@cli.command(...)``, so simply importing them populates the click group.
"""

from app.cli.commands import manage as _manage
from app.cli.commands import server as _server
