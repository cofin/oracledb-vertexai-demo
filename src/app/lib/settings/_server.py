# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Granian HTTP server and Vite frontend bundle settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from litestar_vite import PathConfig, TypeGenConfig, ViteConfig

from app.lib.settings._env import BASE_DIR, _env_bool, _env_int

__all__ = ("ServerSettings", "ViteSettings")


@dataclass(frozen=True)
class ServerSettings:
    """Granian HTTP server configuration settings."""

    HOST: str = field(default_factory=lambda: os.getenv("LITESTAR_HOST", "127.0.0.1"))
    """Bind host for the Granian server."""
    PORT: int = field(default_factory=lambda: _env_int("LITESTAR_PORT", 8000))
    """Bind port for the Granian server."""
    RELOAD: bool = field(default_factory=lambda: _env_bool("LITESTAR_RELOAD", False))
    """Enable live reload in development."""
    WORKERS: int = field(default_factory=lambda: _env_int("WEB_CONCURRENCY", 1))
    """Number of Granian worker processes."""


@dataclass(frozen=True)
class ViteSettings:
    """Vite configuration settings."""

    DEV_MODE: bool = field(default_factory=lambda: _env_bool("VITE_DEV_MODE", False))
    """Enable Vite dev server mode."""
    BUNDLE_DIR: Path = field(
        default_factory=lambda: Path(os.getenv("VITE_BUNDLE_DIR", str(BASE_DIR / "domain" / "web" / "static")))
    )
    """Vite bundle directory."""

    def get_config(self) -> ViteConfig:
        """Build the Vite plugin configuration.

        Returns:
            A ``ViteConfig`` whose paths match ``src/resources/vite.config.ts``.
        """
        return ViteConfig(
            mode="htmx",
            dev_mode=self.DEV_MODE,
            types=TypeGenConfig(
                output=Path("generated"),
                generate_sdk=False,
                generate_routes=False,
                generate_schemas=False,
                generate_page_props=False,
            ),
            paths=PathConfig(
                root=BASE_DIR.parent / "resources",
                resource_dir=Path(),
                bundle_dir=self.BUNDLE_DIR,
                static_dir=Path("public"),
                asset_url="/static/",
            ),
        )
