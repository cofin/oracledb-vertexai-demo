# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from app.domain.products.services.maps import build_store_directions_url, build_store_search_url

_STORE_FIELDS = {
    "name": "Cymbal Coffee Dallas Arts District",
    "address": "1717 N Harwood St",
    "city": "Dallas",
    "state": "TX",
    "zip_code": "75201",
    "place_id": "place-dallas-arts",
}


def test_build_store_search_url_uses_no_key_google_maps_search() -> None:
    url = build_store_search_url(**_STORE_FIELDS)

    assert url.startswith("https://www.google.com/maps/search/?")
    assert "api=1" in url
    assert "query=Cymbal+Coffee+Dallas+Arts+District%2C+1717+N+Harwood+St%2C+Dallas%2C+TX+75201" in url
    assert "query_place_id=place-dallas-arts" in url
    assert "key=" not in url


def test_build_store_search_url_without_place_id_omits_place_id() -> None:
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
    url = build_store_directions_url(**_STORE_FIELDS)

    assert url.startswith("https://www.google.com/maps/dir/?")
    assert "api=1" in url
    assert "destination=Cymbal+Coffee+Dallas+Arts+District%2C+1717+N+Harwood+St%2C+Dallas%2C+TX+75201" in url
    assert "destination_place_id=place-dallas-arts" in url
    assert "origin=" not in url
    assert "key=" not in url


def test_build_store_directions_url_with_browser_origin_coordinates() -> None:
    url = build_store_directions_url(**_STORE_FIELDS, origin=(32.8, -96.81))

    assert "origin=32.800000%2C-96.810000" in url
    assert "destination=" in url
    assert "key=" not in url


def test_build_store_directions_url_with_string_origin() -> None:
    url = build_store_directions_url(**_STORE_FIELDS, origin="Dallas, TX")

    assert "origin=Dallas%2C+TX" in url
    assert "key=" not in url
