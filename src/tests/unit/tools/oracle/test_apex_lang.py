# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the SQLcl APEXlang wrapper."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from tools.oracle.apex_lang import ApexLang, ApexLangConfig, ApexLangError
from tools.oracle.sqlcl_installer import SQLclCapabilityStatus

if TYPE_CHECKING:
    from pathlib import Path

TEST_PASSWORD = "SuperSecret1"  # noqa: S105


def _capable_status() -> SQLclCapabilityStatus:
    return SQLclCapabilityStatus(
        installed=True,
        capable=True,
        version="26.1.2.0",
        minimum="26.1.2",
        message="SQLcl 26.1.2.0 supports APEXlang",
    )


def _wrapper(tmp_path: Path) -> tuple[ApexLang, MagicMock, Path]:
    sql_path = tmp_path / "bin" / "sql"
    installer = MagicMock()
    installer.sql_path.return_value = sql_path
    installer.apexlang_status.return_value = _capable_status()
    config = ApexLangConfig(
        src_root=tmp_path / "apex",
        host="localhost",
        port=1521,
        service_name="freepdb1",
        user="app",
        password=TEST_PASSWORD,
    )
    return ApexLang(installer=installer, config=config), installer, sql_path


def _completed(stdout: str = "ok\n") -> SimpleNamespace:
    return SimpleNamespace(args=[], returncode=0, stdout=stdout, stderr="")


def test_export_runs_sqlcl_with_apexlang_export_command(tmp_path: Path) -> None:
    """Export uses APEXlang format and keeps credentials out of process argv."""
    wrapper, _installer, sql_path = _wrapper(tmp_path)

    with patch("tools.oracle.apex_lang.subprocess.run", return_value=_completed()) as run:
        result = wrapper.export(app_id=105, alias="cymbal-coffee-ops")

    argv = run.call_args.args[0]
    stdin = run.call_args.kwargs["input"]
    assert argv == [str(sql_path), "-S", "/nolog"]
    assert TEST_PASSWORD not in " ".join(argv)
    assert f"connect app/{TEST_PASSWORD}@//localhost:1521/freepdb1" in stdin
    assert "apex export -applicationid 105 -exptype APEXLANG" in stdin
    assert f"-dir {tmp_path / 'apex'}" in stdin
    assert "-force" in stdin
    assert result.target_path == tmp_path / "apex" / "cymbal-coffee-ops"


def test_generate_runs_sqlcl_with_official_options(tmp_path: Path) -> None:
    """Generate passes the official SQLcl APEX command switches."""
    wrapper, _installer, _sql_path = _wrapper(tmp_path)

    with patch("tools.oracle.apex_lang.subprocess.run", return_value=_completed()) as run:
        wrapper.generate(alias="cymbal-coffee-ops", app_name="Cymbal Ops", app_id=100, force=True)

    stdin = run.call_args.kwargs["input"]
    assert "apex generate" in stdin
    assert f"-dir {tmp_path / 'apex'}" in stdin
    assert "-alias cymbal-coffee-ops" in stdin
    assert "-name 'Cymbal Ops'" in stdin
    assert "-id 100" in stdin
    assert "-force" in stdin


def test_validate_and_import_target_alias_directory(tmp_path: Path) -> None:
    """Validate and import read from src/apex/<alias>."""
    wrapper, _installer, _sql_path = _wrapper(tmp_path)

    with patch("tools.oracle.apex_lang.subprocess.run", return_value=_completed()) as run:
        wrapper.validate(alias="cymbal-coffee-ops")
        wrapper.import_app(alias="cymbal-coffee-ops", workspace="COFFEE", schema="app")

    validate_stdin = run.call_args_list[0].kwargs["input"]
    import_stdin = run.call_args_list[1].kwargs["input"]
    target = tmp_path / "apex" / "cymbal-coffee-ops"
    assert f"apex validate -input {target}" in validate_stdin
    assert f"apex import -input {target}" in import_stdin
    assert "-workspace COFFEE" in import_stdin
    assert "-schema app" in import_stdin


def test_validate_does_not_require_database_connection(tmp_path: Path) -> None:
    """SQLcl can validate APEXlang source without connecting to Oracle."""
    wrapper, _installer, _sql_path = _wrapper(tmp_path)

    with patch("tools.oracle.apex_lang.subprocess.run", return_value=_completed()) as run:
        wrapper.validate(alias="cymbal-coffee-ops")

    stdin = run.call_args.kwargs["input"]
    assert "apex validate" in stdin
    assert "connect app/" not in stdin


def test_missing_or_old_sqlcl_fails_before_subprocess(tmp_path: Path) -> None:
    """The wrapper fails fast with install/upgrade guidance when SQLcl cannot run APEXlang."""
    wrapper, installer, _sql_path = _wrapper(tmp_path)
    installer.apexlang_status.return_value = SQLclCapabilityStatus(
        installed=True,
        capable=False,
        version="26.1.1.0",
        minimum="26.1.2",
        message="SQLcl 26.1.2 or newer is required for APEXlang",
    )

    with patch("tools.oracle.apex_lang.subprocess.run") as run, pytest.raises(ApexLangError, match=r"26\.1\.2"):
        wrapper.validate(alias="cymbal-coffee-ops")

    run.assert_not_called()


def test_sqlcl_nonzero_exit_raises(tmp_path: Path) -> None:
    """Non-zero SQLcl status surfaces as an APEXlang error."""
    wrapper, _installer, _sql_path = _wrapper(tmp_path)
    failed = SimpleNamespace(args=[], returncode=1, stdout="", stderr="SP2-0000: error")

    with patch("tools.oracle.apex_lang.subprocess.run", return_value=failed), pytest.raises(ApexLangError):
        wrapper.validate(alias="cymbal-coffee-ops")


def test_sqlcl_connection_failure_raises_even_with_zero_exit(tmp_path: Path) -> None:
    """SQLcl can report connection errors on stdout while still exiting zero."""
    wrapper, _installer, _sql_path = _wrapper(tmp_path)
    failed = SimpleNamespace(
        args=[],
        returncode=0,
        stdout="Connection failed\nORA-12541: Cannot connect.\nSP2-0640: Not connected\n",
        stderr="",
    )

    with patch("tools.oracle.apex_lang.subprocess.run", return_value=failed), pytest.raises(
        ApexLangError,
        match="Connection failed",
    ):
        wrapper.import_app(alias="cymbal-coffee-ops")


def test_sqlcl_apexlang_compile_errors_raise_even_with_zero_exit(tmp_path: Path) -> None:
    """SQLcl can report APEXlang compile errors while still exiting zero."""
    wrapper, _installer, _sql_path = _wrapper(tmp_path)
    failed = SimpleNamespace(
        args=[],
        returncode=0,
        stdout="APEXLang Compile Errors:\nFile: application.apx\nError: Invalid property\n",
        stderr="",
    )

    with patch("tools.oracle.apex_lang.subprocess.run", return_value=failed), pytest.raises(
        ApexLangError,
        match="APEXLang Compile Errors",
    ):
        wrapper.import_app(alias="cymbal-coffee-ops")


def test_sqlcl_apexlang_import_errors_raise_even_with_zero_exit(tmp_path: Path) -> None:
    """SQLcl can report APEXlang import errors while still exiting zero."""
    wrapper, _installer, _sql_path = _wrapper(tmp_path)
    failed = SimpleNamespace(
        args=[],
        returncode=0,
        stdout="APEXLang Import Errors:\nFile:\nError: ORA-06550\n",
        stderr="",
    )

    with patch("tools.oracle.apex_lang.subprocess.run", return_value=failed), pytest.raises(
        ApexLangError,
        match="APEXLang Import Errors",
    ):
        wrapper.import_app(alias="cymbal-coffee-ops")
