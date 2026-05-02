# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for repository license header automation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools import license_headers

from tests.support.paths import PROJECT_ROOT

if TYPE_CHECKING:
    from pathlib import Path


def test_hash_header_inserted_after_shebang(tmp_path: Path) -> None:
    target = tmp_path / "demo.py"
    target.write_text("#!/usr/bin/env python\nprint('ok')\n")

    result = license_headers.ensure_header(target, fix=True)

    assert result.changed
    assert target.read_text() == (
        "#!/usr/bin/env python\n"
        "# Copyright 2026 Google LLC\n"
        "# SPDX-License-Identifier: Apache-2.0\n"
        "\n"
        "print('ok')\n"
    )


def test_dockerfile_header_keeps_parser_directive_first(tmp_path: Path) -> None:
    target = tmp_path / "Dockerfile"
    target.write_text("# syntax=docker/dockerfile:1.7\nFROM python:3.12\n")

    result = license_headers.ensure_header(target, fix=True)

    assert result.changed
    assert target.read_text() == (
        "# syntax=docker/dockerfile:1.7\n"
        "# Copyright 2026 Google LLC\n"
        "# SPDX-License-Identifier: Apache-2.0\n"
        "\n"
        "FROM python:3.12\n"
    )


def test_jinja_header_uses_jinja_comment(tmp_path: Path) -> None:
    target = tmp_path / "template.html.j2"
    target.write_text("<p>{{ message }}</p>\n")

    result = license_headers.ensure_header(target, fix=True)

    assert result.changed
    assert target.read_text().startswith(
        "{#\nCopyright 2026 Google LLC\nSPDX-License-Identifier: Apache-2.0\n#}\n\n"
    )


def test_css_header_uses_block_comment(tmp_path: Path) -> None:
    target = tmp_path / "styles.css"
    target.write_text("body { color: black; }\n")

    result = license_headers.ensure_header(target, fix=True)

    assert result.changed
    assert target.read_text().startswith(
        "/*\n * Copyright 2026 Google LLC\n * SPDX-License-Identifier: Apache-2.0\n */\n\n"
    )


def test_generated_resource_is_skipped(tmp_path: Path) -> None:
    target = tmp_path / "src" / "resources" / "generated" / "static-props.ts"
    target.parent.mkdir(parents=True)
    target.write_text("export const value = 1\n")

    result = license_headers.ensure_header(target, fix=True)

    assert not result.supported
    assert not result.changed
    assert target.read_text() == "export const value = 1\n"


def test_pre_commit_runs_license_headers_before_ruff() -> None:
    config = (PROJECT_ROOT / ".pre-commit-config.yaml").read_text()

    license_hook = config.index("id: license-headers")
    ruff_hook = config.index("id: ruff")

    assert license_hook < ruff_hook
    assert "tools/license_headers.py --fix" in config
    assert "src/js" not in config
