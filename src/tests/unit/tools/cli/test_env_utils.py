# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.lib.utils import create_env_interactive

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


def test_managed_env_template_targets_local_container(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Managed env generation should target the local gvenzl container on freepdb1."""
    monkeypatch.chdir(tmp_path)

    assert create_env_interactive("managed", non_interactive=True)

    env_content = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "DATABASE_USER=app" in env_content
    assert "DATABASE_PASSWORD=SuperSecret1" in env_content
    assert "DATABASE_HOST=localhost" in env_content
    assert "DATABASE_PORT=1521" in env_content
    assert "DATABASE_SERVICE_NAME=freepdb1" in env_content

    # Local container must stay non-autonomous: no wallet/URL keys that would flip
    # DatabaseSettings.is_autonomous to True and route through the wallet/SSL branch.
    assert "DATABASE_URL=" not in env_content
    assert "WALLET_PASSWORD=" not in env_content
    assert "TNS_ADMIN=" not in env_content
    assert "OEE_PASSWORD=" not in env_content
