# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Validate Slides ``batchUpdate`` requests against a presentation dump before applying them.

The checks catch the mistakes that otherwise surface as a failed batch or a
silently broken slide: references to objects that do not exist (or that the
batch deletes or creates later), titles longer than the deck allows, text
ranges past the end of a shape, and ``duplicateObject`` calls without an
explicit objectId map.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tools.slides.deck import known_object_ids, shape_text_lengths, title_shape_ids

__all__ = ["CREATE_REQUESTS", "DEFAULT_MAX_TITLE_CHARS", "RANGE_REQUESTS", "ValidationIssue", "validate_requests"]

DEFAULT_MAX_TITLE_CHARS = 48
CREATE_REQUESTS = frozenset({
    "createImage",
    "createLine",
    "createShape",
    "createSheetsChart",
    "createSlide",
    "createTable",
    "createVideo",
})
RANGE_REQUESTS = frozenset({
    "createParagraphBullets",
    "deleteParagraphBullets",
    "deleteText",
    "updateParagraphStyle",
    "updateTextStyle",
})


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One problem found in a batch.

    Attributes:
        severity: ``error`` blocks applying the batch; ``warning`` is advisory.
        index: Zero-based position of the request in the batch.
        message: Human-readable description of the problem.
    """

    severity: str
    index: int
    message: str


def validate_requests(
    requests: list[dict[str, Any]], deck: dict[str, Any], *, max_title_chars: int = DEFAULT_MAX_TITLE_CHARS
) -> list[ValidationIssue]:
    """Check a batch against a fresh presentation dump.

    Args:
        requests: ``batchUpdate`` requests in the order they will be sent.
        deck: Presentation dump taken right before the batch is applied.
        max_title_chars: Maximum length of the first line of a title.

    Returns:
        Issues ordered by request position; an empty list means the batch passed.
    """
    state = _BatchState.from_deck(deck)
    issues: list[ValidationIssue] = []
    for index, request in enumerate(requests):
        issues.extend(state.check(index, request, max_title_chars))
    return issues


@dataclass
class _BatchState:
    """Running view of the deck while a batch is checked request by request."""

    known: set[str]
    slides: set[str]
    titles: set[str]
    lengths: dict[str, int]
    deleted: set[str] = field(default_factory=set)
    edited: set[str] = field(default_factory=set)
    text_replaced: bool = False

    @classmethod
    def from_deck(cls, deck: dict[str, Any]) -> _BatchState:
        """Build the starting state from a presentation dump."""
        slides = [slide for slide in deck.get("slides", []) if slide.get("objectId")]
        titles: set[str] = set()
        for slide in slides:
            titles.update(title_shape_ids(slide))
        return cls(
            known=known_object_ids(deck),
            slides={slide["objectId"] for slide in slides},
            titles=titles,
            lengths=shape_text_lengths(deck),
        )

    def check(self, index: int, request: Any, max_title_chars: int) -> list[ValidationIssue]:
        """Check one request, then record its effect on the running state."""
        if not isinstance(request, dict) or len(request) != 1:
            return [ValidationIssue("error", index, "each request must be an object with exactly one request type")]
        kind, body = next(iter(request.items()))
        if not isinstance(body, dict):
            return [ValidationIssue("error", index, f"{kind} body must be an object")]
        issues = [ValidationIssue("error", index, message) for message in self._reference_errors(kind, body)]
        issues.extend(self._content_issues(index, kind, body, max_title_chars))
        self._apply(kind, body)
        return issues

    def _reference_errors(self, kind: str, body: dict[str, Any]) -> list[str]:
        """Return errors for objectIds the request uses but the deck does not have."""
        errors: list[str] = []
        for object_id in _referenced_ids(kind, body):
            if object_id in self.deleted:
                errors.append(f"{kind} uses {object_id!r}, which an earlier request deletes")
            elif object_id not in self.known:
                errors.append(f"{kind} uses unknown objectId {object_id!r} (not in the dump or created earlier)")
        new_id = body.get("objectId") if kind in CREATE_REQUESTS else None
        if new_id and new_id in self.known and new_id not in self.deleted:
            errors.append(f"{kind} creates {new_id!r}, which already exists")
        return errors

    def _content_issues(
        self, index: int, kind: str, body: dict[str, Any], max_title_chars: int
    ) -> list[ValidationIssue]:
        """Return title, range, position, and duplicate-map issues for one request."""
        issues: list[ValidationIssue] = []
        if kind == "insertText" and body.get("objectId") in self.titles:
            issues.extend(_title_issues(index, str(body.get("text", "")), max_title_chars))
        if kind == "duplicateObject" and not body.get("objectIds"):
            issues.append(
                ValidationIssue(
                    "warning",
                    index,
                    "duplicateObject without objectIds: later requests cannot target the copied elements reliably",
                )
            )
        if kind in RANGE_REQUESTS:
            issues.extend(self._range_issues(index, body))
        position = body.get("insertionIndex")
        is_position_request = kind in {"createSlide", "updateSlidesPosition"}
        if is_position_request and isinstance(position, int) and not 0 <= position <= len(self.slides):
            issues.append(
                ValidationIssue("error", index, f"insertionIndex {position} is outside 0..{len(self.slides)}")
            )
        return issues

    def _range_issues(self, index: int, body: dict[str, Any]) -> list[ValidationIssue]:
        """Return errors for malformed text ranges or ranges past the end of unedited text."""
        text_range = body.get("textRange", {})
        if text_range.get("type") != "FIXED_RANGE":
            return []
        start, end = text_range.get("startIndex"), text_range.get("endIndex")
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            return [
                ValidationIssue("error", index, f"FIXED_RANGE needs 0 <= startIndex < endIndex, got {start}..{end}")
            ]
        object_id = body.get("objectId", "")
        length = self.lengths.get(object_id)
        unchanged = object_id not in self.edited and not self.text_replaced
        if unchanged and length is not None and end > length:
            return [
                ValidationIssue("error", index, f"range end {end} is past the text length {length} of {object_id!r}")
            ]
        return []

    def _apply(self, kind: str, body: dict[str, Any]) -> None:
        """Record the effect of a request on the running state."""
        if kind in CREATE_REQUESTS:
            self._register_created(kind, body)
        elif kind == "duplicateObject":
            self._register_duplicate(body)
        elif kind == "deleteObject":
            object_id = body.get("objectId", "")
            self.deleted.add(object_id)
            self.slides.discard(object_id)
        elif kind in {"insertText", "deleteText"}:
            self.edited.add(body.get("objectId", ""))
        elif kind == "replaceAllText":
            self.text_replaced = True

    def _register_created(self, kind: str, body: dict[str, Any]) -> None:
        """Track objectIds introduced by a create request."""
        new_id = body.get("objectId")
        if new_id:
            self.known.add(new_id)
            self.deleted.discard(new_id)
            if kind == "createSlide":
                self.slides.add(new_id)
        for mapping in body.get("placeholderIdMappings", []):
            mapped = mapping.get("objectId")
            if mapped:
                self.known.add(mapped)

    def _register_duplicate(self, body: dict[str, Any]) -> None:
        """Track objectIds introduced by duplicateObject, carrying slide and title roles over."""
        for original, copy in body.get("objectIds", {}).items():
            self.known.add(copy)
            if original in self.titles:
                self.titles.add(copy)
            if original in self.slides:
                self.slides.add(copy)
            if original in self.lengths:
                self.lengths[copy] = self.lengths[original]


def _referenced_ids(kind: str, body: dict[str, Any]) -> list[str]:
    """Return the existing objectIds a request refers to."""
    referenced: list[str] = []
    if kind not in CREATE_REQUESTS and isinstance(body.get("objectId"), str):
        referenced.append(body["objectId"])
    page_id = body.get("elementProperties", {}).get("pageObjectId")
    if isinstance(page_id, str):
        referenced.append(page_id)
    layout_id = body.get("slideLayoutReference", {}).get("layoutId")
    if isinstance(layout_id, str):
        referenced.append(layout_id)
    for key in ("slideObjectIds", "pageObjectIds", "childrenObjectIds", "pageElementObjectIds"):
        referenced.extend(value for value in body.get(key, []) if isinstance(value, str))
    if kind == "replaceImage" and isinstance(body.get("imageObjectId"), str):
        referenced.append(body["imageObjectId"])
    return referenced


def _title_issues(index: int, text: str, max_title_chars: int) -> list[ValidationIssue]:
    """Return length and single-line issues for text inserted into a title."""
    lines = [line for line in text.splitlines() if line.strip()]
    first = lines[0] if lines else ""
    issues: list[ValidationIssue] = []
    if len(first) > max_title_chars:
        issues.append(
            ValidationIssue(
                "error", index, f"title is {len(first)} characters; keep titles at or under {max_title_chars}"
            )
        )
    if len(lines) > 1:
        issues.append(ValidationIssue("warning", index, "title text spans more than one line"))
    return issues
