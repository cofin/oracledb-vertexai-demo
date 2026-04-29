"""CLI commands for the application."""

from app.cli.commands import (
    bulk_embed_cmd,
    clear_cache_cmd,
    export_fixtures_cmd,
    load_fixtures_cmd,
    model_info_cmd,
)

__all__ = (
    "bulk_embed_cmd",
    "clear_cache_cmd",
    "export_fixtures_cmd",
    "load_fixtures_cmd",
    "model_info_cmd",
)
