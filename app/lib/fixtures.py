"""Fixture loading utilities for raw SQL database operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from anyio import Path as AsyncPath
from msgspec import json as msgspec_json
from structlog import get_logger

if TYPE_CHECKING:
    from pathlib import Path

_decoder = msgspec_json.Decoder()
decode_json = _decoder.decode

logger = get_logger()


async def open_fixture_async(fixtures_path: Path | AsyncPath, fixture_name: str) -> Any:
    """Load JSON file with the specified fixture name.

    Args:
        fixtures_path: Path to look for fixtures
        fixture_name: The fixture name to load

    Returns:
        Any: The parsed JSON data

    Raises:
        FileNotFoundError: If fixture file doesn't exist
    """
    fixture = AsyncPath(fixtures_path / f"{fixture_name}.json")
    if await fixture.exists():
        async with await fixture.open(mode="r", encoding="utf-8") as f:
            f_data = await f.read()
        return decode_json(f_data)
    msg = f"Could not find the {fixture_name} fixture"
    raise FileNotFoundError(msg)

