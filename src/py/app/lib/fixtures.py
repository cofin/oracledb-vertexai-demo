"""Fixture loading utilities for raw SQL database operations."""

from __future__ import annotations

import gzip
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
    """Load JSON file with the specified fixture name, supporting gzipped files.

    Args:
        fixtures_path: Path to look for fixtures
        fixture_name: The fixture name to load

    Returns:
        Any: The parsed JSON data

    Raises:
        FileNotFoundError: If fixture file doesn't exist
    """
    # Try uppercase gzipped file first (preferred for exported data)
    uppercase_gzipped = AsyncPath(fixtures_path / f"{fixture_name.upper()}.json.gz")
    if await uppercase_gzipped.exists():
        async with await uppercase_gzipped.open(mode="rb") as f:
            compressed_data = await f.read()
        decompressed_data = gzip.decompress(compressed_data)
        return decode_json(decompressed_data)

    # Try lowercase gzipped file
    gzipped_fixture = AsyncPath(fixtures_path / f"{fixture_name}.json.gz")
    if await gzipped_fixture.exists():
        async with await gzipped_fixture.open(mode="rb") as f:
            compressed_data = await f.read()
        decompressed_data = gzip.decompress(compressed_data)
        return decode_json(decompressed_data)

    # Fall back to regular JSON file
    fixture = AsyncPath(fixtures_path / f"{fixture_name}.json")
    if await fixture.exists():
        async with await fixture.open(mode="r", encoding="utf-8") as f:
            f_data = await f.read()
        return decode_json(f_data)

    msg = f"Could not find the {fixture_name} fixture (.json, .json.gz, or {fixture_name.upper()}.json.gz)"
    raise FileNotFoundError(msg)
