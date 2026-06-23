# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the standalone ORDS lifecycle CLI."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from tools.oracle.cli.ords import ords_group


def test_ords_start_command_starts_sidecar() -> None:
    """`infra ords start` starts the configured ORDS sidecar."""
    sidecar = MagicMock()

    with patch("tools.oracle.cli.ords._build_ords_sidecar", return_value=sidecar):
        result = CliRunner().invoke(ords_group, ["start"])

    assert result.exit_code == 0
    sidecar.start.assert_called_once_with(recreate=False)


def test_ords_restart_command_recreates_sidecar() -> None:
    """`infra ords restart` stops then recreates the ORDS sidecar."""
    sidecar = MagicMock()

    with patch("tools.oracle.cli.ords._build_ords_sidecar", return_value=sidecar):
        result = CliRunner().invoke(ords_group, ["restart", "--timeout", "7"])

    assert result.exit_code == 0
    sidecar.stop.assert_called_once_with(timeout=7)
    sidecar.start.assert_called_once_with(recreate=True)


def test_ords_status_command_reports_version_and_readiness() -> None:
    """`infra ords status` reports ORDS version, HTTP readiness, and APEX media state."""
    sidecar = MagicMock()
    sidecar.status.return_value = {
        "name": "oracle-ords",
        "status": "running",
        "image": "container-registry.oracle.com/database/ords:latest",
        "ports": "8181/tcp",
        "ords_version": "26.1.2",
        "minimum_version": "26.1.1",
        "preferred_version": "26.1.2",
        "version_status": "ok",
    }
    sidecar.http_ready.side_effect = [True, False]

    with (
        patch("tools.oracle.cli.ords._build_ords_sidecar", return_value=sidecar),
        patch("tools.oracle.cli.ords._apex_media_status", return_value=("26.1 (ready)", "patch verified")),
    ):
        result = CliRunner().invoke(ords_group, ["status"])

    assert result.exit_code == 0
    assert "ORDS Version" in result.output
    assert "26.1.2" in result.output
    assert "/ords/" in result.output
    assert "/i/" in result.output
    assert "APEX Media" in result.output
    assert "26.1 (ready)" in result.output
    assert "APEX Patch" in result.output
    assert "patch verified" in result.output


def test_ords_stop_command_stops_sidecar() -> None:
    """`infra ords stop` stops the configured ORDS sidecar."""
    sidecar = MagicMock()

    with patch("tools.oracle.cli.ords._build_ords_sidecar", return_value=sidecar):
        result = CliRunner().invoke(ords_group, ["stop", "--timeout", "9"])

    assert result.exit_code == 0
    sidecar.stop.assert_called_once_with(timeout=9)


def test_ords_logs_and_remove_commands_delegate_to_sidecar() -> None:
    """`infra ords logs` and `infra ords remove` delegate to the shared sidecar."""
    sidecar = MagicMock()

    with patch("tools.oracle.cli.ords._build_ords_sidecar", return_value=sidecar):
        logs = CliRunner().invoke(ords_group, ["logs", "--tail", "25"])
        remove = CliRunner().invoke(ords_group, ["remove", "--force"])

    assert logs.exit_code == 0
    assert remove.exit_code == 0
    sidecar.logs.assert_called_once_with(follow=False, tail=25)
    sidecar.remove.assert_called_once_with(force=True)
