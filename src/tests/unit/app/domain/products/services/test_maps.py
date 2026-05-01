# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.products.schemas import Store
from app.domain.products.services.maps import build_store_directions_url, build_store_search_url


def _store() -> Store:
    now = datetime(2026, 5, 1, tzinfo=UTC)
    return Store(
        id=16,
        name="Cymbal Coffee Dallas Arts District",
        address="1717 N Harwood St",
        city="Dallas",
        state="TX",
        zip="75201",
        phone="(214) 555-1500",
        latitude=32.7876,
        longitude=-96.7994,
        timezone="America/Chicago",
        google_place_id="place-dallas-arts",
        hours={"monday": "6am-8pm"},
        metadata={"wifi": True},
        created_at=now,
        updated_at=now,
    )


def test_build_store_search_url_uses_no_key_google_maps_search() -> None:
    url = build_store_search_url(_store())

    assert url.startswith("https://www.google.com/maps/search/?")
    assert "api=1" in url
    assert "query=Cymbal+Coffee+Dallas+Arts+District%2C+1717+N+Harwood+St%2C+Dallas%2C+TX+75201" in url
    assert "query_place_id=place-dallas-arts" in url
    assert "key=" not in url


def test_build_store_directions_url_without_origin() -> None:
    url = build_store_directions_url(_store())

    assert url.startswith("https://www.google.com/maps/dir/?")
    assert "api=1" in url
    assert "destination=Cymbal+Coffee+Dallas+Arts+District%2C+1717+N+Harwood+St%2C+Dallas%2C+TX+75201" in url
    assert "destination_place_id=place-dallas-arts" in url
    assert "origin=" not in url
    assert "key=" not in url


def test_build_store_directions_url_with_browser_origin_coordinates() -> None:
    url = build_store_directions_url(_store(), origin=(32.8, -96.81))

    assert "origin=32.800000%2C-96.810000" in url
    assert "destination=" in url
    assert "key=" not in url
