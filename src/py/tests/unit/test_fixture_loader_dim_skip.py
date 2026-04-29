from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.utils.fixtures import FixtureProcessor

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def processor(tmp_path: Path) -> FixtureProcessor:
    return FixtureProcessor(tmp_path, expected_vector_dim=3072)


def test_prepare_record_drops_vector_column_with_mismatched_dim(
    processor: FixtureProcessor, capsys: pytest.CaptureFixture[str]
) -> None:
    record = {"id": 1, "phrase": "hello", "embedding": [0.1] * 768}

    prepared = dict(processor.prepare_record(record))

    assert "embedding" not in prepared
    assert prepared == {"id": 1, "phrase": "hello"}
    captured = capsys.readouterr().out + capsys.readouterr().err
    assert "dimension mismatch" in captured.lower() or "fixture column" in captured.lower()


def test_prepare_record_keeps_vector_column_with_matching_dim(processor: FixtureProcessor) -> None:
    record = {"id": 1, "phrase": "hello", "embedding": [0.0] * 3072}

    prepared = dict(processor.prepare_record(record))

    assert len(prepared["embedding"]) == 3072


def test_prepare_record_does_not_drop_short_non_vector_lists(processor: FixtureProcessor) -> None:
    record = {"id": 1, "tags": ["espresso", "single-origin"]}

    prepared = dict(processor.prepare_record(record))

    assert prepared["tags"] == ["espresso", "single-origin"]


def test_prepare_record_does_not_treat_string_lists_as_vectors(processor: FixtureProcessor) -> None:
    record = {"id": 1, "phrases": ["a"] * 4096}

    prepared = dict(processor.prepare_record(record))

    assert prepared["phrases"] == ["a"] * 4096


def test_prepare_record_skips_columns_without_dim_when_unconfigured(tmp_path: Path) -> None:
    proc = FixtureProcessor(tmp_path)
    record = {"id": 1, "embedding": [0.1] * 768}

    prepared = dict(proc.prepare_record(record))

    assert prepared["embedding"] == [0.1] * 768
