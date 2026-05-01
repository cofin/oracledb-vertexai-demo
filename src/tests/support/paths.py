# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
APP_ROOT = SRC_ROOT / "app"
RESOURCES_ROOT = SRC_ROOT / "resources"
TESTS_ROOT = SRC_ROOT / "tests"
