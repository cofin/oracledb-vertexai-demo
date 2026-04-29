"""Brand-asset preservation invariants for Ch 4 Phase 2.

Phase 2 of the htmx-vite-frontend chapter (`oracledb-vertexai-4d6.4.10`)
rescues 23 brand assets from ``src/js/public/`` to ``src/resources/public/``
via ``git mv`` (history preserved), then deletes ``src/js`` wholesale.

These tests pin the *post-move* layout: the brand asset directory must exist
under the new path with every legacy file present, and the legacy
``src/js/`` tree must be gone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.lib.settings import BASE_DIR

if TYPE_CHECKING:
    from pathlib import Path

REPO_ROOT: Path = BASE_DIR.parents[1]
RESCUED_PUBLIC: Path = REPO_ROOT / "src" / "resources" / "public"


# Locked from `git ls-files src/js/public/` captured pre-move (Phase 2 task description: "23 SVG/icon assets").
LEGACY_BRAND_ASSETS: tuple[str, ...] = (
    "android-chrome-192x192.png",
    "android-chrome-512x512.png",
    "apple-touch-icon.png",
    "browserconfig.xml",
    "coffee.jpg",
    "cymbal-coffee-cup.svg",
    "cymbal-coffee-logo-dark.svg",
    "cymbal-coffee-logo-light.svg",
    "cymbal-coffee-logo.svg",
    "cymbal-coffee-text-dark.svg",
    "cymbal-coffee-text-light.svg",
    "cymbal-coffee-text.svg",
    "cymbal-orig.jpg",
    "favicon-16x16.png",
    "favicon-32x32.png",
    "favicon.ico",
    "mstile-144x144.png",
    "mstile-150x150.png",
    "mstile-310x150.png",
    "mstile-310x310.png",
    "mstile-70x70.png",
    "safari-pinned-tab.svg",
    "site.webmanifest",
)


def test_rescued_public_directory_exists() -> None:
    """The rescue target ``src/resources/public/`` must exist after Phase 2.1."""
    assert RESCUED_PUBLIC.is_dir(), f"missing rescue target: {RESCUED_PUBLIC}"


def test_rescued_public_contains_exactly_23_assets() -> None:
    """The 23 legacy assets are the entirety of the rescued tree."""
    found = sorted(p.name for p in RESCUED_PUBLIC.iterdir() if p.is_file())
    assert found == sorted(LEGACY_BRAND_ASSETS), (
        f"rescued public/ inventory drift: missing={set(LEGACY_BRAND_ASSETS) - set(found)} "
        f"extra={set(found) - set(LEGACY_BRAND_ASSETS)}"
    )


@pytest.mark.parametrize("asset", LEGACY_BRAND_ASSETS)
def test_each_brand_asset_present(asset: str) -> None:
    """Every legacy asset must land under ``src/resources/public/``.

    Parametrized so a single missing logo surfaces a precise failure rather
    than a single inventory diff.
    """
    assert (RESCUED_PUBLIC / asset).is_file(), f"missing rescued asset: {asset}"


def test_favicon_ico_is_nonempty() -> None:
    """The 16x16/32x32 multi-icon ``favicon.ico`` must be byte-equivalent (i.e. > 0 bytes)."""
    favicon = RESCUED_PUBLIC / "favicon.ico"
    assert favicon.is_file(), "favicon.ico missing from rescued public/"
    assert favicon.stat().st_size > 0, "favicon.ico is empty after rescue"


def test_legacy_src_js_directory_is_gone() -> None:
    """``src/js`` must be wholly removed after Phase 2.2 (`git rm -r src/js`)."""
    legacy = REPO_ROOT / "src" / "js"
    assert not legacy.exists(), (
        f"src/js/ must not exist after Phase 2.2 — found: {legacy}. "
        "If only __pycache__ regenerated, run `rm -rf src/js`."
    )


def test_legacy_src_js_public_directory_is_gone() -> None:
    """The original ``src/js/public/`` is gone (assets were moved, not copied)."""
    legacy = REPO_ROOT / "src" / "js" / "public"
    assert not legacy.exists(), f"legacy src/js/public/ still present: {legacy}"
