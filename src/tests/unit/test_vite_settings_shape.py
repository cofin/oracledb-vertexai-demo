# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Phase 4.2 contract: ``ViteSettings.get_config()`` must return a template-mode
config that uses Node executor and points at the new ``src/resources`` /
``domain/web/static/dist`` paths.
"""

from __future__ import annotations

from pathlib import Path

from app.lib.settings import BASE_DIR, ViteSettings


def test_vite_config_mode_is_template() -> None:
    cfg = ViteSettings().get_config()
    assert cfg.mode == "template", f"Phase 4 flipped mode from 'spa' to 'template'; got {cfg.mode!r}"


def test_vite_config_runtime_executor_is_node() -> None:
    cfg = ViteSettings().get_config()
    assert cfg.runtime is not None
    assert cfg.runtime.executor == "node", (
        f"Phase 4 flipped executor from 'bun' to 'node'; got {cfg.runtime.executor!r}"
    )


def test_vite_config_resource_dir_is_src_resources() -> None:
    cfg = ViteSettings().get_config()
    assert cfg.paths is not None
    assert cfg.paths.resource_dir == Path("src/resources"), (
        f"resource_dir must point at src/resources; got {cfg.paths.resource_dir!r}"
    )


def test_vite_config_root_is_repo_root() -> None:
    cfg = ViteSettings().get_config()
    assert cfg.paths is not None
    assert cfg.paths.root == BASE_DIR.parents[1], (
        f"paths.root must be repo root (BASE_DIR.parents[1]); got {cfg.paths.root!r}"
    )


def test_vite_config_typegen_is_all_off() -> None:
    cfg = ViteSettings().get_config()
    assert cfg.types is not None
    assert cfg.types.generate_sdk is False
    assert cfg.types.generate_routes is False
    assert cfg.types.generate_schemas is False
    assert cfg.types.generate_page_props is False


def test_vite_settings_bundle_dir_default_is_domain_web() -> None:
    bundle_dir = ViteSettings().BUNDLE_DIR
    assert bundle_dir == BASE_DIR / "domain" / "web" / "static" / "dist", (
        f"Phase 4 retargets BUNDLE_DIR from server/static/dist to domain/web/static/dist; got {bundle_dir!r}"
    )
