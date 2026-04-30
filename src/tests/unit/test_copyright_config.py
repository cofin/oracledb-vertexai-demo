# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin Ruff CPY001 + SPDX header configuration."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
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
