# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Offline Google Slides helpers for building and checking presentation batches.

The helpers read a presentation JSON dump, build ``batchUpdate`` request
payloads, and validate them before any tool applies them to a live deck. None
of them call a Slides API; fetching dumps and applying batches is left to the
Slides tooling configured for your environment.
"""

from __future__ import annotations

from tools.slides.cli import slides_group
from tools.slides.deck import SlideSummary, load_deck, summarize_slides
from tools.slides.diff import SlideDiff, diff_decks
from tools.slides.highlight import highlight_code_requests
from tools.slides.qr import write_qr_png
from tools.slides.validate import ValidationIssue, validate_requests

__all__ = [
    "SlideDiff",
    "SlideSummary",
    "ValidationIssue",
    "diff_decks",
    "highlight_code_requests",
    "load_deck",
    "slides_group",
    "summarize_slides",
    "validate_requests",
    "write_qr_png",
]
