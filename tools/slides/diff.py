# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Word-level differences between two presentation dumps, matched by slide objectId.

Copies made with a Drive copy keep slide objectIds, so a copy edited by hand
can be compared with the main deck slide by slide even after slides move.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tools.slides.deck import summarize_slides

if TYPE_CHECKING:
    from tools.slides.deck import SlideSummary

__all__ = ["SlideDiff", "diff_decks"]


@dataclass(frozen=True, slots=True)
class SlideDiff:
    """Change summary for one slide.

    Attributes:
        object_id: Slide objectId shared by both dumps.
        status: ``added``, ``removed``, or ``changed``.
        removed: Phrases present only in the old dump.
        added: Phrases present only in the new dump.
    """

    object_id: str
    status: str
    removed: tuple[str, ...]
    added: tuple[str, ...]


def diff_decks(old: dict[str, Any], new: dict[str, Any]) -> list[SlideDiff]:
    """Compare slide text and speaker notes between two dumps.

    Args:
        old: Presentation dump taken first.
        new: Presentation dump taken later, or from a copy.

    Returns:
        One entry per slide that was added, removed, or changed, in old-deck order
        followed by slides that exist only in the new dump.
    """
    old_words = {summary.object_id: _slide_words(summary) for summary in summarize_slides(old)}
    new_words = {summary.object_id: _slide_words(summary) for summary in summarize_slides(new)}
    diffs: list[SlideDiff] = []
    for object_id, words in old_words.items():
        if object_id not in new_words:
            diffs.append(SlideDiff(object_id, "removed", (), ()))
            continue
        removed, added = _word_changes(words, new_words[object_id])
        if removed or added:
            diffs.append(SlideDiff(object_id, "changed", removed, added))
    diffs.extend(SlideDiff(object_id, "added", (), ()) for object_id in new_words if object_id not in old_words)
    return diffs


def _slide_words(summary: SlideSummary) -> list[str]:
    """Return the words of a slide's text followed by its speaker notes."""
    return " ".join([*summary.texts, summary.notes]).split()


def _word_changes(old: list[str], new: list[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return the phrases removed from and added to a word sequence."""
    removed: list[str] = []
    added: list[str] = []
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            removed.append(" ".join(old[old_start:old_end]))
        if tag in {"replace", "insert"}:
            added.append(" ".join(new[new_start:new_end]))
    return tuple(removed), tuple(added)
