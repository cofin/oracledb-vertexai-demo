# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Maps integration configuration settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.lib.settings._env import _env_bool

__all__ = ("MapsSettings",)


@dataclass(frozen=True, slots=True)
class MapsSettings:
    """Google Maps integration settings."""

    ENABLE_EMBED: bool = field(default_factory=lambda: _env_bool("MAPS_ENABLE_EMBED", False))
    """Enable optional Google Maps Embed iframe rendering."""
    EMBED_API_KEY: str = field(default_factory=lambda: os.getenv("GOOGLE_MAPS_EMBED_API_KEY", ""))
    """Restricted Google Maps Embed API key. Do not reuse Gemini or Vertex keys."""

    @property
    def embed_enabled(self) -> bool:
        """True only when embed rendering is explicitly enabled and keyed."""
        return self.ENABLE_EMBED and bool(self.EMBED_API_KEY.strip())
