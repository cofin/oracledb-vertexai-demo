# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for validating batchUpdate requests against a presentation dump."""

from __future__ import annotations

from typing import Any

from tools.slides.validate import validate_requests


def test_clean_batch_has_no_issues(sample_deck: dict[str, Any]) -> None:
    """Rewriting a title within the limit and unskipping a slide passes."""
    requests: list[dict[str, Any]] = [
        {"deleteText": {"objectId": "title_one", "textRange": {"type": "ALL"}}},
        {"insertText": {"objectId": "title_one", "insertionIndex": 0, "text": "Vector Search and the Optimizer"}},
        {
            "updateSlideProperties": {
                "objectId": "slide_two",
                "slideProperties": {"isSkipped": False},
                "fields": "isSkipped",
            }
        },
    ]

    assert validate_requests(requests, sample_deck) == []


def test_unknown_object_id_is_an_error(sample_deck: dict[str, Any]) -> None:
    """Requests that target ids missing from the dump fail validation."""
    issues = validate_requests([{"deleteObject": {"objectId": "missing_box"}}], sample_deck)

    assert [issue.severity for issue in issues] == ["error"]
    assert "missing_box" in issues[0].message


def test_object_created_earlier_in_the_batch_can_be_used(sample_deck: dict[str, Any]) -> None:
    """A shape created by an earlier request is a valid target for later requests."""
    requests: list[dict[str, Any]] = [
        {
            "createShape": {
                "objectId": "new_box",
                "shapeType": "TEXT_BOX",
                "elementProperties": {"pageObjectId": "slide_one"},
            }
        },
        {"insertText": {"objectId": "new_box", "text": "hello"}},
    ]

    assert validate_requests(requests, sample_deck) == []


def test_use_before_create_and_use_after_delete_are_errors(sample_deck: dict[str, Any]) -> None:
    """Ordering mistakes are reported on the request that makes them."""
    requests: list[dict[str, Any]] = [
        {"insertText": {"objectId": "later_box", "text": "too soon"}},
        {
            "createShape": {
                "objectId": "later_box",
                "shapeType": "TEXT_BOX",
                "elementProperties": {"pageObjectId": "slide_one"},
            }
        },
        {"deleteObject": {"objectId": "code_one"}},
        {
            "updateTextStyle": {
                "objectId": "code_one",
                "textRange": {"type": "ALL"},
                "style": {"bold": True},
                "fields": "bold",
            }
        },
    ]

    issues = validate_requests(requests, sample_deck)

    assert [(issue.index, issue.severity) for issue in issues] == [(0, "error"), (3, "error")]


def test_long_title_is_an_error(sample_deck: dict[str, Any]) -> None:
    """Titles longer than the limit are rejected."""
    text = "A slide title that runs well past forty-eight characters"

    issues = validate_requests([{"insertText": {"objectId": "title_one", "text": text}}], sample_deck)

    assert issues[0].severity == "error"
    assert "48" in issues[0].message


def test_duplicate_without_map_warns_and_mapped_titles_are_checked(sample_deck: dict[str, Any]) -> None:
    """A duplicate needs an objectIds map, and copied titles keep the length rule."""
    requests: list[dict[str, Any]] = [
        {"duplicateObject": {"objectId": "slide_one"}},
        {
            "duplicateObject": {
                "objectId": "slide_one",
                "objectIds": {"slide_one": "slide_copy", "title_one": "title_copy"},
            }
        },
        {"insertText": {"objectId": "title_copy", "text": "x" * 60}},
    ]

    issues = validate_requests(requests, sample_deck)

    assert [(issue.index, issue.severity) for issue in issues] == [(0, "warning"), (2, "error")]


def test_fixed_range_past_the_text_is_an_error(sample_deck: dict[str, Any]) -> None:
    """The code box holds 19 UTF-16 units, so a range ending at 40 is rejected."""
    requests: list[dict[str, Any]] = [
        {
            "updateTextStyle": {
                "objectId": "code_one",
                "textRange": {"type": "FIXED_RANGE", "startIndex": 0, "endIndex": 40},
                "style": {"bold": True},
                "fields": "bold",
            }
        }
    ]

    issues = validate_requests(requests, sample_deck)

    assert issues
    assert "past the text length" in issues[0].message


def test_slide_position_outside_the_deck_is_an_error(sample_deck: dict[str, Any]) -> None:
    """Moving a slide past the end of a two-slide deck fails."""
    requests: list[dict[str, Any]] = [{"updateSlidesPosition": {"slideObjectIds": ["slide_two"], "insertionIndex": 5}}]

    issues = validate_requests(requests, sample_deck)

    assert [issue.severity for issue in issues] == ["error"]
