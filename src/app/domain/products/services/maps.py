# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode, urlunsplit

if TYPE_CHECKING:
    from app.domain.products.schemas import Store

_MAPS_HOST = "www.google.com"


def build_store_search_url(store: Store) -> str:
    """Build a no-key Google Maps search URL for a store."""
    params = {"query": _store_query(store)}
    if store.google_place_id:
        params["query_place_id"] = store.google_place_id
    return _maps_url("/maps/search/", params)


def build_store_directions_url(store: Store, origin: tuple[float, float] | str | None = None) -> str:
    """Build a no-key Google Maps directions URL for a store."""
    params = {"destination": _store_query(store)}
    if store.google_place_id:
        params["destination_place_id"] = store.google_place_id
    if isinstance(origin, tuple):
        params["origin"] = f"{origin[0]:.6f},{origin[1]:.6f}"
    elif origin:
        params["origin"] = origin
    return _maps_url("/maps/dir/", params)


def _store_query(store: Store) -> str:
    locality = " ".join(part for part in (store.state, store.zip) if part)
    city_region = ", ".join(part for part in (store.city, locality) if part)
    return ", ".join(part for part in (store.name, store.address, city_region) if part)


def _maps_url(path: str, params: dict[str, str]) -> str:
    return urlunsplit(("https", _MAPS_HOST, path, urlencode({"api": "1", **params}), ""))
