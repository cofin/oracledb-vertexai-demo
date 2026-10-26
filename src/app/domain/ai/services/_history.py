# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Session state hydration, coordinate-safe turn state sanitization, and product history extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

import msgspec

from app.utils.serialization import decode_json

if TYPE_CHECKING:
    from app.domain.ai.runtime._types import AgentEvent

__all__ = ("extract_last_products", "extract_session_state", "has_session_context")


def extract_session_state(existing: Mapping[str, Any] | None) -> dict[str, Any]:
    """Decode and sanitize persisted session state, stripping any raw browser coordinates.

    Args:
        existing: Optional session row mapping returned by ``OracleSessionStore.get_session``.

    Returns:
        Sanitized dictionary of persisted session state fields.
    """
    if not isinstance(existing, Mapping):
        return {}
    raw_state = existing.get("state")
    parsed: dict[str, Any] = {}
    if isinstance(raw_state, Mapping):
        parsed = dict(raw_state)
    elif isinstance(raw_state, str) and raw_state.strip():
        try:
            decoded = decode_json(raw_state)
        except msgspec.DecodeError:
            return {}
        if isinstance(decoded, Mapping):
            parsed = dict(decoded)
    parsed.pop("coordinates", None)
    loc = parsed.get("location_context")
    if isinstance(loc, Mapping):
        cleaned_loc = dict(loc)
        cleaned_loc.pop("coordinates", None)
        cleaned_loc.pop("latitude", None)
        cleaned_loc.pop("longitude", None)
        parsed["location_context"] = cleaned_loc
    return parsed


def extract_last_products(session_state: Mapping[str, Any]) -> list[str] | None:
    """Extract normalized non-empty product names from persisted session state.

    Args:
        session_state: Decoded session state mapping.

    Returns:
        List of product names if present, otherwise ``None``.
    """
    raw = session_state.get("last_products")
    if not isinstance(raw, list):
        return None
    return [str(item) for item in raw if str(item).strip()] or None


def has_session_context(history: Sequence[AgentEvent], session_state: Mapping[str, Any]) -> bool:
    """Return True when prior conversation history or tracked product context is active.

    Args:
        history: Ordered list of prior ``AgentEvent`` turns.
        session_state: Decoded session state mapping.

    Returns:
        Boolean indicating whether global response cache reads/writes must be bypassed.
    """
    return bool(history) or bool(extract_last_products(session_state))
