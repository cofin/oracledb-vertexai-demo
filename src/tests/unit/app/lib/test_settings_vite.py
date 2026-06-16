# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Vite frontend settings contract for litestar-vite template mode."""

from __future__ import annotations

from pathlib import Path


def test_vite_config_uses_resources_as_frontend_root() -> None:
    from app.lib.settings import BASE_DIR, ViteSettings

    config = ViteSettings().get_config()

    assert config.paths.root == BASE_DIR.parent / "resources"
    assert config.paths.resource_dir == Path()
    assert config.paths.static_dir == Path("public")
    assert config.types is not None
    assert config.types.output == BASE_DIR.parent / "resources" / "generated"
