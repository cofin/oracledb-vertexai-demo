# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""High-contrast QR code PNGs for slide resource cards.

QR generation needs the optional ``slides`` dependency group
(``uv sync --group slides``); the rest of the slide tooling works without it.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

__all__ = ["QR_BACKGROUND", "QR_FILL", "write_qr_png"]

QR_FILL = "#212226"
QR_BACKGROUND = "#FFFFFF"


def write_qr_png(url: str, output: Path, *, box_size: int = 12, border: int = 2) -> Path:
    """Write a QR code PNG with high error correction, dark modules on white.

    Args:
        url: Link the QR code opens.
        output: PNG path to write; parent directories are created.
        box_size: Pixels per QR module.
        border: Quiet-zone width in modules.

    Returns:
        The path that was written.

    Raises:
        RuntimeError: If the ``slides`` dependency group is not installed.
    """
    qrcode = _load_qrcode()
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=box_size, border=border)
    code.add_data(url)
    code.make(fit=True)
    image = code.make_image(fill_color=QR_FILL, back_color=QR_BACKGROUND)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


def _load_qrcode() -> ModuleType:
    """Import ``qrcode`` on demand so the other slide commands work without it."""
    try:
        return importlib.import_module("qrcode")
    except ModuleNotFoundError as exc:
        msg = "QR codes need the 'slides' dependency group: run `uv sync --group slides`"
        raise RuntimeError(msg) from exc
