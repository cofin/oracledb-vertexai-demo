# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner
from tools.cli.install import install_group
from tools.lib.utils import (
    build_antigravity_mcp_config,
    get_antigravity_mcp_config_path,
    write_antigravity_mcp_config,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_antigravity_mcp_paths_default_to_workspace_and_require_explicit_globals(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"

    assert get_antigravity_mcp_config_path(home=home) == tmp_path / ".agents" / "mcp_config.json"
    assert get_antigravity_mcp_config_path("workspace", workspace_root=tmp_path / "demo", home=home) == (
        tmp_path / "demo" / ".agents" / "mcp_config.json"
    )
    assert get_antigravity_mcp_config_path("ide", home=home) == home / ".gemini" / "config" / "mcp_config.json"
    assert get_antigravity_mcp_config_path("cli-global", home=home) == (
        home / ".gemini" / "antigravity-cli" / "mcp_config.json"
    )


def test_mcp_toolbox_config_uses_placeholders_not_process_secrets(monkeypatch: MonkeyPatch) -> None:
    password_key = "ORACLE_" + "PASSWORD"
    password_value = "real-" + "password"
    password_placeholder = "${" + password_key + "}"
    monkeypatch.setenv(password_key, password_value)
    monkeypatch.setenv("ORACLE_USERNAME", "real-user")
    monkeypatch.setenv("ORACLE_CONNECTION_STRING", "real-host:1521/freepdb1")
    monkeypatch.setenv("ORACLE_WALLET", "/real/wallet")

    config = build_antigravity_mcp_config()
    encoded = json.dumps(config)

    assert config["mcpServers"]["sqlcl"] == {"command": "sql", "args": ["-mcp"]}
    assert config["mcpServers"]["oracle-toolbox"]["command"] == "toolbox"
    assert config["mcpServers"]["oracle-toolbox"]["args"] == ["--prebuilt", "oracledb", "--stdio"]
    assert config["mcpServers"]["oracle-toolbox"]["env"] == {
        "ORACLE_CONNECTION_STRING": "${ORACLE_CONNECTION_STRING}",
        "ORACLE_USERNAME": "${ORACLE_USERNAME}",
        password_key: password_placeholder,
        "ORACLE_WALLET": "${ORACLE_WALLET}",
        "ORACLE_USE_OCI": "${ORACLE_USE_OCI}",
    }
    assert password_value not in encoded
    assert "real-user" not in encoded
    assert "real-host" not in encoded
    assert "/real/wallet" not in encoded


def test_write_antigravity_mcp_config_does_not_touch_legacy_gemini_settings(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    legacy_settings = home / ".gemini" / "settings.json"
    legacy_settings.parent.mkdir(parents=True)
    legacy_settings.write_text('{"mcpServers": {"legacy": null}}\n', encoding="utf-8")

    config_path = write_antigravity_mcp_config(home=home)

    assert config_path == tmp_path / ".agents" / "mcp_config.json"
    assert config_path.exists()
    assert json.loads(config_path.read_text(encoding="utf-8"))["mcpServers"]["oracle-toolbox"]["command"] == "toolbox"
    assert legacy_settings.read_text(encoding="utf-8") == '{"mcpServers": {"legacy": null}}\n'


def test_install_mcp_toolbox_dry_run_prints_guidance_without_writes(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    with CliRunner().isolated_filesystem(temp_dir=tmp_path):
        result = CliRunner().invoke(install_group, ["mcp-toolbox", "--dry-run"])

        assert result.exit_code == 0
        assert ".agents/mcp_config.json" in result.output
        assert "toolbox --prebuilt oracledb --stdio" in result.output
        assert "npx skills add oracle/skills/apex" in result.output
        assert "npx skills add oracle/skills/db" in result.output
        assert not Path(".agents/mcp_config.json").exists()
        assert not Path(".agents/plugins/oracle-skills").exists()
        assert not (tmp_path / "home" / ".gemini" / "settings.json").exists()


def test_install_mcp_toolbox_workspace_writes_antigravity_config_only(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    with CliRunner().isolated_filesystem(temp_dir=tmp_path):
        result = CliRunner().invoke(install_group, ["mcp-toolbox", "--workspace"])

        assert result.exit_code == 0
        config_path = Path(".agents/mcp_config.json")
        assert config_path.exists()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert set(config["mcpServers"]) >= {"sqlcl", "oracle-toolbox"}
        password_key = "ORACLE_" + "PASSWORD"
        assert config["mcpServers"]["oracle-toolbox"]["env"][password_key] == "${" + password_key + "}"
        assert not Path(".agents/plugins/oracle-skills").exists()
        assert not (tmp_path / "home" / ".gemini" / "settings.json").exists()
