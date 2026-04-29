# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Repo-root layout invariants for Ch 4 Phase 3.

Phase 3 (`oracledb-vertexai-4d6.4.11`) places ``package.json``,
``vite.config.ts``, and ``tsconfig.json`` at the repo root (replacing the
deleted ``src/js/`` toolchain), and emits the Vite bundle to
``src/app/domain/web/static/dist/`` (the new web-domain peer).

These tests pin that contract so future commits cannot silently drift back
into a nested ``src/js`` layout or move the bundle output elsewhere.

The build-output asserts (``package-lock.json`` + ``manifest.json``) are
deliberately strict — they fail if ``npm install`` or ``npm run build`` was
not run after a fresh checkout, which is the same signal CI needs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.lib.settings import BASE_DIR

if TYPE_CHECKING:
    from pathlib import Path

REPO_ROOT: Path = BASE_DIR.parents[1]
BUNDLE_DIR: Path = REPO_ROOT / "src" / "app" / "domain" / "web" / "static" / "dist"


def test_root_toolchain_files_exist() -> None:
    for name in ("package.json", "vite.config.ts", "tsconfig.json"):
        assert (REPO_ROOT / name).is_file(), f"{name} missing at repo root"


def test_legacy_src_js_directory_absent() -> None:
    """Belt-and-braces with ``test_repo_layout_invariants`` — owned here too so the
    Phase 3 contract is self-contained and a future split of test files can't
    drop the assertion accidentally.
    """
    assert not (REPO_ROOT / "src" / "js").exists()


def test_resources_scaffold_present() -> None:
    resources = REPO_ROOT / "src" / "resources"
    assert (resources / "main.js").is_file()
    assert (resources / "styles.css").is_file()
    assert (resources / "public").is_dir()


def test_npm_install_lockfile_exists() -> None:
    """``npm install`` writes ``package-lock.json`` at the same level as ``package.json``."""
    assert (REPO_ROOT / "package-lock.json").is_file(), (
        "package-lock.json missing — run `npm install` from the repo root"
    )


def test_vite_build_emits_manifest() -> None:
    """``npm run build`` (or ``manage.py assets build``) emits ``manifest.json``
    into the bundle dir matching the coupled contract.
    """
    assert BUNDLE_DIR.is_dir(), f"bundle dir missing: {BUNDLE_DIR}"
    assert (BUNDLE_DIR / "manifest.json").is_file(), (
        "manifest.json missing — run `npm run build` from the repo root"
    )
