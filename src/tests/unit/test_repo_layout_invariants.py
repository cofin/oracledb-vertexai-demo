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


# ---------------------------------------------------------------------------
# Ch 4 Phase 2 — .gitignore + layout invariants for the React frontend deletion
# ---------------------------------------------------------------------------


def _read_gitignore() -> str:
    return (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")


def test_gitignore_has_no_legacy_src_js_references() -> None:
    """Phase 2.3 must scrub all ``src/js/...`` patterns from .gitignore."""
    body = _read_gitignore()
    legacy = re.findall(r"^!?src/js/.*$", body, flags=re.MULTILINE)
    assert not legacy, f".gitignore still references src/js/: {legacy}"


def test_gitignore_has_no_legacy_src_py_references() -> None:
    """Phase 1A flatten leftover: ``!src/py/app/lib`` and ``src/py/app/...`` must be gone."""
    body = _read_gitignore()
    legacy = re.findall(r"^!?src/py/.*$", body, flags=re.MULTILINE)
    assert not legacy, f".gitignore still references src/py/: {legacy}"


def test_legacy_src_js_directory_is_gone() -> None:
    """Belt-and-braces with ``test_brand_assets_layout`` — owned by the layout-invariants suite."""
    assert not (REPO_ROOT / "src" / "js").exists(), "src/js/ must not exist after Ch 4 Phase 2.2"


def test_pyproject_has_no_src_js_references_after_phase_2() -> None:
    """Belt-and-braces — pyproject.toml must remain free of src/js paths."""
    raw = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "src/js" not in raw, "pyproject.toml still references src/js"


# ---------------------------------------------------------------------------
# Ch 4 Phase 6 — toolchain finalize invariants
# ---------------------------------------------------------------------------


def test_pyproject_has_no_litestar_htmx_direct_dep() -> None:
    """HTMX support comes from ``litestar.plugins.htmx`` (built-in 2.x), not a separate dep."""
    pyproject = _read_pyproject()
    deps = pyproject["project"]["dependencies"]
    for entry in deps:
        assert not entry.startswith("litestar-htmx"), (
            f"litestar-htmx is a separate package and must not be a direct dep: {entry}"
        )


def test_pyproject_has_no_bun_references() -> None:
    raw = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "bun" not in raw.lower(), "pyproject.toml still references bun"


def test_pyproject_wheel_artifacts_include_j2_templates() -> None:
    """Hatch wheel build must bundle Jinja2 templates so HTMX partials ship in the wheel."""
    pyproject = _read_pyproject()
    artifacts = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["artifacts"]
    assert "**/*.j2" in artifacts, f"wheel artifacts missing **/*.j2: {artifacts}"


def test_pyproject_wheel_packages_pin_src_app() -> None:
    pyproject = _read_pyproject()
    wheel_pkgs = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert wheel_pkgs == ["src/app"], f"wheel packages must be ['src/app']: {wheel_pkgs}"


def test_makefile_has_no_coffee_assets_or_upgrade_invocations() -> None:
    """Phase 1.8 made `coffee assets` and `coffee upgrade` unregistered subcommands.

    Architecture-enforced via ``test_cli_surface.py``; this guards the Makefile
    surface so a future commit cannot accidentally re-introduce the forbidden
    invocations.
    """
    body = _read_makefile()
    for needle in ("coffee assets", "coffee upgrade"):
        assert needle not in body, f"Makefile still invokes forbidden CLI: {needle!r}"


def test_makefile_clean_targets_new_bundle_dir() -> None:
    """Phase 6.2: ``make clean`` must scrub the new ``src/app/domain/web/static/dist``
    bundle dir, not the pre-flatten ``src/app/server/static/dist`` path.
    """
    body = _read_makefile()
    assert "src/app/server/static" not in body, (
        "Makefile still references legacy src/app/server/static — bundle dir is now src/app/domain/web/static"
    )


def test_makefile_lint_runs_frontend_typecheck() -> None:
    """Phase 6.2: ``make lint`` must invoke the frontend type-checker so CI catches TS regressions."""
    body = _read_makefile()
    lint_block = body.split(".PHONY: lint", 1)[1].split(".PHONY:", 1)[0]
    assert "tsc" in lint_block or "frontend-typecheck" in lint_block, (
        "make lint must run npx tsc --noEmit (directly or via frontend-typecheck)"
    )


def test_makefile_build_runs_frontend_assets_build() -> None:
    """Phase 6.2: ``make build`` must rebuild frontend assets alongside the wheel."""
    body = _read_makefile()
    build_block = body.split(".PHONY: build\nbuild:", 1)[1].split(".PHONY:", 1)[0]
    assert "assets build" in build_block or "npm run build" in build_block, (
        "make build must build frontend assets (via `manage.py assets build` or `npm run build`)"
    )


def test_gitignore_ignores_new_bundle_dir() -> None:
    """Phase 6.3: the Vite bundle dir lives under the web domain after the flatten."""
    body = _read_gitignore()
    assert "src/app/domain/web/static/dist" in body, (
        ".gitignore must ignore src/app/domain/web/static/dist (post-flatten bundle dir)"
    )


def test_gitignore_ignores_resources_generated() -> None:
    """Phase 6.3: type-gen output is ephemeral and rebuilt by `manage.py assets generate-types`."""
    body = _read_gitignore()
    assert "src/resources/generated" in body, ".gitignore must ignore src/resources/generated"


def test_gitignore_ignores_node_modules() -> None:
    body = _read_gitignore()
    assert "node_modules" in body, ".gitignore must ignore node_modules"


# ---------------------------------------------------------------------------
# Ch 4 Phase 6.4 — Dockerfile invariants
# ---------------------------------------------------------------------------

DOCKERFILES: tuple[str, ...] = (
    "tools/deploy/docker/run/Dockerfile",
    "tools/deploy/docker/run/Dockerfile.distroless",
)


@pytest.mark.parametrize("path", DOCKERFILES)
def test_dockerfile_has_no_bun_references(path: str) -> None:
    """Phase 6.4: Dockerfiles must not COPY oven/bun or run `bun install`/`bun run`."""
    body = (REPO_ROOT / path).read_text(encoding="utf-8")
    for needle in ("oven/bun", "bun install", "bun run", "bun.lock"):
        assert needle not in body, f"{path} still references bun: {needle!r}"


@pytest.mark.parametrize("path", DOCKERFILES)
def test_dockerfile_has_no_legacy_src_paths(path: str) -> None:
    """Phase 6.4: Dockerfiles must use ``src/`` (post-flatten), not ``src/py`` or ``src/js``."""
    body = (REPO_ROOT / path).read_text(encoding="utf-8")
    for needle in ("src/py/", "src/js/"):
        assert needle not in body, f"{path} still references pre-flatten path: {needle!r}"


@pytest.mark.parametrize("path", DOCKERFILES)
def test_dockerfile_uses_npm_ci(path: str) -> None:
    """Phase 6.4: Dockerfiles install JS deps via ``npm ci`` against root package-lock.json."""
    body = (REPO_ROOT / path).read_text(encoding="utf-8")
    assert "npm ci" in body, f"{path} must run `npm ci`"
    assert "package.json package-lock.json" in body or "package-lock.json" in body, (
        f"{path} must COPY root package-lock.json"
    )
