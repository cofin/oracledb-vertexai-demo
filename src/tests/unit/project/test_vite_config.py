# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin project-level Vite config defaults."""

from __future__ import annotations

from tests.support.paths import PROJECT_ROOT

VITE_CONFIG = PROJECT_ROOT / "vite.config.ts"


def test_vite_config_is_warning_only() -> None:
    source = VITE_CONFIG.read_text()

    assert 'logLevel: "warn"' in source
    assert "clearScreen: false" in source
