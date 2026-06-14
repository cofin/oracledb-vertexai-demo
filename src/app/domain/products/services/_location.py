# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Private location ranking helpers for product/store services."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.products.schemas import ProductAvailability, Store


MIN_LOCATION_HINT_NAME_LENGTH = 3


def haversine_miles(latitude: float, longitude: float, store: Store | ProductAvailability) -> float:
    """Return local distance in miles without calling external Maps APIs."""
    if store.latitude is None or store.longitude is None:
        return float("inf")
    earth_radius_miles = 3958.8
    lat1 = radians(latitude)
    lon1 = radians(longitude)
    lat2 = radians(store.latitude)
    lon2 = radians(store.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * earth_radius_miles * asin(sqrt(a))


def store_matches_hint(store: Store | ProductAvailability, location_hint: str) -> bool:
    normalized = location_hint.casefold().strip()
    if not normalized:
        return True
    name = getattr(store, "store_name", getattr(store, "name", None))
    fields = (
        name,
        getattr(store, "store_address", None),
        getattr(store, "store_city", None),
        getattr(store, "store_state", None),
        getattr(store, "store_zip", None),
        getattr(store, "address", None),
        getattr(store, "city", None),
        getattr(store, "state", None),
        getattr(store, "zip", None),
    )
    if any(normalized in str(field or "").casefold() for field in fields):
        return True
    return bool(name and len(name) > MIN_LOCATION_HINT_NAME_LENGTH and name.casefold() in normalized)


def location_hint_matches(row: ProductAvailability, location_hint: str) -> bool:
    return store_matches_hint(row, location_hint)
