# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Explore-page support endpoints (Ch 4 Phase 5).

Currently exposes ``GET /api/classify-compare`` which serves the Ch 3
``classify --compare`` CLI artifact for the explore-page Panel 5 chart.
The path is module-scoped so tests can redirect it at a tmp file.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from litestar import Controller, get
from litestar.exceptions import NotFoundException

from app.domain.system.schemas import ClassifyCompare, ClassifyCompareIntent
from app.lib.settings import BASE_DIR
from app.utils.serialization import from_json

CLASSIFY_COMPARE_PATH: Path = BASE_DIR.parents[1] / "dist" / "classify-compare.json"


def _summarize(rows: list[dict[str, str]]) -> list[ClassifyCompareIntent]:
    """Per-intent counts (gold / legacy / new) plus precision/recall/agreement.

    Precision and recall are computed against the gold labels for the
    *new* classifier — the legacy column is shown only as raw counts.
    """
    intents = sorted({row["gold"] for row in rows} | {row["new"] for row in rows} | {row["legacy"] for row in rows})
    gold_counts = Counter(row["gold"] for row in rows)
    legacy_counts = Counter(row["legacy"] for row in rows)
    new_counts = Counter(row["new"] for row in rows)

    summary: list[ClassifyCompareIntent] = []
    for intent in intents:
        gold_n = gold_counts[intent]
        new_n = new_counts[intent]
        true_positives = sum(1 for row in rows if row["gold"] == intent and row["new"] == intent)
        intent_rows = [row for row in rows if row["gold"] == intent]
        agreement = (
            sum(1 for row in intent_rows if row["legacy"] == row["new"]) / len(intent_rows) if intent_rows else 0.0
        )
        summary.append(
            ClassifyCompareIntent(
                intent=intent,
                gold=gold_n,
                legacy=legacy_counts[intent],
                new=new_n,
                precision=(true_positives / new_n) if new_n else 0.0,
                recall=(true_positives / gold_n) if gold_n else 0.0,
                agreement=agreement,
            )
        )
    return summary


class ExploreController(Controller):
    """Explore-page panels that don't fit cleanly under products / system."""

    @get(
        path="/api/classify-compare",
        name="explore.classify_compare",
        exclude_from_auth=True,
    )
    async def classify_compare(self) -> ClassifyCompare:
        if not CLASSIFY_COMPARE_PATH.exists():
            raise NotFoundException(
                detail=(
                    "classify-compare.json not found — run "
                    "`uv run coffee classify --compare` to generate it."
                )
            )
        payload = from_json(CLASSIFY_COMPARE_PATH.read_bytes())
        return ClassifyCompare(intents=_summarize(payload.get("rows", [])))
