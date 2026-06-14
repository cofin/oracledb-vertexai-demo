# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the doctor CLI command diagnostic checks."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from click.testing import CliRunner
from tools.cli.doctor import doctor_command

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@patch("tools.cli.doctor.shutil.which")
@patch("tools.cli.doctor.run_command")
@patch("tools.cli.doctor.check_env_file")
def test_doctor_managed_mode_warns_on_low_memory(
    mock_check_env: MagicMock,
    mock_run_command: MagicMock,
    mock_which: MagicMock,
) -> None:
    """Verify that doctor command warns if container runtime has less than 8.5 GB allocated."""
    mock_check_env.return_value = True
    mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in {"uv", "docker"} else None

    def run_cmd_side_effect(cmd: list[str], check: bool = False) -> tuple[int, str, str]:
        if "uv" in cmd:
            return 0, "uv 0.1.0", ""
        if "docker" in cmd:
            return 0, "4294967296", ""
        return 0, "", ""

    mock_run_command.side_effect = run_cmd_side_effect

    result = CliRunner().invoke(doctor_command, ["--mode", "managed"])

    assert result.exit_code == 0
    assert "Allocated host memory is below 8.5 GB" in result.output
    assert "We recommend allocating at least 8 GiB" in result.output


@patch("tools.cli.doctor.shutil.which")
@patch("tools.cli.doctor.run_command")
@patch("tools.cli.doctor.check_env_file")
def test_doctor_managed_mode_no_warning_on_sufficient_memory(
    mock_check_env: MagicMock,
    mock_run_command: MagicMock,
    mock_which: MagicMock,
) -> None:
    """Verify that doctor command does not warn if container runtime has enough memory."""
    mock_check_env.return_value = True
    mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in {"uv", "docker"} else None

    def run_cmd_side_effect(cmd: list[str], check: bool = False) -> tuple[int, str, str]:
        if "uv" in cmd:
            return 0, "uv 0.1.0", ""
        if "docker" in cmd:
            return 0, "17179869184", ""
        return 0, "", ""

    mock_run_command.side_effect = run_cmd_side_effect

    result = CliRunner().invoke(doctor_command, ["--mode", "managed"])

    assert result.exit_code == 0
    assert "Allocated host memory is below 8.5 GB" not in result.output
