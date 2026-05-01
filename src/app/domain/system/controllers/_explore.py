# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

from litestar import Controller, get

from app.domain.system.schemas import ClassifyCompare
from app.lib.settings import BASE_DIR
from app.utils.serialization import from_json

CLASSIFY_COMPARE_PATH = BASE_DIR.parents[1] / "dist" / "classify-compare.json"
_MISSING_HINT = "Run `uv run coffee classify-compare` to generate dist/classify-compare.json."


class ExploreController(Controller):
    """Explore-page auxiliary endpoints."""

    @get(path="/api/classify-compare", name="explore.classify_compare")
    async def classify_compare(self) -> ClassifyCompare:
        if not CLASSIFY_COMPARE_PATH.exists():
            return ClassifyCompare(available=False, rows=[], summary={}, hint=_MISSING_HINT)

        data = from_json(CLASSIFY_COMPARE_PATH.read_bytes())
        if not isinstance(data, dict):
            return ClassifyCompare(available=False, rows=[], summary={}, hint="classify-compare data is malformed.")

        rows = data.get("rows", [])
        summary = data.get("summary", {})
        return ClassifyCompare(
            available=True,
            rows=rows if isinstance(rows, list) else [],
            summary=summary if isinstance(summary, dict) else {},
            hint=None,
        )


__all__ = ("CLASSIFY_COMPARE_PATH", "ExploreController")
