# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Database / data-ops commands for the ``coffee`` CLI.

Imports ``cli`` from ``app.cli.main`` and registers each command with
``@cli.command(...)``. Importing this module side-effects the registration,
so ``app.cli.main:main()`` only needs ``import app.cli.commands`` to wire
everything up.
"""

from __future__ import annotations

import rich_click as click

from app.cli._helpers.cache import clear_application_cache
from app.cli._helpers.database import downgrade_database, upgrade_database
from app.cli._helpers.embeddings import generate_product_embeddings
from app.cli._helpers.fixtures import (
    display_available_tables,
    display_fixture_list,
    export_fixture_data,
    load_fixture_data,
)
from app.cli._helpers.models import show_model_info
from app.cli.main import cli
from app.cli.utils import async_inject

# Service imports must be runtime (not TYPE_CHECKING) because async_inject calls
# get_type_hints() to resolve dependencies against this module's globals.
from app.domain.products.services import ProductService, VertexAIService  # noqa: TC001
from app.domain.system.services import CacheService  # noqa: TC001


@cli.command(name="bulk-embed", help="Generate or refresh product embeddings with Vertex AI.")
@click.option("--batch-size", default=50, show_default=True, help="Number of products to process per batch.")
@click.option("--force", "-f", is_flag=True, help="Re-embed all products, even when embeddings already exist.")
@async_inject
async def bulk_embed_cmd(
    batch_size: int,
    force: bool,
    product_service: ProductService,
    vertex_ai_service: VertexAIService,
) -> None:
    """Generate ``RETRIEVAL_DOCUMENT`` embeddings for product rows."""
    await generate_product_embeddings(batch_size, force, product_service, vertex_ai_service)


@cli.command(name="clear-cache", help="Clear response and embedding cache tables.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@async_inject
async def clear_cache_cmd(force: bool, cache_service: CacheService) -> None:
    """Clear application caches (response_cache + embedding_cache)."""
    await clear_application_cache(force, cache_service)


@cli.command(name="model-info", help="Show information about currently configured AI models.")
@async_inject
async def model_info_cmd(vertex_ai_service: VertexAIService) -> None:  # noqa: RUF029
    """Show information about currently configured AI models."""
    show_model_info(vertex_ai_service)


@cli.command(name="upgrade", help="Upgrade database schema and load fixture data.")
@click.option("--revision", "-r", default="head", show_default=True, help="Target revision")
@click.option("--no-fixtures", is_flag=True, help="Skip fixture loading after migration")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@async_inject
async def upgrade_cmd(
    revision: str,
    no_fixtures: bool,
    dry_run: bool,
) -> None:
    """Upgrade database to a specific revision and optionally load fixtures."""
    await upgrade_database(revision, no_fixtures, dry_run)


@cli.command(name="downgrade", help="Downgrade database to a specific revision.")
@click.option("--revision", "-r", required=True, help="Target revision to downgrade to")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@async_inject
async def downgrade_cmd(revision: str, dry_run: bool) -> None:
    """Downgrade database to a specific revision."""
    await downgrade_database(revision, dry_run)


@cli.command(name="load-fixtures", help="Load application fixture data into the database.")
@click.option("--tables", "-t", help="Comma-separated list of specific tables to load (loads all if not specified)")
@click.option("--list", "list_fixtures", is_flag=True, help="List available fixture files")
@async_inject
async def load_fixtures_cmd(tables: str | None, list_fixtures: bool) -> None:
    """Load application fixture data into the database."""
    if list_fixtures:
        display_fixture_list()
        return

    await load_fixture_data(tables)


@cli.command(name="export-fixtures", help="Export coffee data tables to fixture JSON files.")
@click.option("--tables", "-t", help="Comma-separated list of tables to export. Exports all if omitted.")
@click.option("--output-dir", "-o", help="Custom output directory. Defaults to configured fixtures directory.")
@click.option("--no-compress", is_flag=True, help="Export uncompressed JSON. Default is gzipped.")
@click.option("--list", "list_tables", is_flag=True, help="List available tables for export")
@async_inject
async def export_fixtures_cmd(
    tables: str | None,
    output_dir: str | None,
    no_compress: bool,
    list_tables: bool,
) -> None:
    """Export coffee shop fixture tables for committed demo data."""
    if list_tables:
        display_available_tables()
        return

    await export_fixture_data(tables, output_dir, no_compress)
