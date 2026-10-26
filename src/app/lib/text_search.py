# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Shared Oracle Text query token sanitization and proximity expression builders."""

from __future__ import annotations

import re

__all__ = (
    "ORACLE_TEXT_RESERVED_WORDS",
    "ORACLE_TEXT_STOPWORDS",
    "build_oracle_proximity_query",
    "build_oracle_text_query",
    "extract_search_tokens",
)

ORACLE_TEXT_RESERVED_WORDS: frozenset[str] = frozenset({
    "about",
    "accum",
    "and",
    "bt",
    "btg",
    "bti",
    "btp",
    "definescore",
    "definomerge",
    "equiv",
    "fuzzy",
    "mddata",
    "minus",
    "near",
    "not",
    "nt",
    "ntg",
    "nti",
    "ntp",
    "or",
    "pt",
    "rt",
    "sdata",
    "soundex",
    "sqe",
    "stem",
    "syn",
    "threshold",
    "tr",
    "transform",
    "trsyn",
    "wild",
    "within",
})

ORACLE_TEXT_STOPWORDS: frozenset[str] = frozenset({
    "a",
    "all",
    "am",
    "an",
    "any",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "carry",
    "do",
    "does",
    "for",
    "from",
    "give",
    "has",
    "have",
    "hello",
    "here",
    "hi",
    "how",
    "i",
    "in",
    "into",
    "is",
    "it",
    "list",
    "me",
    "my",
    "of",
    "on",
    "please",
    "sell",
    "show",
    "tell",
    "that",
    "the",
    "their",
    "there",
    "they",
    "this",
    "to",
    "us",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "you",
    "your",
})

_EXCLUDED_ORACLE_TEXT_TERMS: frozenset[str] = ORACLE_TEXT_RESERVED_WORDS | ORACLE_TEXT_STOPWORDS
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-']*")
_NON_TOKEN_CHARS_RE = re.compile(r"[^a-z0-9\-]")
_MIN_TOKEN_LEN = 2


def extract_search_tokens(text: str | None, *, max_terms: int = 16) -> list[str]:
    """Extract deduplicated, lowercase searchable tokens suitable for Oracle Text ``CONTAINS``.

    Args:
        text: Raw user search phrase or chat prompt.
        max_terms: Maximum number of distinct tokens to extract.

    Returns:
        Ordered list of sanitized alphanumeric/hyphen tokens with operators and stopwords removed.
    """
    if not text or max_terms <= 0:
        return []

    tokens: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_RE.finditer(text):
        raw = match.group(0).strip("-'").lower()
        if len(raw) < _MIN_TOKEN_LEN or raw in _EXCLUDED_ORACLE_TEXT_TERMS:
            continue
        safe = _NON_TOKEN_CHARS_RE.sub("", raw).strip("-")
        if len(safe) < _MIN_TOKEN_LEN or safe in _EXCLUDED_ORACLE_TEXT_TERMS or safe in seen:
            continue
        seen.add(safe)
        tokens.append(safe)
        if len(tokens) >= max_terms:
            break
    return tokens


def build_oracle_text_query(text: str | None, *, max_terms: int = 16) -> str | None:
    """Sanitize raw user text into a brace-escaped Oracle Text ``ACCUM`` expression.

    Args:
        text: Raw user search phrase or chat prompt.
        max_terms: Maximum number of distinct tokens to include.

    Returns:
        Sanitized ``{token} ACCUM ...`` expression, or ``None`` when no searchable tokens exist.
    """
    tokens = extract_search_tokens(text, max_terms=max_terms)
    if not tokens:
        return None
    return " ACCUM ".join(f"{{{token}}}" for token in tokens)


def build_oracle_proximity_query(
    text: str | None, *, max_span: int = 6, in_order: bool = True, max_terms: int = 8
) -> str | None:
    """Build an Oracle Text ``NEAR`` proximity expression with ``ACCUM`` recall fallback.

    Args:
        text: Raw user search phrase or chat prompt.
        max_span: Maximum token distance inside ``NEAR((...), max_span, in_order)``.
        in_order: Whether matched tokens must appear in query order for the ``NEAR`` boost.
        max_terms: Maximum number of distinct tokens to include.

    Returns:
        ``NEAR(({t1}, {t2}), span, TRUE) ACCUM ({t1} ACCUM {t2})`` when two or more tokens exist,
        ``{t1}`` for single-token queries, or ``None`` when empty.
    """
    tokens = extract_search_tokens(text, max_terms=max_terms)
    if not tokens:
        return None
    escaped = [f"{{{token}}}" for token in tokens]
    if len(escaped) == 1:
        return escaped[0]
    span = max(1, int(max_span))
    order_flag = "TRUE" if in_order else "FALSE"
    near_clause = ", ".join(escaped)
    accum_clause = " ACCUM ".join(escaped)
    return f"NEAR(({near_clause}), {span}, {order_flag}) ACCUM ({accum_clause})"
