# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Phase 5.1c contract: ``GET /api/classify-compare`` serves the
Ch 3 CLI artifact (``dist/classify-compare.json``) for the explore-page
Panel 5 grouped-bar chart.

Two branches are exercised here:
* file missing → 404 with a hint pointing at the CLI command
* file present → 200 with per-intent counts (gold vs legacy vs new) plus
  per-intent precision / recall / agreement
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from litestar.testing import AsyncTestClient

pytestmark = pytest.mark.anyio


@pytest.fixture
def _classify_compare_path(monkeypatch: pytest.MonkeyPatch, tmp_path: "Path") -> "Path":
    """Redirect the controller at a tmp file we control per-test."""
    target = tmp_path / "classify-compare.json"
    from app.domain.system.controllers import _explore

    monkeypatch.setattr(_explore, "CLASSIFY_COMPARE_PATH", target)
    return target


async def test_classify_compare_returns_404_when_missing(
    client: "AsyncTestClient", _classify_compare_path: "Path"
) -> None:
    assert not _classify_compare_path.exists()
    response = await client.get("/api/classify-compare")
    assert response.status_code == 404


async def test_classify_compare_returns_per_intent_metrics(
    client: "AsyncTestClient", _classify_compare_path: "Path"
) -> None:
    _classify_compare_path.write_text(
        json.dumps(
            {
                "rows": [
                    # 3x RECOMMEND gold; legacy gets 2 right, new gets 3
                    {"phrase": "x", "gold": "RECOMMEND", "legacy": "RECOMMEND", "new": "RECOMMEND"},
                    {"phrase": "y", "gold": "RECOMMEND", "legacy": "GENERAL", "new": "RECOMMEND"},
                    {"phrase": "z", "gold": "RECOMMEND", "legacy": "RECOMMEND", "new": "RECOMMEND"},
                    # 1x GENERAL — both classifiers right
                    {"phrase": "w", "gold": "GENERAL", "legacy": "GENERAL", "new": "GENERAL"},
                ]
            }
        )
    )

    response = await client.get("/api/classify-compare")
    assert response.status_code == 200, response.text[:500]
    payload = response.json()

    intents = {row["intent"]: row for row in payload["intents"]}
    assert intents["RECOMMEND"]["gold"] == 3
    assert intents["RECOMMEND"]["legacy"] == 2
    assert intents["RECOMMEND"]["new"] == 3
    assert intents["RECOMMEND"]["agreement"] == pytest.approx(2 / 3)

    assert intents["GENERAL"]["gold"] == 1
    # Legacy mis-classified one RECOMMEND as GENERAL so the GENERAL legacy
    # column is 2 even though only one row's gold is GENERAL.
    assert intents["GENERAL"]["legacy"] == 2
    assert intents["GENERAL"]["new"] == 1
    assert intents["GENERAL"]["agreement"] == 1.0
