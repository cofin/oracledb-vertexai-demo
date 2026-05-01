# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Classify-compare explore endpoint contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.utils.serialization import to_json

if TYPE_CHECKING:
    from pathlib import Path

    from litestar.testing import AsyncTestClient

pytestmark = pytest.mark.anyio


async def test_classify_compare_missing_file_returns_hint(
    client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.domain.system.controllers import _explore

    monkeypatch.setattr(_explore, "CLASSIFY_COMPARE_PATH", tmp_path / "missing.json")

    response = await client.get("/api/classify-compare")

    assert response.status_code == 200, response.text[:500]
    payload = response.json()
    assert payload["available"] is False
    assert payload["rows"] == []
    assert "coffee classify-compare" in payload["hint"]


async def test_classify_compare_present_file_returns_dataset(
    client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.domain.system.controllers import _explore

    dataset = {
        "rows": [{"phrase": "what's good", "gold": "PRODUCT_RAG", "legacy": "PRODUCT_RAG", "new": "PRODUCT_RAG"}],
        "summary": {"per_intent": {"PRODUCT_RAG": {"precision": 1.0, "recall": 1.0, "agreement": 1.0}}},
    }
    path = tmp_path / "classify-compare.json"
    path.write_text(to_json(dataset), encoding="utf-8")
    monkeypatch.setattr(_explore, "CLASSIFY_COMPARE_PATH", path)

    response = await client.get("/api/classify-compare")

    assert response.status_code == 200, response.text[:500]
    payload = response.json()
    assert payload["available"] is True
    assert payload["rows"] == dataset["rows"]
    assert payload["summary"] == dataset["summary"]
