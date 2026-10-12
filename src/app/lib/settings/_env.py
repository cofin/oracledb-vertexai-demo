# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Environment parsing helpers and base directory constants for settings."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Final

from litestar.utils.module_loader import module_to_os_path

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ("BASE_DIR", "DEFAULT_MODULE_NAME", "_env_bool", "_env_cors", "_env_float", "_env_int", "_env_str")

DEFAULT_MODULE_NAME = "app"
BASE_DIR: Final[Path] = module_to_os_path(DEFAULT_MODULE_NAME)

_TRUE_VALUES: Final[frozenset[str]] = frozenset({"true", "1", "yes", "y", "t", "on"})


def _env_bool(name: str, default: bool) -> bool:
    """Parse an environment variable as a boolean using a single truth table."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def _env_int(name: str, default: int) -> int:
    """Parse an environment variable as an integer, falling back to the default."""
    raw = os.getenv(name)
    if not raw:
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    """Parse an environment variable as a float, falling back to the default."""
    raw = os.getenv(name)
    if not raw:
        return default
    return float(raw)


def _env_str(name: str, default: str) -> str:
    """Read an environment variable as a string with a default."""
    return os.getenv(name, default)


def _env_cors(name: str, default: str) -> list[str]:
    """Parse an env value into a CORS origin list.

    Accepts a JSON list (``["*"]``) or a comma-separated string (``a.com,b.com``)
    and always returns a ``list[str]``.

    Raises:
        ValueError: If a bracketed value is not valid JSON.
    """
    raw = os.getenv(name, default)
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
        except (SyntaxError, ValueError):
            msg = "ALLOWED_CORS_ORIGINS is not a valid list representation."
            raise ValueError(msg) from None
        return [str(host) for host in parsed]
    return [host.strip() for host in raw.split(",")]
