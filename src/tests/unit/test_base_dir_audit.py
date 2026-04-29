# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""BASE_DIR.parents audit — proves the Ch 4 source-tree flatten kept parents[N] sane.

Ch 4 Phase 1.1 collapsed `src/py/app/` to `src/app/`, which shifts every
``BASE_DIR.parents[N]`` accessor by one. Phase 1.6 rewrote the two affected
call sites; this test guards the layout going forward.
"""

from __future__ import annotations

from app.lib.settings import BASE_DIR


def test_base_dir_resolves_to_src_app() -> None:
    assert BASE_DIR.name == "app"
    assert BASE_DIR.parent.name == "src"


def test_base_dir_parents_one_is_repo_root() -> None:
    repo_root = BASE_DIR.parents[1]
    assert (repo_root / "pyproject.toml").is_file(), f"parents[1] should be repo root, got {repo_root}"
    assert (repo_root / "manage.py").is_file()


def test_legacy_src_py_layout_is_gone() -> None:
    repo_root = BASE_DIR.parents[1]
    assert not (repo_root / "src" / "py").exists()


def test_favicon_path_resolves() -> None:
    repo_root = BASE_DIR.parents[1]
    assert (repo_root / "src" / "resources" / "public" / "favicon.ico").is_file()
