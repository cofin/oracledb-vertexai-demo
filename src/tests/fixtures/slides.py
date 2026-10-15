# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Shared presentation-dump fixtures for the offline slide tooling tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path

EMU_PER_PT = 12700


@pytest.fixture
def sample_deck() -> dict[str, Any]:
    """Two slides: a content slide with title, badge, subtitle, code box, and notes; plus a skipped backup."""
    return {
        "presentationId": "sample-deck",
        "slides": [
            {
                "objectId": "slide_one",
                "pageElements": [
                    _text_box(
                        "title_one", "Vector Search and the Optimizer Rule\n", top_pt=10, width_pt=568, font_pt=18
                    ),
                    _text_box("badge_one", "Part 3\n", top_pt=14, width_pt=110, font_pt=9),
                    _text_box("subtitle_one", "FETCH APPROX or a full scan\n", top_pt=40, width_pt=568, font_pt=11),
                    _text_box("code_one", "SELECT 1 FROM dual\n", top_pt=102, width_pt=346, font_pt=8.5),
                ],
                "slideProperties": {
                    "notesPage": {
                        "objectId": "notes_one",
                        "notesProperties": {"speakerNotesObjectId": "notes_body_one"},
                        "pageElements": [
                            _text_box(
                                "notes_body_one",
                                "Explain the plan change.\nBRIDGE: Next, exact words.\n",
                                top_pt=400,
                                width_pt=500,
                                font_pt=12,
                            )
                        ],
                    }
                },
            },
            {
                "objectId": "slide_two",
                "pageElements": [_text_box("title_two", "HNSW Sizing\n", top_pt=10, width_pt=568, font_pt=18)],
                "slideProperties": {
                    "isSkipped": True,
                    "notesPage": {
                        "objectId": "notes_two",
                        "notesProperties": {"speakerNotesObjectId": "notes_body_two"},
                        "pageElements": [],
                    },
                },
            },
        ],
        "layouts": [{"objectId": "layout_title", "pageElements": []}],
        "masters": [{"objectId": "master_one", "pageElements": []}],
    }


@pytest.fixture
def deck_file(tmp_path: Path, sample_deck: dict[str, Any]) -> Path:
    """Write the sample deck to a JSON dump file."""
    path = tmp_path / "deck.json"
    path.write_text(json.dumps(sample_deck), encoding="utf-8")
    return path


def _text_box(object_id: str, text: str, *, top_pt: float, width_pt: float, font_pt: float) -> dict[str, Any]:
    """Build a text-box page element shaped like a Slides API dump entry."""
    return {
        "objectId": object_id,
        "size": {
            "width": {"magnitude": width_pt * EMU_PER_PT, "unit": "EMU"},
            "height": {"magnitude": 30 * EMU_PER_PT, "unit": "EMU"},
        },
        "transform": {
            "scaleX": 1,
            "scaleY": 1,
            "translateX": 18 * EMU_PER_PT,
            "translateY": top_pt * EMU_PER_PT,
            "unit": "EMU",
        },
        "shape": {
            "shapeType": "TEXT_BOX",
            "text": {
                "textElements": [
                    {"paragraphMarker": {"style": {}}},
                    {"textRun": {"content": text, "style": {"fontSize": {"magnitude": font_pt, "unit": "PT"}}}},
                ]
            },
        },
    }
