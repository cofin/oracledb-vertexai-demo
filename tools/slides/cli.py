# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""``manage.py slides`` commands for building and checking presentation batches offline.

The commands read presentation JSON dumps and ``batchUpdate`` request files.
They never call the Slides API: fetch dumps and apply batches with whatever
Slides tooling is configured for your environment.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import rich_click as click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from tools.slides.deck import load_deck, summarize_slides
from tools.slides.diff import diff_decks
from tools.slides.highlight import LANGUAGES, highlight_code_requests
from tools.slides.qr import write_qr_png
from tools.slides.validate import DEFAULT_MAX_TITLE_CHARS, validate_requests

if TYPE_CHECKING:
    from tools.slides.deck import SlideSummary

__all__ = ["diff_command", "highlight_command", "inventory_command", "qr_command", "slides_group", "validate_command"]

console = Console()

EXISTING_FILE = click.Path(exists=True, dir_okay=False)
OUTPUT_FILE = click.Path(dir_okay=False)


@click.group(name="slides")
def slides_group() -> None:
    """Build and check Google Slides batches offline.

    Reads presentation JSON dumps and batchUpdate request files. Nothing here
    calls the Slides API; fetch dumps and apply batches with the Slides tooling
    configured for your environment.
    """


@slides_group.command(name="inventory")
@click.argument("dump", type=EXISTING_FILE)
@click.option("--text", "show_text", is_flag=True, help="Also print every text element and the speaker notes.")
@click.option("--json", "as_json", is_flag=True, help="Print the inventory as JSON.")
def inventory_command(dump: str, show_text: bool, as_json: bool) -> None:
    """List slides with skip state, detected title, and BRIDGE status."""
    summaries = summarize_slides(load_deck(Path(dump)))
    if as_json:
        click.echo(json.dumps([_summary_payload(summary) for summary in summaries], indent=2))
        return
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", justify="right")
    table.add_column("objectId", no_wrap=True)
    table.add_column("Skip")
    table.add_column("Bridge")
    table.add_column("Title")
    for summary in summaries:
        table.add_row(
            str(summary.index),
            Text(summary.object_id),
            "yes" if summary.skipped else "",
            "yes" if summary.has_bridge else "",
            Text(summary.title),
        )
    console.print(table)
    if show_text:
        for summary in summaries:
            _print_slide_text(summary)
    shown = [summary for summary in summaries if not summary.skipped]
    missing = [str(summary.index) for summary in shown if not summary.has_bridge]
    console.print(
        Text(
            f"{len(shown)} shown, {len(summaries) - len(shown)} skipped; "
            f"shown slides without a BRIDGE line: {', '.join(missing) or 'none'}"
        )
    )


@slides_group.command(name="validate")
@click.argument("requests_file", type=EXISTING_FILE)
@click.option("--dump", "dump_file", required=True, type=EXISTING_FILE, help="Fresh dump of the target deck.")
@click.option(
    "--max-title", default=DEFAULT_MAX_TITLE_CHARS, show_default=True, help="Maximum title length in characters."
)
def validate_command(requests_file: str, dump_file: str, max_title: int) -> None:
    """Check a batchUpdate request file against a presentation dump.

    Exits with status 1 when any error is found.
    """
    requests = _load_requests(Path(requests_file))
    issues = validate_requests(requests, load_deck(Path(dump_file)), max_title_chars=max_title)
    for issue in issues:
        style = "red" if issue.severity == "error" else "yellow"
        console.print(Text(f"{issue.severity.upper()} request[{issue.index}]: {issue.message}", style=style))
    errors = sum(1 for issue in issues if issue.severity == "error")
    console.print(Text(f"{len(requests)} requests checked: {errors} errors, {len(issues) - errors} warnings"))
    if errors:
        raise SystemExit(1)


@slides_group.command(name="diff")
@click.argument("old_dump", type=EXISTING_FILE)
@click.argument("new_dump", type=EXISTING_FILE)
def diff_command(old_dump: str, new_dump: str) -> None:
    """Show word-level text and notes changes between two dumps, matched by slide objectId."""
    diffs = diff_decks(load_deck(Path(old_dump)), load_deck(Path(new_dump)))
    if not diffs:
        console.print("No text or speaker-notes changes.")
        return
    for entry in diffs:
        console.print(Text(f"{entry.status.upper()} {entry.object_id}", style="bold"))
        for phrase in entry.removed:
            console.print(Text(f"  - {phrase}", style="red"))
        for phrase in entry.added:
            console.print(Text(f"  + {phrase}", style="green"))


@slides_group.command(name="highlight")
@click.argument("code_file", type=EXISTING_FILE)
@click.option("--element", "object_id", required=True, help="objectId of the code text box.")
@click.option("--language", type=click.Choice(LANGUAGES), default="oracle", show_default=True)
@click.option("--output", type=OUTPUT_FILE, default=None, help="Write the requests here instead of stdout.")
def highlight_command(code_file: str, object_id: str, language: str, output: str | None) -> None:
    """Emit updateTextStyle requests that syntax-highlight a code card.

    The file's final newline is dropped. Insert exactly the same text into the
    code box, because ranges are UTF-16 offsets into that text.
    """
    code = Path(code_file).read_text(encoding="utf-8").removesuffix("\n")
    payload = json.dumps(highlight_code_requests(object_id, code, language), indent=2)
    if output is None:
        click.echo(payload)
        return
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{payload}\n", encoding="utf-8")
    console.print(Text(f"Wrote {target}"))


@slides_group.command(name="qr")
@click.argument("url")
@click.option("--output", required=True, type=OUTPUT_FILE, help="PNG file to write.")
def qr_command(url: str, output: str) -> None:
    """Write a high-contrast QR code PNG for a resource card."""
    try:
        path = write_qr_png(url, Path(output))
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    console.print(Text(f"Wrote {path}"))


def _load_requests(path: Path) -> list[dict[str, Any]]:
    """Read a request list or a ``{"requests": [...]}`` batchUpdate body."""
    data = json.loads(path.read_text(encoding="utf-8"))
    requests = data.get("requests") if isinstance(data, dict) else data
    if not isinstance(requests, list):
        msg = f"{path} must contain a list of requests or an object with a 'requests' list"
        raise click.ClickException(msg)
    return requests


def _summary_payload(summary: SlideSummary) -> dict[str, Any]:
    """Return the JSON form of a slide summary."""
    return {
        "index": summary.index,
        "object_id": summary.object_id,
        "skipped": summary.skipped,
        "title": summary.title,
        "has_bridge": summary.has_bridge,
        "texts": list(summary.texts),
        "notes": summary.notes,
    }


def _print_slide_text(summary: SlideSummary) -> None:
    """Print every text element and the notes of one slide."""
    console.rule(Text(f"#{summary.index} {summary.object_id}"))
    for text in summary.texts:
        console.print(Text(text))
    if summary.notes:
        console.print(Text(f"NOTES: {summary.notes}", style="dim"))
