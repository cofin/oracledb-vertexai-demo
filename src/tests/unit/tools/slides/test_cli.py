# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for word-level deck diffs and the slides CLI."""

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from tools.slides.cli import slides_group
from tools.slides.diff import diff_decks

if TYPE_CHECKING:
    from pathlib import Path


def test_diff_reports_changed_removed_and_added_slides(sample_deck: dict[str, Any]) -> None:
    """Changed words, dropped slides, and new slides are each reported by objectId."""
    new = copy.deepcopy(sample_deck)
    new["slides"][0]["pageElements"][0]["shape"]["text"]["textElements"][1]["textRun"]["content"] = (
        "Vector Search Done Right\n"
    )
    new["slides"].pop(1)
    new["slides"].append({"objectId": "slide_three", "pageElements": []})

    diffs = {entry.object_id: entry for entry in diff_decks(sample_deck, new)}

    assert diffs["slide_one"].status == "changed"
    assert diffs["slide_one"].removed == ("and the Optimizer Rule",)
    assert diffs["slide_one"].added == ("Done Right",)
    assert diffs["slide_two"].status == "removed"
    assert diffs["slide_three"].status == "added"


def test_inventory_lists_slides_and_bridge_summary(deck_file: Path) -> None:
    """The inventory table names every slide and summarizes skip and BRIDGE state."""
    result = CliRunner().invoke(slides_group, ["inventory", str(deck_file)])

    assert result.exit_code == 0, result.output
    assert "slide_one" in result.output
    assert "slide_two" in result.output
    assert "1 shown, 1 skipped" in result.output


def test_inventory_json_output(deck_file: Path) -> None:
    """The JSON inventory carries titles and skip flags."""
    result = CliRunner().invoke(slides_group, ["inventory", str(deck_file), "--json"])

    payload = json.loads(result.output)
    assert payload[0]["title"] == "Vector Search and the Optimizer Rule"
    assert payload[1]["skipped"] is True


def test_validate_exit_codes(tmp_path: Path, deck_file: Path) -> None:
    """Validation exits 1 on errors and 0 on a clean batch, for both file shapes."""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"requests": [{"deleteObject": {"objectId": "no_such_box"}}]}), encoding="utf-8")
    good = tmp_path / "good.json"
    good.write_text(json.dumps([{"deleteObject": {"objectId": "code_one"}}]), encoding="utf-8")

    bad_result = CliRunner().invoke(slides_group, ["validate", str(bad), "--dump", str(deck_file)])
    good_result = CliRunner().invoke(slides_group, ["validate", str(good), "--dump", str(deck_file)])

    assert bad_result.exit_code == 1
    assert "no_such_box" in bad_result.output
    assert good_result.exit_code == 0, good_result.output


def test_highlight_writes_requests_for_the_code_box(tmp_path: Path) -> None:
    """Highlight requests target the given element and drop the file's final newline."""
    code_file = tmp_path / "query.sql"
    code_file.write_text("SELECT 1 FROM dual\n", encoding="utf-8")
    output = tmp_path / "highlight.json"

    result = CliRunner().invoke(
        slides_group, ["highlight", str(code_file), "--element", "code_one", "--output", str(output)]
    )

    assert result.exit_code == 0, result.output
    requests = json.loads(output.read_text(encoding="utf-8"))
    assert requests[0]["updateTextStyle"]["objectId"] == "code_one"
    ends = [request["updateTextStyle"]["textRange"].get("endIndex", 0) for request in requests]
    assert max(ends) <= len("SELECT 1 FROM dual")


def test_qr_writes_a_png(tmp_path: Path) -> None:
    """The qr command writes a PNG when the slides dependency group is installed."""
    pytest.importorskip("qrcode")
    output = tmp_path / "qr" / "repo.png"

    result = CliRunner().invoke(
        slides_group, ["qr", "https://github.com/cofin/oracledb-vertexai-demo", "--output", str(output)]
    )

    assert result.exit_code == 0, result.output
    assert output.read_bytes().startswith(b"\x89PNG")
