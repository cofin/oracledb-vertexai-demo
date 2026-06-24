# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for SQLcl capability detection."""

from __future__ import annotations

from tools.oracle.sqlcl_installer import SQLclInstaller


def test_parse_version_from_release_output() -> None:
    """SQLcl release output yields a numeric version tuple."""
    output = "SQLcl: Release 26.1.2.0 Production on Tue Jun 23 00:00:00 2026"

    assert SQLclInstaller.parse_version(output) == (26, 1, 2, 0)


def test_parse_version_from_short_output() -> None:
    """Shorter version formats are supported for mocked and platform output."""
    output = "Oracle SQLcl Version 26.1.2"

    assert SQLclInstaller.parse_version(output) == (26, 1, 2)


def test_parse_version_returns_none_for_unrecognised_output() -> None:
    """Garbage output is treated as unknown rather than usable."""
    assert SQLclInstaller.parse_version("not sqlcl") is None


def test_apexlang_status_reports_missing_sqlcl(monkeypatch) -> None:
    """Missing SQLcl produces explicit install guidance."""
    installer = SQLclInstaller()
    monkeypatch.setattr(installer, "get_version", lambda: None)

    status = installer.apexlang_status()

    assert not status.installed
    assert not status.capable
    assert "install sqlcl" in status.message


def test_apexlang_status_rejects_old_sqlcl(monkeypatch) -> None:
    """SQLcl before 26.1.2 is not accepted for the local APEXlang workflow."""
    installer = SQLclInstaller()
    monkeypatch.setattr(installer, "get_version", lambda: "SQLcl: Release 26.1.1.0 Production")

    status = installer.apexlang_status()

    assert status.installed
    assert not status.capable
    assert status.version == "26.1.1.0"
    assert "26.1.2" in status.message


def test_apexlang_status_accepts_sqlcl_26_1_2(monkeypatch) -> None:
    """SQLcl 26.1.2+ satisfies the APEXlang capability gate."""
    installer = SQLclInstaller()
    monkeypatch.setattr(installer, "get_version", lambda: "SQLcl: Release 26.1.2.0 Production")

    status = installer.apexlang_status()

    assert status.installed
    assert status.capable
    assert installer.is_apexlang_capable()
