# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the repository-wide tools/ci/check_code_hygiene.py gate."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools.ci.check_code_hygiene import ROOT_DIR, TOOLS_DIR, check_ast_rules, check_inline_comments, main


def test_code_hygiene_main_passes_across_repository(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify check_code_hygiene.main scans src/app, tools, and manage.py cleanly."""
    exit_code = main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Code hygiene OK" in captured.out
    assert not captured.err
    assert (TOOLS_DIR / "bundler.py").exists()
    assert (TOOLS_DIR / "oracle" / "adb.py").exists()


def test_check_inline_comments_flags_prose_and_allows_directives(tmp_path: Path) -> None:
    """Verify check_inline_comments rejects prose comments while permitting directives."""
    sample = tmp_path / "sample.py"
    sample.write_text(
        "# SPDX-FileCopyrightText: 2026 Google LLC\n"
        "# SPDX-License-Identifier: Apache-2.0\n"
        '"""Sample module."""\n\n'
        "VALUE = 1  # ruff: ignore[magic-value-comparison]\n"
        "BAD = 2  # explain what BAD is\n",
        encoding="utf-8",
    )

    errors = check_inline_comments([sample])

    assert len(errors) == 1
    assert "sample.py:6: disallowed inline comment" in errors[0]


def test_check_ast_rules_flags_nested_imports_ordering_future_ioc_and_controllers(tmp_path: Path) -> None:
    """Verify check_ast_rules catches nested imports, ordering, ioc annotations, and raw controllers."""
    nested_and_order = tmp_path / "module_order.py"
    nested_and_order.write_text(
        '"""Module ordering fixture."""\n\n'
        "def _helper() -> int:\n"
        "    return 1\n\n"
        "def public_fn() -> str:\n"
        "    import json\n"
        "    return json.dumps({'ok': _helper()})\n",
        encoding="utf-8",
    )

    ioc_file = tmp_path / "src" / "app" / "ioc" / "_fake_provider.py"
    ioc_file.parent.mkdir(parents=True)
    ioc_file.write_text(
        '"""Fake Dishka provider."""\nfrom __future__ import annotations\n\nclass FakeProvider:\n    pass\n',
        encoding="utf-8",
    )

    controller_file = tmp_path / "controllers" / "_bad_controller.py"
    controller_file.parent.mkdir(parents=True)
    controller_file.write_text(
        '"""Unsecured controller fixture."""\n\nclass BareController:\n    pass\n', encoding="utf-8"
    )

    errors = check_ast_rules([nested_and_order, ioc_file, controller_file])

    assert any("function-scoped import inside 'public_fn'" in err for err in errors)
    assert any("public symbol 'public_fn' defined after private helper" in err for err in errors)
    assert any("Dishka provider modules in src/app/ioc/ must not use" in err for err in errors)
    assert any("controller 'BareController' must inherit from" in err for err in errors)


def test_makefile_start_infra_and_apex_targets_use_adb_free_workflow() -> None:
    """Verify Makefile start-infra and apex targets avoid destructive legacy flags."""
    makefile_text = (ROOT_DIR / "Makefile").read_text(encoding="utf-8")

    assert "--skip-apex" not in makefile_text
    assert "--skip-ords" not in makefile_text
    assert "uv run python manage.py infra start\n" in makefile_text
    assert "uv run python manage.py infra apex status" in makefile_text
