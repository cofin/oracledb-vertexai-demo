# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from urllib.parse import urlencode, urlunsplit

_MAPS_HOST = "www.google.com"


def build_store_search_url(
    name: str, address: str, city: str, state: str, zip_code: str, place_id: str | None = None
) -> str:
    """Build a no-key Google Maps search URL for a store."""
    params = {"query": _store_query(name, address, city, state, zip_code)}
    if place_id:
        params["query_place_id"] = place_id
    return _maps_url("/maps/search/", params)


def build_store_directions_url(
    name: str,
    address: str,
    city: str,
    state: str,
    zip_code: str,
    place_id: str | None = None,
    origin: tuple[float, float] | str | None = None,
) -> str:
    """Build a no-key Google Maps directions URL for a store."""
    params = {"destination": _store_query(name, address, city, state, zip_code)}
    if place_id:
        params["destination_place_id"] = place_id
    if isinstance(origin, tuple):
        params["origin"] = f"{origin[0]:.6f},{origin[1]:.6f}"
    elif origin:
        params["origin"] = origin
    return _maps_url("/maps/dir/", params)


def _store_query(name: str, address: str, city: str, state: str, zip_code: str) -> str:
    locality = " ".join(part for part in (state, zip_code) if part)
    city_region = ", ".join(part for part in (city, locality) if part)
    return ", ".join(part for part in (name, address, city_region) if part)


def _maps_url(path: str, params: dict[str, str]) -> str:
    return urlunsplit(("https", _MAPS_HOST, path, urlencode({"api": "1", **params}), ""))
