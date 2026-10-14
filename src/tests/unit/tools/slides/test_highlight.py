# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for code-card syntax highlighting requests."""

from __future__ import annotations

from typing import Any

import pytest
from tools.slides.deck import utf16_len
from tools.slides.highlight import CODE_COLORS, hex_to_rgb, highlight_code_requests


def _style_at(requests: list[dict[str, Any]], position: int) -> dict[str, Any]:
    """Return the effective style at a UTF-16 position after applying requests in order."""
    style: dict[str, Any] = {}
    for request in requests:
        body = request["updateTextStyle"]
        text_range = body["textRange"]
        if text_range["type"] == "ALL" or text_range["startIndex"] <= position < text_range["endIndex"]:
            style = {**style, **body["style"]}
    return style


def _color_at(requests: list[dict[str, Any]], position: int) -> dict[str, float]:
    """Return the effective foreground RGB color at a UTF-16 position."""
    color: dict[str, float] = _style_at(requests, position)["foregroundColor"]["opaqueColor"]["rgbColor"]
    return color


def test_keywords_functions_and_comments_get_distinct_styles() -> None:
    """Keywords are bold, Oracle functions use the function color, and comments are italic."""
    code = "-- nearest products\nSELECT id FROM product ORDER BY VECTOR_DISTANCE(embedding, :q, COSINE)"

    requests = highlight_code_requests("code_box", code)

    assert requests[0]["updateTextStyle"]["textRange"] == {"type": "ALL"}
    assert _style_at(requests, 3)["italic"] is True
    assert _style_at(requests, code.index("SELECT"))["bold"] is True
    assert _color_at(requests, code.index("SELECT")) == hex_to_rgb(CODE_COLORS["keyword"])
    assert _color_at(requests, code.index("VECTOR_DISTANCE")) == hex_to_rgb(CODE_COLORS["function"])


def test_oracle_phrases_are_highlighted_outside_comments() -> None:
    """APPROX and DBMS_* calls are styled in code, but not when they appear in a comment."""
    code = "-- DBMS_VECTOR in a comment\nSELECT DBMS_VECTOR.UTL_TO_EMBEDDING(:t, :p) FROM dual FETCH APPROX FIRST 5 ROWS ONLY"

    requests = highlight_code_requests("code_box", code)

    assert _color_at(requests, 4) == hex_to_rgb(CODE_COLORS["comment"])
    assert _color_at(requests, code.index("DBMS_VECTOR.UTL")) == hex_to_rgb(CODE_COLORS["function"])
    assert _color_at(requests, code.index("APPROX")) == hex_to_rgb(CODE_COLORS["keyword"])


def test_offsets_are_utf16_and_clamped_to_the_text() -> None:
    """Ranges after an emoji shift by two units and never run past the end of the text."""
    code = "-- 🟡 tip\nSELECT 1 FROM dual"

    requests = highlight_code_requests("code_box", code)

    select_offset = utf16_len(code[: code.index("SELECT")])
    assert _style_at(requests, select_offset)["bold"] is True
    ends = [request["updateTextStyle"]["textRange"].get("endIndex", 0) for request in requests]
    assert max(ends) <= utf16_len(code)


def test_unsupported_language_is_rejected() -> None:
    """Only the documented languages are accepted."""
    with pytest.raises(ValueError, match="unsupported language"):
        highlight_code_requests("code_box", "print(1)", language="cobol")
