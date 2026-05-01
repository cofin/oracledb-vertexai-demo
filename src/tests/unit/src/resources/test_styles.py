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


def test_app_title_text_can_wrap_on_small_screens() -> None:
    source = (RESOURCES_ROOT / "styles.css").read_text()

    assert ".app-title__subheading" in source
    assert "overflow-wrap: break-word" in source
    assert "min-width: 0" in source
    assert "@media (max-width: 47.999rem)" in source
    assert 'input[type="search"]' in source
    assert "width: calc(100vw - 4rem)" in source


def test_chat_surface_has_avatar_and_soft_bubble_rules() -> None:
    source = (RESOURCES_ROOT / "styles.css").read_text()

    assert ".message-row" in source
    assert ".chat-avatar" in source
    assert "border-radius: 0.875rem" in source
    assert "border-color: transparent" in source
