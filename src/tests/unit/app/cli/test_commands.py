# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
"""Behavioral tests for the ``coffee run`` command's port resolution."""

import pytest
from click.testing import CliRunner

from app.cli.commands import _create_run_command


def _resolve_port(monkeypatch: pytest.MonkeyPatch, args: list[str], env: dict[str, str | None]) -> int:
    captured: dict[str, int] = {}

    def fake_callback(**kwargs: object) -> None:  # granian callback stand-in
        captured["port"] = int(kwargs["port"])  # type: ignore[arg-type]

    # The wrapped command forwards to granian's callback via original_command.callback.
    monkeypatch.setattr("app.cli.commands.litestar_run_command.callback", fake_callback)
    # Avoid building the real Litestar app/env during the resolution test.
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
        ([], {"PORT": "9090", "LITESTAR_PORT": None}, 9090),  # AC1 Cloud Run
        ([], {"PORT": None, "LITESTAR_PORT": "5006"}, 5006),  # AC2 local .env
        ([], {"PORT": None, "LITESTAR_PORT": None}, 8000),  # AC3 bare default
        (["--port", "1234"], {"PORT": "9090", "LITESTAR_PORT": None}, 1234),  # AC4 flag wins
    ],
)
def test_run_port_resolution(monkeypatch, args, env, expected):
    assert _resolve_port(monkeypatch, args, env) == expected
