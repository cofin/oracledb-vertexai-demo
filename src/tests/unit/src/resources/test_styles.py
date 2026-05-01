# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Shared frontend style contract checks."""

from tests.support.paths import RESOURCES_ROOT


def test_shared_cymbal_ui_primitives_are_defined() -> None:
    source = (RESOURCES_ROOT / "styles.css").read_text()

    for selector in (
        ".app-shell",
        ".app-header",
        ".ui-panel",
        ".metric-card",
        ".telemetry-chip",
        ".icon-button",
        ".chart-host",
        ".popover-surface",
    ):
        assert selector in source
