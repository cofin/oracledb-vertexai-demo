# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for no-key Google Maps search and directions URL builders."""

from __future__ import annotations

import app.domain.products.services as products_services
import app.domain.products.services._maps as maps_module
from app.domain.products.services import build_store_directions_url, build_store_search_url

_STORE_FIELDS = {
    "name": "Cymbal Coffee Dallas Arts District",
    "address": "1717 N Harwood St",
    "city": "Dallas",
    "state": "TX",
    "zip_code": "75201",
    "place_id": "place-dallas-arts",
}


def test_build_store_search_url_uses_no_key_google_maps_search() -> None:
    """Verify `build_store_search_url` builds a Google Maps search URL without an API key."""
    url = build_store_search_url(**_STORE_FIELDS)

    assert url.startswith("https://www.google.com/maps/search/?")
    assert "api=1" in url
    assert "query=Cymbal+Coffee+Dallas+Arts+District%2C+1717+N+Harwood+St%2C+Dallas%2C+TX+75201" in url
    assert "query_place_id=place-dallas-arts" in url
    assert "key=" not in url


def test_build_store_search_url_without_place_id_omits_place_id() -> None:
    """Verify `build_store_search_url` omits `query_place_id` when `place_id` is None."""
    url = build_store_search_url(
        name="Cymbal Coffee Dallas Arts District",
        address="1717 N Harwood St",
        city="Dallas",
        state="TX",
        zip_code="75201",
    )

    assert "query_place_id=" not in url
    assert "key=" not in url


def test_build_store_directions_url_without_origin() -> None:
    """Verify `build_store_directions_url` omits `origin` when not provided."""
    url = build_store_directions_url(**_STORE_FIELDS)

    assert url.startswith("https://www.google.com/maps/dir/?")
    assert "api=1" in url
    assert "destination=Cymbal+Coffee+Dallas+Arts+District%2C+1717+N+Harwood+St%2C+Dallas%2C+TX+75201" in url
    assert "destination_place_id=place-dallas-arts" in url
    assert "origin=" not in url
    assert "key=" not in url


def test_build_store_directions_url_with_browser_origin_coordinates() -> None:
    """Verify `build_store_directions_url` encodes coordinate origins."""
    url = build_store_directions_url(**_STORE_FIELDS, origin=(32.8, -96.81))

    assert "origin=32.800000%2C-96.810000" in url
    assert "destination=" in url
    assert "key=" not in url


def test_build_store_directions_url_with_string_origin() -> None:
    """Verify `build_store_directions_url` encodes string origins and `MapsService` facade is removed."""
    url = build_store_directions_url(**_STORE_FIELDS, origin="Dallas, TX")

    assert "origin=Dallas%2C+TX" in url
    assert "key=" not in url
    assert tuple(maps_module.__all__) == ("build_store_directions_url", "build_store_search_url")
    assert not hasattr(maps_module, "MapsService")
    assert not hasattr(products_services, "MapsService")
