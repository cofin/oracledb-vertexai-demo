# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from tools.oracle.connection import ConnectionConfig, ConnectionTester, DeploymentMode

if TYPE_CHECKING:
    from pathlib import Path

DEMO_PASSWORD = "SuperSecret1"  # noqa: S105


def test_connection_tester_uses_wallet_directory_as_config_dir(monkeypatch: object, tmp_path: Path) -> None:
    """TNS aliases require config_dir in addition to wallet_location/TNS_ADMIN."""
    wallet_dir = tmp_path / "tns"
    wallet_dir.mkdir()
    cursor_context = MagicMock()
    cursor_context.__enter__.return_value.fetchone.return_value = ("OK",)
    connection = MagicMock()
    connection.cursor.return_value = cursor_context
    connection.version = "test-version"
    connection_context = MagicMock()
    connection_context.__enter__.return_value = connection
    oracledb = MagicMock()
    oracledb.connect.return_value = connection_context
    monkeypatch.setitem(sys.modules, "oracledb", oracledb)
    config = ConnectionConfig(
        mode=DeploymentMode.MANAGED,
        user="app",
        password=DEMO_PASSWORD,
        service_name="myatp_low",
        wallet_location=wallet_dir,
        wallet_password=DEMO_PASSWORD,
    )

    result = ConnectionTester()._do_connection_test(config)

    assert result.success
    connect_kwargs = oracledb.connect.call_args.kwargs
    assert connect_kwargs["wallet_location"] == str(wallet_dir)
    assert connect_kwargs["config_dir"] == str(wallet_dir)
