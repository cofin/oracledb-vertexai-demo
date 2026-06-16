# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the doctor CLI command diagnostic checks."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from tools.cli.doctor import doctor_command

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.mark.parametrize(
    ("docker_bytes", "warning_expected"),
    [
        ("4294967296", True),  # 4 GiB -> below the 8.5 GB floor
        ("17179869184", False),  # 16 GiB -> sufficient
    ],
)
@patch("tools.cli.doctor.shutil.which")
@patch("tools.cli.doctor.run_command")
@patch("tools.cli.doctor.check_env_file")
def test_doctor_managed_mode_warns_only_below_memory_floor(
    mock_check_env: MagicMock,
    mock_run_command: MagicMock,
    mock_which: MagicMock,
    docker_bytes: str,
    warning_expected: bool,
) -> None:
    """Doctor warns when the container runtime has less than 8.5 GB allocated."""
    mock_check_env.return_value = True
    mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in {"uv", "docker"} else None

    def run_cmd_side_effect(cmd: list[str], check: bool = False) -> tuple[int, str, str]:
        if "uv" in cmd:
            return 0, "uv 0.1.0", ""
        if "docker" in cmd:
            return 0, docker_bytes, ""
        return 0, "", ""

    mock_run_command.side_effect = run_cmd_side_effect

    result = CliRunner().invoke(doctor_command, ["--mode", "managed"])

    assert result.exit_code == 0
    warning = "Allocated host memory is below 8.5 GB"
    assert (warning in result.output) is warning_expected
    if warning_expected:
        assert "We recommend allocating at least 8 GiB" in result.output
