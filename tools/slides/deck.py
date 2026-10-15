# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Read Google Slides presentation dumps into compact slide summaries.

A dump is the presentation JSON returned by the Slides API
``presentations.get`` call. Every helper in this module works offline against
that structure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

__all__ = [
    "BRIDGE_PREFIX",
    "EMU_PER_PT",
    "TITLE_BAND_PT",
    "TITLE_PLACEHOLDER_TYPES",
    "SlideSummary",
    "iter_page_elements",
    "known_object_ids",
    "load_deck",
    "shape_text",
    "shape_text_lengths",
    "summarize_slides",
    "title_shape_ids",
    "utf16_len",
]

BRIDGE_PREFIX = "BRIDGE:"
EMU_PER_PT = 12700
TITLE_BAND_PT = 120.0
TITLE_PLACEHOLDER_TYPES = frozenset({"TITLE", "CENTERED_TITLE"})


@dataclass(frozen=True, slots=True)
class SlideSummary:
    """Compact view of one slide in a presentation dump.

    Attributes:
        index: One-based slide position in the deck.
        object_id: Slide page ``objectId``.
        skipped: Whether the slide is skipped in presentation mode.
        title: First line of the detected title shape, or an empty string.
        texts: Text of every text-bearing element in reading order.
        notes: Speaker notes text.
    """

    index: int
    object_id: str
    skipped: bool
    title: str
    texts: tuple[str, ...]
    notes: str

    @property
    def has_bridge(self) -> bool:
        """Whether the speaker notes end with a ``BRIDGE:`` hand-off line."""
        lines = [line.strip() for line in self.notes.splitlines() if line.strip()]
        return bool(lines) and lines[-1].startswith(BRIDGE_PREFIX)


def load_deck(path: Path) -> dict[str, Any]:
    """Load a presentation dump and confirm it contains a ``slides`` array.

    Args:
        path: Path to the presentation JSON dump.

    Returns:
        The parsed presentation object.

    Raises:
        ValueError: If the file does not contain a presentation object.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("slides"), list):
        msg = f"{path} is not a presentation dump: expected an object with a 'slides' array"
        raise ValueError(msg)
    return data


def utf16_len(text: str) -> int:
    """Return the length of ``text`` in UTF-16 code units, the unit Slides text ranges use."""
    return len(text.encode("utf-16-le")) // 2


def shape_text(element: dict[str, Any]) -> str:
    """Return the text of a shape element, or an empty string for elements without text."""
    text_elements = element.get("shape", {}).get("text", {}).get("textElements", [])
    return "".join(item.get("textRun", {}).get("content", "") for item in text_elements)


def iter_page_elements(elements: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """Yield page elements depth-first, including the children of element groups."""
    for element in elements:
        yield element
        yield from iter_page_elements(element.get("elementGroup", {}).get("children", []))


def title_shape_ids(slide: dict[str, Any]) -> set[str]:
    """Return the objectIds of the title shape on a slide.

    Title placeholders always count. Without a placeholder, the title is the
    text shape inside the top band of the slide with the largest font size,
    which matches decks that use plain text boxes for headings next to a
    smaller category badge.

    Args:
        slide: Slide page object from a presentation dump.

    Returns:
        The objectIds treated as titles (empty when the slide has no text).
    """
    titles: set[str] = set()
    candidates: list[tuple[float, float, float, str]] = []
    for element in iter_page_elements(slide.get("pageElements", [])):
        shape = element.get("shape")
        if not shape or not shape_text(element).strip():
            continue
        if shape.get("placeholder", {}).get("type") in TITLE_PLACEHOLDER_TYPES:
            titles.add(element["objectId"])
            continue
        top = _translate_pt(element, "translateY")
        if top <= TITLE_BAND_PT:
            candidates.append((-_first_font_size(shape), top, -_width_pt(element), element["objectId"]))
    if not titles and candidates:
        titles.add(min(candidates)[3])
    return titles


def summarize_slides(deck: dict[str, Any]) -> list[SlideSummary]:
    """Summarize every slide, listing text in reading order (top to bottom, then left to right).

    Args:
        deck: Parsed presentation dump.

    Returns:
        One summary per slide, in deck order.
    """
    summaries: list[SlideSummary] = []
    for index, slide in enumerate(deck.get("slides", []), start=1):
        titles = title_shape_ids(slide)
        positioned: list[tuple[float, float, str]] = []
        title = ""
        for element in iter_page_elements(slide.get("pageElements", [])):
            text = _element_text(element).strip()
            if not text:
                continue
            if not title and element.get("objectId") in titles:
                title = text.splitlines()[0].strip()
            positioned.append((_translate_pt(element, "translateY"), _translate_pt(element, "translateX"), text))
        positioned.sort()
        summaries.append(
            SlideSummary(
                index=index,
                object_id=slide.get("objectId", ""),
                skipped=bool(slide.get("slideProperties", {}).get("isSkipped", False)),
                title=title,
                texts=tuple(text for _, _, text in positioned),
                notes=_notes_text(slide),
            )
        )
    return summaries


def known_object_ids(deck: dict[str, Any]) -> set[str]:
    """Return every page and page-element objectId in a dump.

    Covers slides, their notes pages, layouts, and masters.

    Args:
        deck: Parsed presentation dump.

    Returns:
        The set of objectIds a batch may reference without creating them first.
    """
    ids: set[str] = set()
    for collection in ("slides", "layouts", "masters"):
        for page in deck.get(collection, []):
            ids.add(page.get("objectId", ""))
            ids.update(_element_ids(page.get("pageElements", [])))
            notes_page = page.get("slideProperties", {}).get("notesPage", {})
            if notes_page:
                ids.add(notes_page.get("objectId", ""))
                ids.update(_element_ids(notes_page.get("pageElements", [])))
    ids.discard("")
    return ids


def shape_text_lengths(deck: dict[str, Any]) -> dict[str, int]:
    """Map each shape objectId on slides and notes pages to its text length in UTF-16 code units.

    Args:
        deck: Parsed presentation dump.

    Returns:
        Text lengths keyed by shape objectId.
    """
    lengths: dict[str, int] = {}
    for slide in deck.get("slides", []):
        notes_elements = slide.get("slideProperties", {}).get("notesPage", {}).get("pageElements", [])
        for element in iter_page_elements([*slide.get("pageElements", []), *notes_elements]):
            if "shape" in element:
                lengths[element["objectId"]] = utf16_len(shape_text(element))
    return lengths


def _element_ids(elements: list[dict[str, Any]]) -> set[str]:
    """Return the objectIds of every element in a page-element list, including group children."""
    return {element.get("objectId", "") for element in iter_page_elements(elements)}


def _element_text(element: dict[str, Any]) -> str:
    """Return displayable text for a shape or table element."""
    if "shape" in element:
        return shape_text(element)
    rows = element.get("table", {}).get("tableRows", [])
    return "\n".join(" | ".join(_cell_text(cell) for cell in row.get("tableCells", [])) for row in rows)


def _cell_text(cell: dict[str, Any]) -> str:
    """Return the whitespace-normalized text of a table cell."""
    content = "".join(
        item.get("textRun", {}).get("content", "") for item in cell.get("text", {}).get("textElements", [])
    )
    return " ".join(content.split())


def _notes_text(slide: dict[str, Any]) -> str:
    """Return the speaker notes text for a slide."""
    notes_page = slide.get("slideProperties", {}).get("notesPage", {})
    speaker_id = notes_page.get("notesProperties", {}).get("speakerNotesObjectId")
    for element in notes_page.get("pageElements", []):
        if element.get("objectId") == speaker_id:
            return shape_text(element).strip()
    return ""


def _translate_pt(element: dict[str, Any], key: str) -> float:
    """Return a transform translation in points."""
    return float(element.get("transform", {}).get(key, 0)) / EMU_PER_PT


def _width_pt(element: dict[str, Any]) -> float:
    """Return the rendered element width in points."""
    magnitude = float(element.get("size", {}).get("width", {}).get("magnitude", 0))
    scale = float(element.get("transform", {}).get("scaleX", 1))
    return magnitude * scale / EMU_PER_PT


def _first_font_size(shape: dict[str, Any]) -> float:
    """Return the first explicit font size in a shape, or ``0.0`` when every run inherits it."""
    for item in shape.get("text", {}).get("textElements", []):
        size = item.get("textRun", {}).get("style", {}).get("fontSize", {}).get("magnitude")
        if size:
            return float(size)
    return 0.0
