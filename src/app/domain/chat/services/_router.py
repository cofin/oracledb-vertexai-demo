# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Single-query Oracle 26ai Hybrid RRF route resolver and Oracle Text query sanitizer."""

from __future__ import annotations

import re
import time
from typing import cast

import msgspec

from app.config import db_manager
from app.domain.chat.schemas import (
    HybridProductCandidate,
    HybridRouteLabel,
    HybridSearchRow,
    HybridStoreCandidate,
    HybridTurnContext,
    TermHitRow,
)
from app.lib.service import OracleAsyncService

__all__ = (
    "HybridRouteResolver",
    "build_oracle_text_query",
    "extract_candidate_terms",
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-']*")
_CAPITALIZED_RE = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
_QUOTED_RE = re.compile(r"['\"]([A-Za-z][A-Za-z0-9\-\s]{2,30})['\"]")
_MIN_TOKEN_LEN = 2
_MAX_QUERY_TOKENS = 16
_DETERMINISTIC_MARGIN_MIN = 0.004
_DETERMINISTIC_RRF_MIN = 0.028

_ORACLE_TEXT_RESERVED_AND_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "accum",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "bt",
        "btg",
        "bti",
        "btp",
        "by",
        "can",
        "carry",
        "definescore",
        "definomerge",
        "do",
        "does",
        "equiv",
        "for",
        "from",
        "fuzzy",
        "give",
        "has",
        "have",
        "here",
        "hi",
        "hello",
        "how",
        "i",
        "in",
        "into",
        "is",
        "it",
        "list",
        "mddata",
        "me",
        "minus",
        "my",
        "near",
        "not",
        "nt",
        "ntg",
        "nti",
        "ntp",
        "of",
        "on",
        "or",
        "please",
        "pt",
        "rt",
        "sdata",
        "sell",
        "show",
        "soundex",
        "sqe",
        "stem",
        "syn",
        "tell",
        "that",
        "the",
        "their",
        "there",
        "they",
        "this",
        "threshold",
        "to",
        "tr",
        "transform",
        "trsyn",
        "us",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "wild",
        "will",
        "with",
        "within",
        "you",
        "your",
    }
)

_NON_BRAND_PROPER_WORDS = frozenset(
    {
        "Are",
        "Austin",
        "Ave",
        "Bean",
        "Bishop",
        "Blend",
        "Brew",
        "Can",
        "Capitol",
        "Chicago",
        "Cold",
        "Colombian",
        "Compare",
        "Concentrate",
        "Coffee",
        "Cymbal",
        "Dallas",
        "District",
        "Do",
        "Does",
        "Downtown",
        "Espresso",
        "Ethiopian",
        "Francisco",
        "Give",
        "Google",
        "Guatemalan",
        "Hello",
        "Hill",
        "House",
        "How",
        "Is",
        "Kenyan",
        "List",
        "Maps",
        "My",
        "Not",
        "Pearl",
        "Place",
        "Portland",
        "Recommend",
        "Roast",
        "San",
        "Seattle",
        "Show",
        "SoMa",
        "Tell",
        "The",
        "Velvet",
        "What",
        "When",
        "Where",
        "Which",
        "Whole",
        "Yirgacheffe",
    }
)

_VALID_ROUTES: frozenset[str] = frozenset(
    {
        "PRODUCT_RAG",
        "PRODUCT_AVAILABILITY",
        "STORE_LOCATION",
        "ORDER_STATUS",
        "GENERAL_CONVERSATION",
    }
)


def build_oracle_text_query(user_query: str) -> str | None:
    """Sanitize a raw user message into a safe Oracle Text ``CONTAINS`` expression.

    Each searchable alphanumeric token is stripped of Oracle Text punctuation,
    filtered against reserved words and stopwords, wrapped in ``{token}``
    literal braces to prevent ``DRG-50901`` parser errors, and joined with
    ``ACCUM``.

    Args:
        user_query: Raw user message string.

    Returns:
        Sanitized Oracle Text query string, or ``None`` if no searchable tokens remain.
    """
    cleaned_tokens: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_RE.finditer(user_query):
        raw = match.group(0).strip("-'").lower()
        if len(raw) < _MIN_TOKEN_LEN or raw in _ORACLE_TEXT_RESERVED_AND_STOPWORDS:
            continue
        safe = re.sub(r"[^a-z0-9\-]", "", raw).strip("-")
        if len(safe) < _MIN_TOKEN_LEN or safe in _ORACLE_TEXT_RESERVED_AND_STOPWORDS or safe in seen:
            continue
        seen.add(safe)
        cleaned_tokens.append(f"{{{safe}}}")
        if len(cleaned_tokens) >= _MAX_QUERY_TOKENS:
            break

    if not cleaned_tokens:
        return None
    return " ACCUM ".join(cleaned_tokens)


def extract_candidate_terms(user_query: str) -> list[str]:
    """Extract proper-noun or quoted product/brand candidate tokens for per-term lexical hit checks.

    Args:
        user_query: Raw user message string.

    Returns:
        Deduplicated list of sanitized candidate tokens to verify against ``hybrid-term-hits``.
    """
    candidates: list[str] = []
    seen: set[str] = set()

    for match in _QUOTED_RE.finditer(user_query):
        for word in _TOKEN_RE.findall(match.group(1)):
            clean = re.sub(r"[^A-Za-z0-9\-]", "", word).strip("-")
            if len(clean) >= _MIN_TOKEN_LEN and clean.lower() not in seen:
                seen.add(clean.lower())
                candidates.append(clean)

    tokens = list(_CAPITALIZED_RE.finditer(user_query))
    for idx, match in enumerate(tokens):
        word = match.group(0)
        if idx == 0 and match.start() == 0 and word in _NON_BRAND_PROPER_WORDS:
            continue
        if word in _NON_BRAND_PROPER_WORDS or word.lower() in _ORACLE_TEXT_RESERVED_AND_STOPWORDS:
            continue
        if word.lower() not in seen:
            seen.add(word.lower())
            candidates.append(word)

    return candidates[:8]


class HybridRouteResolver(OracleAsyncService):
    """Executes single-query Oracle 26ai Hybrid RRF search and resolves turn routing."""

    async def resolve_turn(
        self,
        *,
        user_message: str,
        query_embedding: list[float],
        rrf_k: int = 60,
        limit: int = 5,
    ) -> HybridTurnContext:
        """Run ``hybrid-search-turn`` and ``hybrid-term-hits`` to resolve route and grounded candidates.

        Args:
            user_message: Raw user prompt.
            query_embedding: 3072-dimension query embedding vector.
            rrf_k: Reciprocal Rank Fusion smoothing constant (default 60).
            limit: Maximum product/store candidates to return.

        Returns:
            Populated ``HybridTurnContext`` with route decision, candidates, and off-menu terms.
        """
        oracle_text_query = build_oracle_text_query(user_message)
        has_text_query = 1 if oracle_text_query is not None else 0
        bind_text_query = oracle_text_query if oracle_text_query is not None else "{coffee}"

        start = time.perf_counter()
        rows = await self.driver.select(
            db_manager.get_sql("hybrid-search-turn"),
            has_text_query=has_text_query,
            text_query=bind_text_query,
            query_vector=query_embedding,
            rrf_k=rrf_k,
            limit=limit,
            schema_type=HybridSearchRow,
        )

        candidate_terms = extract_candidate_terms(user_message)
        term_hits: dict[str, int] = {}
        if candidate_terms:
            terms_json = msgspec.json.encode(candidate_terms).decode("utf-8")
            hit_rows = await self.driver.select(
                db_manager.get_sql("hybrid-term-hits"),
                terms_json=terms_json,
                schema_type=TermHitRow,
            )
            for hit in hit_rows:
                term_hits[hit.term] = int(hit.hit_count)

        oracle_ms = (time.perf_counter() - start) * 1000.0
        return _build_turn_context(
            user_message=user_message,
            oracle_text_query=oracle_text_query,
            rows=rows,
            term_hits=term_hits,
            oracle_time_ms=oracle_ms,
        )


def _build_turn_context(
    *,
    user_message: str,
    oracle_text_query: str | None,
    rows: list[HybridSearchRow],
    term_hits: dict[str, int],
    oracle_time_ms: float,
) -> HybridTurnContext:
    """Assemble ``HybridTurnContext`` from fused rows and per-term lexical hit counts."""
    route_rows = [r for r in rows if r.entity_type == "route" and r.route_label in _VALID_ROUTES]
    route_rows.sort(key=lambda r: r.rrf_score, reverse=True)

    route_scores = {r.route_label: r.rrf_score for r in route_rows if r.route_label is not None}

    products = [
        HybridProductCandidate(
            id=int(r.entity_id),
            name=r.name,
            description=r.description or "",
            category=r.category,
            price=float(r.price or 0.0),
            in_stock=bool(r.in_stock) if r.in_stock is not None else True,
            lexical_score=float(r.lexical_score or 0.0),
            vector_similarity=float(r.vector_similarity or 0.0),
            lexical_rank=r.lexical_rank,
            vector_rank=r.vector_rank,
            rrf_score=float(r.rrf_score or 0.0),
        )
        for r in rows
        if r.entity_type == "product"
    ]
    products.sort(key=lambda p: p.rrf_score, reverse=True)

    stores = [
        HybridStoreCandidate(
            id=int(r.entity_id),
            name=r.name,
            address=r.address or r.description or "",
            city=r.city,
            state=r.state,
            lexical_score=float(r.lexical_score or 0.0),
            lexical_rank=r.lexical_rank,
            rrf_score=float(r.rrf_score or 0.0),
        )
        for r in rows
        if r.entity_type == "store"
    ]
    stores.sort(key=lambda s: s.rrf_score, reverse=True)

    top_label: HybridRouteLabel = "GENERAL_CONVERSATION"
    top_score = 0.0
    second_score = 0.0
    if route_rows and route_rows[0].route_label is not None:
        top_label = cast("HybridRouteLabel", route_rows[0].route_label)
        top_score = float(route_rows[0].rrf_score)
        if len(route_rows) > 1:
            second_score = float(route_rows[1].rrf_score)

    margin = top_score - second_score
    total_top_two = top_score + second_score
    confidence = round(top_score / total_top_two, 4) if total_top_two > 0 else 0.5

    is_deterministic = (
        top_label != "GENERAL_CONVERSATION"
        and top_score >= _DETERMINISTIC_RRF_MIN
        and margin >= _DETERMINISTIC_MARGIN_MIN
    )

    off_menu_terms = [term for term, count in term_hits.items() if count == 0]

    return HybridTurnContext(
        user_message=user_message,
        oracle_text_query=oracle_text_query,
        intent_detected=top_label,
        is_deterministic=is_deterministic,
        route_confidence=confidence,
        route_scores=route_scores,
        products=products,
        stores=stores,
        term_hits=term_hits,
        off_menu_terms=off_menu_terms,
        oracle_time_ms=round(oracle_time_ms, 2),
    )
