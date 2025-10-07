"""Database utilities using generic fixture infrastructure."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.lib.settings import get_settings
from app.utils.fixtures import FixtureExporter, FixtureLoader

if TYPE_CHECKING:
    from sqlspec.driver import AsyncDriverAdapterBase


# Coffee shop table loading order (respects foreign key dependencies)
COFFEE_SHOP_TABLES = [
    "product",
    "embedding_cache",
    "response_cache",
    "intent_exemplar",
    "search_metric",
]


async def load_fixtures(
    driver: AsyncDriverAdapterBase,
    tables: list[str] | None = None,
) -> dict[str, dict | str]:
    """Load fixture data into database using generic loader.

    Args:
        driver: SQLSpec database driver
        tables: Optional list of specific tables to load

    Returns:
        Dictionary mapping table names to loading results
    """
    settings = get_settings()
    fixtures_dir = Path(settings.db.FIXTURE_PATH)

    loader = FixtureLoader(
        fixtures_dir=fixtures_dir,
        driver=driver,
        table_order=COFFEE_SHOP_TABLES,
    )

    return await loader.load_all_fixtures(specific_tables=tables)


async def export_fixtures(
    driver: AsyncDriverAdapterBase,
    tables: list[str] | None = None,
    output_dir: Path | None = None,
    compress: bool = True,
) -> dict[str, str]:
    """Export database tables to fixture files.

    Args:
        driver: SQLSpec database driver
        tables: Optional list of specific tables to export
        output_dir: Output directory (defaults to fixtures dir)
        compress: Whether to gzip compress output

    Returns:
        Dictionary mapping table names to output paths or error messages
    """
    settings = get_settings()
    fixtures_dir = Path(settings.db.FIXTURE_PATH)

    if output_dir is None:
        output_dir = fixtures_dir

    exporter = FixtureExporter(
        fixtures_dir=fixtures_dir,
        driver=driver,
        table_order=COFFEE_SHOP_TABLES,
    )

    return await exporter.export_all_fixtures(
        tables=tables,
        output_dir=output_dir,
        compress=compress,
    )
