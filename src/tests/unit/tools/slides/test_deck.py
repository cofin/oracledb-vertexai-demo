# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for reading presentation dumps."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from tools.slides.deck import known_object_ids, load_deck, summarize_slides, title_shape_ids, utf16_len

if TYPE_CHECKING:
    from pathlib import Path


def test_summarize_slides_reads_title_skip_state_and_bridge(sample_deck: dict[str, Any]) -> None:
    """The title is the largest top-band text, notes are read, and skipped slides are flagged."""
    first, second = summarize_slides(sample_deck)

    assert first.title == "Vector Search and the Optimizer Rule"
    assert first.texts[0] == "Vector Search and the Optimizer Rule"
    assert first.has_bridge
    assert not first.skipped
    assert second.skipped
    assert not second.has_bridge


def test_title_placeholder_wins_over_larger_text(sample_deck: dict[str, Any]) -> None:
    """A TITLE placeholder is the title even when another top-band box uses a bigger font."""
    slide = sample_deck["slides"][0]
    slide["pageElements"][2]["shape"]["placeholder"] = {"type": "TITLE"}

    assert title_shape_ids(slide) == {"subtitle_one"}


def test_known_object_ids_cover_notes_layouts_and_masters(sample_deck: dict[str, Any]) -> None:
    """Every page and element id a batch may reference is collected."""
    ids = known_object_ids(sample_deck)

    assert {"slide_one", "title_one", "notes_one", "notes_body_one", "layout_title", "master_one"} <= ids


def test_utf16_len_counts_characters_outside_the_basic_plane_twice() -> None:
    """Emoji cost two UTF-16 code units, matching Slides text indexes."""
    assert utf16_len("🟡AB") == 4
    assert utf16_len("café") == 4


def test_load_deck_rejects_files_without_slides(tmp_path: Path) -> None:
    """A JSON file that is not a presentation dump is rejected with a clear message."""
    path = tmp_path / "not-a-deck.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="not a presentation dump"):
        load_deck(path)
