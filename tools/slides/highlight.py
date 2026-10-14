# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Syntax highlighting for dark code cards, emitted as Slides ``updateTextStyle`` requests.

Ranges are UTF-16 offsets into the exact text placed in the code text box, so
the same string must be used for the ``insertText`` request and for
highlighting.
"""

from __future__ import annotations

import re
from typing import Any

from pygments import lex  # type: ignore[import-untyped]
from pygments.lexers import BashLexer, JsonLexer, PlPgsqlLexer, PythonLexer, SqlLexer, YamlLexer  # type: ignore[import-untyped]
from pygments.token import Comment, Keyword, Name, Number, String  # type: ignore[import-untyped]

from tools.slides.deck import utf16_len

__all__ = [
    "CODE_COLORS",
    "LANGUAGES",
    "ORACLE_FUNCTIONS",
    "ORACLE_FUNCTION_PATTERN",
    "ORACLE_KEYWORD_PATTERN",
    "hex_to_rgb",
    "highlight_code_requests",
]

CODE_COLORS: dict[str, str] = {
    "default": "#E6EDF3",
    "keyword": "#FF7B72",
    "function": "#D2A8FF",
    "string": "#A5D6FF",
    "number": "#79C0FF",
    "comment": "#8B949E",
    "operator": "#FFA657",
}
LANGUAGES: tuple[str, ...] = ("oracle", "sql", "python", "bash", "json", "yaml")
ORACLE_FUNCTIONS = frozenset({
    "ANNOTATIONS",
    "COALESCE",
    "CONTAINS",
    "GRAPH_TABLE",
    "JSON_TABLE",
    "NVL",
    "ROW_NUMBER",
    "SCORE",
    "VECTOR",
    "VECTOR_DISTANCE",
})
ORACLE_FUNCTION_PATTERN = re.compile(
    r"\bDBMS_[A-Z_]+(?:\.[A-Z_]+)?\b|\bCTX_DDL\.[A-Z_]+\b|\bCTXSYS\.[A-Z_]+\b|(?<=SELECT\s)AI\b", re.IGNORECASE
)
ORACLE_KEYWORD_PATTERN = re.compile(
    r"\b(?:APPROX|INMEMORY|NEIGHBOR|GRAPH|ORGANIZATION|ACCUM|INDEXTYPE|ACCURACY|SKIP\s+LOCKED)\b", re.IGNORECASE
)
HEX_COLOR_LENGTH = 6
CHANNEL_MAX = 255

_LEXERS: dict[str, Any] = {
    "oracle": PlPgsqlLexer,
    "sql": SqlLexer,
    "python": PythonLexer,
    "bash": BashLexer,
    "json": JsonLexer,
    "yaml": YamlLexer,
}
_TOKEN_STYLES: tuple[tuple[Any, str, bool, bool], ...] = (
    (String, "string", False, False),
    (Number, "number", False, False),
    (Keyword.Type, "function", False, False),
    (Keyword, "keyword", True, False),
    (Name.Function, "function", False, False),
    (Name.Builtin, "function", False, False),
)
_SQL_LANGUAGES = frozenset({"oracle", "sql"})

_Span = tuple[int, int, str, bool, bool]


def hex_to_rgb(hex_color: str) -> dict[str, float]:
    """Convert a ``#RRGGBB`` color to a Slides ``rgbColor`` object.

    Raises:
        ValueError: If the color is not six hexadecimal digits.
    """
    clean = hex_color.removeprefix("#")
    if len(clean) != HEX_COLOR_LENGTH:
        msg = f"expected a #RRGGBB color, got {hex_color!r}"
        raise ValueError(msg)
    return {
        "red": round(int(clean[0:2], 16) / CHANNEL_MAX, 4),
        "green": round(int(clean[2:4], 16) / CHANNEL_MAX, 4),
        "blue": round(int(clean[4:6], 16) / CHANNEL_MAX, 4),
    }


def highlight_code_requests(
    object_id: str,
    code: str,
    language: str = "oracle",
    extra_functions: frozenset[str] = frozenset(),
    *,
    include_base: bool = True,
) -> list[dict[str, Any]]:
    """Build ``updateTextStyle`` requests that syntax-highlight a code text box.

    Args:
        object_id: objectId of the code text box.
        code: Exact text of the code text box.
        language: One of :data:`LANGUAGES`. ``oracle`` adds Oracle package,
            vector-search, and Oracle Text highlighting on top of the SQL lexer.
        extra_functions: Additional names to style as functions.
        include_base: Prepend a request that resets the whole box to the base
            code color, unbolded and upright.

    Returns:
        Requests ordered so that later, more specific styles win.

    Raises:
        ValueError: If ``language`` is not supported.
    """
    functions = frozenset(name.upper() for name in ORACLE_FUNCTIONS | extra_functions)
    spans, comments = _token_spans(code, language, functions)
    if language in _SQL_LANGUAGES:
        spans.extend(_pattern_spans(code, ORACLE_KEYWORD_PATTERN, "keyword", comments))
        spans.extend(_pattern_spans(code, ORACLE_FUNCTION_PATTERN, "function", comments))
    total = utf16_len(code)
    requests = [_base_request(object_id)] if include_base else []
    requests.extend(
        _style_request(object_id, start, min(end, total), color, bold, italic)
        for start, end, color, bold, italic in spans
        if start < min(end, total)
    )
    return requests


def _lexer_for(language: str) -> Any:
    """Return a Pygments lexer that keeps leading and trailing newlines."""
    try:
        lexer_class = _LEXERS[language]
    except KeyError as exc:
        msg = f"unsupported language {language!r}; choose one of: {', '.join(LANGUAGES)}"
        raise ValueError(msg) from exc
    return lexer_class(stripnl=False)


def _classify(token_type: Any, value: str, functions: frozenset[str]) -> tuple[str, bool, bool]:
    """Map a Pygments token to a ``(color key, bold, italic)`` style."""
    if token_type in Comment:
        return ("comment", False, True)
    if value.strip().upper() in functions:
        return ("function", True, False)
    for parent, color, bold, italic in _TOKEN_STYLES:
        if token_type in parent:
            return (color, bold, italic)
    return ("default", False, False)


def _token_spans(code: str, language: str, functions: frozenset[str]) -> tuple[list[_Span], list[tuple[int, int]]]:
    """Lex ``code`` into styled spans plus the ranges covered by comments."""
    spans: list[_Span] = []
    comments: list[tuple[int, int]] = []
    position = 0
    for token_type, value in lex(code, _lexer_for(language)):
        width = utf16_len(value)
        if value.strip():
            color, bold, italic = _classify(token_type, value, functions)
            if color == "comment":
                comments.append((position, position + width))
            if color != "default":
                _append_span(spans, (position, position + width, color, bold, italic))
        position += width
    return spans, comments


def _append_span(spans: list[_Span], span: _Span) -> None:
    """Append a span, merging it into the previous span when both are adjacent and styled alike."""
    if spans and spans[-1][1] == span[0] and spans[-1][2:] == span[2:]:
        previous = spans[-1]
        spans[-1] = (previous[0], span[1], previous[2], previous[3], previous[4])
        return
    spans.append(span)


def _pattern_spans(code: str, pattern: re.Pattern[str], color: str, comments: list[tuple[int, int]]) -> list[_Span]:
    """Return bold spans for regex matches that fall outside comments."""
    bounds = [(utf16_len(code[: match.start()]), utf16_len(code[: match.end()])) for match in pattern.finditer(code)]
    return [
        (start, end, color, True, False)
        for start, end in bounds
        if not any(c_start <= start and end <= c_end for c_start, c_end in comments)
    ]


def _base_request(object_id: str) -> dict[str, Any]:
    """Return a request that resets the whole text box to the base code style."""
    return {
        "updateTextStyle": {
            "objectId": object_id,
            "textRange": {"type": "ALL"},
            "style": {
                "bold": False,
                "italic": False,
                "foregroundColor": {"opaqueColor": {"rgbColor": hex_to_rgb(CODE_COLORS["default"])}},
            },
            "fields": "bold,italic,foregroundColor",
        }
    }


def _style_request(object_id: str, start: int, end: int, color: str, bold: bool, italic: bool) -> dict[str, Any]:
    """Return an ``updateTextStyle`` request for one fixed range."""
    return {
        "updateTextStyle": {
            "objectId": object_id,
            "textRange": {"type": "FIXED_RANGE", "startIndex": start, "endIndex": end},
            "style": {
                "bold": bold,
                "italic": italic,
                "foregroundColor": {"opaqueColor": {"rgbColor": hex_to_rgb(CODE_COLORS[color])}},
            },
            "fields": "bold,italic,foregroundColor",
        }
    }
