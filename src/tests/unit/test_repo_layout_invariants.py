"""Repo-layout invariants enforced by Ch 4 Phase 1A (source-tree flatten).

Phase 1.1 collapsed ``src/py/{app,tests}`` to ``src/{app,tests}`` and removed
all bun/biome/src-js toolchain references from Makefile/pyproject. These tests
prevent regressions: any future commit that re-introduces ``src/py``,
``src/js``, ``bun``, or ``biome`` to the build/test plumbing fails CI here.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from typing import TYPE_CHECKING

import pytest

from app.lib.settings import BASE_DIR

if TYPE_CHECKING:
    from pathlib import Path

REPO_ROOT: Path = BASE_DIR.parents[1]


def _read_makefile() -> str:
    return (REPO_ROOT / "Makefile").read_text(encoding="utf-8")


def _read_pyproject() -> dict[str, object]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def test_pyproject_packages_resolve_to_existing_dirs() -> None:
    """`packages = [...]` entries in pyproject must point at real directories."""
    pyproject = _read_pyproject()
    hatch = pyproject["tool"]["hatch"]["build"]
    sdist_pkgs = pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["packages"]
    wheel_pkgs = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    dev_dirs = hatch["dev-mode-dirs"]

    for entry in (*sdist_pkgs, *wheel_pkgs):
        assert (REPO_ROOT / entry).is_dir(), f"hatch package path missing: {entry}"
    for entry in dev_dirs:
        if entry == ".":
            continue
        assert (REPO_ROOT / entry).is_dir(), f"hatch dev-mode-dir missing: {entry}"


def test_pyproject_pytest_paths_resolve() -> None:
    """`testpaths` and `pythonpath` must point at the post-flatten dirs."""
    pyproject = _read_pyproject()
    pytest_cfg = pyproject["tool"]["pytest"]["ini_options"]
    for entry in (*pytest_cfg["testpaths"], *pytest_cfg["pythonpath"]):
        assert (REPO_ROOT / entry).is_dir(), f"pytest path missing: {entry}"


def test_pyproject_has_no_legacy_src_py_references() -> None:
    raw = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    legacy = re.findall(r'"src/py[/"]', raw)
    assert not legacy, f"pyproject.toml still references src/py: {legacy}"


def test_pyproject_has_no_src_js_references() -> None:
    raw = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    legacy = re.findall(r'"src/js[/"]', raw)
    assert not legacy, f"pyproject.toml still references src/js: {legacy}"


def test_makefile_has_no_legacy_path_references() -> None:
    body = _read_makefile()
    for needle in ("src/py", "src/js"):
        assert needle not in body, f"Makefile still mentions {needle!r}"


def test_makefile_has_no_bun_or_biome() -> None:
    body = _read_makefile()
    # Allow `bun` if it ever appears inside a comment line; check token boundaries.
    for needle in ("bun ", "bun\t", "bunx", "biome", "install-bun"):
        assert needle not in body, f"Makefile still mentions {needle!r}"


def test_legacy_src_py_directory_is_gone() -> None:
    assert not (REPO_ROOT / "src" / "py").exists(), (
        "src/py/ must not exist after Ch 4 Phase 1.1 — re-run `rm -rf src/py` if pycache regenerated"
    )


def test_src_layout_has_app_and_tests_at_top_level() -> None:
    src = REPO_ROOT / "src"
    assert (src / "app").is_dir()
    assert (src / "tests").is_dir()


def test_manage_py_help_runs_without_error() -> None:
    """Phase 1.5: manage.py sys.path was bumped to src/. --help must still work."""
    result = subprocess.run(  # noqa: S603 — fixed argv, no shell, executing the project's own manage.py.
        [sys.executable, str(REPO_ROOT / "manage.py"), "--help"],
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=30,
        check=False,
        text=True,
    )
    assert result.returncode == 0, f"manage.py --help failed: stderr={result.stderr!r}"
    # Sanity-check the help output exposes the expected top-level groups.
    for cmd in ("init", "install", "doctor", "infra", "database", "assets"):
        assert cmd in result.stdout, f"manage.py --help missing command {cmd!r}: {result.stdout}"


@pytest.mark.parametrize("subcommand", ["database", "assets"])
def test_manage_py_subgroup_help_runs(subcommand: str) -> None:
    """database/assets sub-groups must render their help (validates lazy imports work)."""
    result = subprocess.run(  # noqa: S603 — fixed argv, no shell, executing the project's own manage.py.
        [sys.executable, str(REPO_ROOT / "manage.py"), subcommand, "--help"],
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=30,
        check=False,
        text=True,
    )
    assert result.returncode == 0, f"manage.py {subcommand} --help failed: stderr={result.stderr!r}"
