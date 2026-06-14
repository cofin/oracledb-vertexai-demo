# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.lib.utils import create_env_interactive

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


def test_managed_env_template_aligns_app_and_wallet_credentials(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Managed env generation should configure both app and ADB wallet credentials."""
    monkeypatch.chdir(tmp_path)

    assert create_env_interactive("managed", non_interactive=True)

    env_content = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "DATABASE_URL=oracle+oracledb://app:SuperSecret1@myatp_low" in env_content
    assert "DATABASE_USER=app" in env_content
    assert "DATABASE_PASSWORD=SuperSecret1" in env_content
    assert "OEE_PASSWORD=SuperSecret1" in env_content
    assert "WALLET_PASSWORD=SuperSecret1" in env_content
    assert "TNS_ADMIN=.envs/tns" in env_content
    assert "DATABASE_SERVICE_NAME=myatp_low" in env_content
