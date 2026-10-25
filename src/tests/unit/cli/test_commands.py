# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Behavioral tests for `coffee run` port resolution and `configure-apex-cdn`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import oracledb
import pytest
from click.testing import CliRunner

from app.cli.commands import _create_run_command
from app.cli.main import cli

if TYPE_CHECKING:
    from pathlib import Path


def _build_mock_dbms_output_conn() -> MagicMock:
    """Build a mocked `oracledb.Connection` emitting a single `DBMS_OUTPUT` confirmation line."""
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_cursor.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value = mock_cursor

    mock_num_lines_var = MagicMock()
    mock_num_lines_var.getvalue.side_effect = [1, 0]
    mock_cursor.var.return_value = mock_num_lines_var

    mock_lines_var = MagicMock()
    mock_lines_var.getvalue.side_effect = [["APEX IMAGE_PREFIX successfully updated to CDN"], []]
    mock_cursor.arrayvar.return_value = mock_lines_var
    return mock_conn


def _resolve_port(monkeypatch: pytest.MonkeyPatch, args: list[str], env: dict[str, str | None]) -> int:
    """Invoke `_create_run_command` with mocked Granian callback and return resolved port."""
    captured: dict[str, int] = {}

    def fake_callback(**kwargs: Any) -> None:
        captured["port"] = int(kwargs["port"])

    monkeypatch.setattr("app.cli.commands.litestar_run_command.callback", fake_callback)
    monkeypatch.setattr("app.server.asgi.create_app", object)
    monkeypatch.setattr(
        "litestar.cli._utils.LitestarEnv.from_env", classmethod(lambda cls, _p: type("E", (), {"app": None})())
    )
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    result = CliRunner().invoke(_create_run_command(), args, standalone_mode=False)
    assert result.exit_code == 0, result.output
    return captured["port"]


@pytest.mark.parametrize(
    ("args", "env", "expected"),
    [
        ([], {"PORT": "9090", "LITESTAR_PORT": None}, 9090),
        ([], {"PORT": None, "LITESTAR_PORT": "5006"}, 5006),
        ([], {"PORT": None, "LITESTAR_PORT": None}, 8000),
        (["--port", "1234"], {"PORT": "9090", "LITESTAR_PORT": None}, 1234),
    ],
)
def test_run_port_resolution(
    monkeypatch: pytest.MonkeyPatch, args: list[str], env: dict[str, str | None], expected: int
) -> None:
    """Verify `coffee run` resolves `--port`, `PORT`, `LITESTAR_PORT`, and `8000` in precedence order."""
    assert _resolve_port(monkeypatch, args, env) == expected


def test_configure_apex_cdn_command_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify `configure-apex-cdn` loads packaged SQL, connects as SYSDBA, and executes the PL/SQL block."""
    monkeypatch.chdir(tmp_path)
    for key in ("DATABASE_URL", "WALLET_LOCATION", "WALLET_PASSWORD", "TNS_ADMIN"):
        monkeypatch.delenv(key, raising=False)

    mock_conn = _build_mock_dbms_output_conn()
    mock_connect = MagicMock(return_value=mock_conn)
    monkeypatch.setattr("app.cli._helpers.ords.oracledb.connect", mock_connect)

    runner = CliRunner()
    result = runner.invoke(cli, ["configure-apex-cdn"], env={"DATABASE_SYSTEM_PASSWORD": "test-password"})

    assert result.exit_code == 0, result.output
    assert "APEX IMAGE_PREFIX successfully updated to CDN" in result.output
    assert "✓ APEX CDN configuration completed successfully!" in result.output
    mock_connect.assert_called_once()
    assert mock_connect.call_args[1]["user"] == "SYS"
    assert mock_connect.call_args[1]["password"] == "test-password"
    assert mock_connect.call_args[1]["mode"] == oracledb.AUTH_MODE_SYSDBA


def test_configure_apex_cdn_command_autonomous_wallet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify `configure-apex-cdn` connects as `ADMIN` with wallet when Autonomous DB settings are active."""
    monkeypatch.chdir(tmp_path)
    wallet_dir = tmp_path / "tns"
    wallet_dir.mkdir()
    (wallet_dir / "tnsnames.ora").write_text("myatp_low = (DESCRIPTION=...)\n", encoding="utf-8")

    monkeypatch.delenv("DATABASE_SYSTEM_PASSWORD", raising=False)
    monkeypatch.delenv("ORACLE_SYSTEM_PASSWORD", raising=False)
    monkeypatch.setattr("app.cli._helpers.ords.extract_oracle_wallet_zip", MagicMock(return_value=wallet_dir))
    mock_conn = _build_mock_dbms_output_conn()
    mock_connect = MagicMock(return_value=mock_conn)
    monkeypatch.setattr("app.cli._helpers.ords.oracledb.connect", mock_connect)

    result = CliRunner().invoke(
        cli,
        ["configure-apex-cdn"],
        env={
            "DATABASE_URL": "myatp_low",
            "WALLET_LOCATION": str(wallet_dir),
            "WALLET_PASSWORD": "WalletSecret1",
            "DATABASE_ADMIN_PASSWORD": "AdminSecret1",
        },
    )

    assert result.exit_code == 0, result.output
    mock_connect.assert_called_once_with(
        user="ADMIN",
        password="AdminSecret1",
        dsn="myatp_low",
        config_dir=str(wallet_dir),
        wallet_location=str(wallet_dir),
        wallet_password="WalletSecret1",
    )


def test_configure_apex_cdn_command_missing_password(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify `configure-apex-cdn` fails when `DATABASE_SYSTEM_PASSWORD` is absent on non-autonomous PDBs."""
    monkeypatch.chdir(tmp_path)
    for key in (
        "DATABASE_URL",
        "WALLET_LOCATION",
        "WALLET_PASSWORD",
        "TNS_ADMIN",
        "DATABASE_SYSTEM_PASSWORD",
        "ORACLE_SYSTEM_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["configure-apex-cdn"])

    assert result.exit_code != 0
    assert "DATABASE_SYSTEM_PASSWORD environment variable is not set" in result.output
