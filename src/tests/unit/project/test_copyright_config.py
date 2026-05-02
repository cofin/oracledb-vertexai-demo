# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin Ruff CPY001 + SPDX header configuration."""

from __future__ import annotations

import re
import tomllib

import pytest

from tests.support.paths import PROJECT_ROOT

PYPROJECT = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
RUFF_LINT = PYPROJECT["tool"]["ruff"]["lint"]
COPYRIGHT_CFG = RUFF_LINT.get("flake8-copyright", {})


def test_copyright_author_is_google_llc() -> None:
    assert COPYRIGHT_CFG.get("author") == "Google LLC"


def test_cpy001_not_ignored() -> None:
    assert "CPY001" not in RUFF_LINT.get("ignore", [])


def test_notice_rgx_configured() -> None:
    assert "notice-rgx" in COPYRIGHT_CFG, (
        "notice-rgx must be set so both traditional 'Copyright YYYY' and SPDX "
        "'SPDX-FileCopyrightText: YYYY' headers are accepted."
    )


@pytest.mark.parametrize(
    "header",
    [
        "Copyright 2026 Google LLC",
        "Copyright 2024-2026 Google LLC",
        "Copyright (C) 2026 Google LLC",
        "SPDX-FileCopyrightText: 2026 Google LLC",
        "SPDX-FileCopyrightText: Copyright 2026 Google LLC",
    ],
)
def test_notice_rgx_accepts_supported_formats(header: str) -> None:
    pattern = COPYRIGHT_CFG["notice-rgx"]
    assert re.search(pattern, header), f"notice-rgx should match: {header!r}"


@pytest.mark.parametrize(
    "header",
    [
        "All rights reserved.",
        "(c) Some Other Company",
        "License: MIT",
    ],
)
def test_notice_rgx_rejects_unsupported_formats(header: str) -> None:
    pattern = COPYRIGHT_CFG["notice-rgx"]
    assert not re.search(pattern, header), f"notice-rgx should NOT match: {header!r}"


def test_every_python_source_file_has_valid_copyright_header() -> None:
    pattern = re.compile(COPYRIGHT_CFG["notice-rgx"])
    failures: list[str] = []
    for py in (PROJECT_ROOT / "src").rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        head = "".join(py.read_text().splitlines(keepends=True)[:5])
        if not pattern.search(head):
            failures.append(str(py.relative_to(PROJECT_ROOT)))
    assert not failures, "Python files missing valid copyright header:\n" + "\n".join(failures)


SPDX_PREFIX = "SPDX-FileCopyrightText:"


def _spdx_failures(root: str, suffixes: tuple[str, ...]) -> list[str]:
    failures: list[str] = []
    base = PROJECT_ROOT / root
    if not base.exists():
        return failures
    for path in base.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if "__pycache__" in path.parts or ".venv" in path.parts:
            continue
        head = "".join(path.read_text().splitlines(keepends=True)[:5])
        if SPDX_PREFIX not in head:
            failures.append(str(path.relative_to(PROJECT_ROOT)))
    return failures


def test_src_python_uses_spdx_filecopyrighttext() -> None:
    failures = _spdx_failures("src", (".py",))
    assert not failures, (
        "src/ Python files must use SPDX-FileCopyrightText header:\n" + "\n".join(failures)
    )


def test_tools_python_uses_spdx_filecopyrighttext() -> None:
    failures = _spdx_failures("tools", (".py",))
    assert not failures, (
        "tools/ Python files must use SPDX-FileCopyrightText header:\n" + "\n".join(failures)
    )


def test_sql_files_use_spdx_filecopyrighttext() -> None:
    failures = _spdx_failures("src", (".sql",)) + _spdx_failures("tools", (".sql",))
    assert not failures, "SQL files must use SPDX-FileCopyrightText header:\n" + "\n".join(failures)


def test_patterns_doc_uses_spdx_filecopyrighttext_example() -> None:
    text = (PROJECT_ROOT / ".agents" / "patterns.md").read_text()
    assert "SPDX-FileCopyrightText" in text, (
        ".agents/patterns.md must show the canonical SPDX-FileCopyrightText form, "
        "not the legacy 'Copyright YYYY Google LLC' line."
    )


def test_python_styleguide_documents_license_tooling() -> None:
    text = (PROJECT_ROOT / ".agents" / "code-styleguides" / "python.md").read_text()
    assert "SPDX-FileCopyrightText" in text
    assert "CPY001" in text, "styleguide must reference the Ruff rule that enforces headers"
    assert "license_headers" in text, "styleguide must reference the prek auto-fix hook"
