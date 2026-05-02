# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from tests.support.paths import TESTS_ROOT

ROOT = TESTS_ROOT
ALLOWED_TOP_LEVEL = frozenset({"__init__.py", "conftest.py"})


def test_tests_use_only_unit_and_integration_behavior_buckets() -> None:
    buckets = {path.name for path in ROOT.iterdir() if path.is_dir() and not path.name.startswith("__")}

    assert "api" not in buckets
    assert {"unit", "integration"} <= buckets


def test_no_direct_top_level_test_files_in_behavior_buckets() -> None:
    offenders = [
        path.as_posix()
        for bucket in (ROOT / "unit", ROOT / "integration")
        for path in bucket.glob("test_*.py")
    ]

    assert offenders == []


def test_suite_infrastructure_files_stay_out_of_behavior_buckets() -> None:
    offenders = [
        path.as_posix()
        for path in ROOT.glob("test_*.py")
        if path.name not in ALLOWED_TOP_LEVEL
    ]

    assert offenders == []
