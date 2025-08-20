# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import array
import gzip
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import msgspec
from structlog import get_logger

from app import config
from app.lib.fixtures import open_fixture_async
from app.lib.settings import get_settings

if TYPE_CHECKING:
    import oracledb

logger = get_logger()


async def _upsert(
    conn: oracledb.AsyncConnection, table_name: str, data: list[dict[str, Any]], match_on: list[str]
) -> None:
    """Generic upsert function using MERGE.

    Args:
        conn: The database connection.
        table_name: The name of the table to upsert into.
        data: A list of dictionaries representing the rows to upsert.
        match_on: A list of column names to use for matching existing rows.
    """
    if not data:
        return

    async with conn.cursor() as cursor:
        cols = data[0].keys()
        update_cols = [c for c in cols if c not in match_on]

        on_clause = " AND ".join([f"t.{c} = s.{c}" for c in match_on])
        update_clause = ", ".join([f"t.{c} = s.{c}" for c in update_cols])
        insert_cols = ", ".join(cols)
        insert_vals = ", ".join([f":{c}" for c in cols])
        source_cols = ", ".join([f":{c} AS {c}" for c in cols])

        update_sql = f"WHEN MATCHED THEN UPDATE SET {update_clause}" if update_clause else ""

        sql = f"""
            MERGE INTO {table_name} t
            USING (SELECT {source_cols} FROM dual) s
            ON ({on_clause})
            {update_sql}
            WHEN NOT MATCHED THEN
                INSERT ({insert_cols}) VALUES ({insert_vals})"""  # noqa: S608

        await cursor.executemany(sql, data)
        await conn.commit()


async def _upsert_companies(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert company records using a generic upsert function."""
    await _upsert(conn, "company", [{k: v for k, v in c.items() if k in ["name"]} for c in data], ["name"])


async def _upsert_shops(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert shop records using a generic upsert function."""
    await _upsert(conn, "shop", [{k: v for k, v in s.items() if k in ["name", "address"]} for s in data], ["name"])


async def _upsert_products(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert product records using a PL/SQL block with executemany for bulk processing."""

    async with conn.cursor() as cursor:
        await cursor.execute("SELECT id FROM company ORDER BY id")
        company_ids = [row[0] for row in await cursor.fetchall()]
        company_id_map = {i + 1: company_ids[i] for i in range(len(company_ids))}

        products_to_upsert = []
        for product in data:
            product_data = {
                "company_id": company_id_map.get(product["company_id"], product["company_id"]),
                "name": product["name"],
                "current_price": product["current_price"],
                "description": product["description"],
                "embedding": array.array("f", product["embedding"]) if product.get("embedding") else None,
                "embedding_generated_on": product.get("embedding_generated_on"),
            }
            products_to_upsert.append(product_data)

    await _upsert(conn, "product", products_to_upsert, ["name"])


async def _upsert_inventory(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert inventory records using a generic upsert function."""
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT id, name FROM product ORDER BY id")
        products = {row[0]: row[1] for row in await cursor.fetchall()}

        await cursor.execute("SELECT id, name FROM shop ORDER BY id")
        shops = {row[0]: row[1] for row in await cursor.fetchall()}

        shop_id_map = {i + 1: list(shops.keys())[i] for i in range(len(shops))}
        product_list = list(products.keys())
        product_id_map = {}
        if product_list:
            for i, fixture_id in enumerate(range(1, 217)):
                if i < len(product_list):
                    product_id_map[fixture_id] = product_list[i]

        inventory_to_upsert = []
        for inventory in data:
            inventory_data = {
                "shop_id": shop_id_map.get(inventory["shop_id"]),
                "product_id": product_id_map.get(inventory["product_id"]),
            }
            if inventory_data["shop_id"] and inventory_data["product_id"]:
                inventory_to_upsert.append(inventory_data)
            else:
                logger.warning(
                    "Skipping inventory - could not map shop %s or product %s",
                    inventory["shop_id"],
                    inventory["product_id"],
                )

    await _upsert(conn, "inventory", inventory_to_upsert, ["shop_id", "product_id"])


async def _upsert_intent_exemplars(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert intent exemplar records using a generic upsert function."""
    import array

    exemplars_to_upsert = []
    for exemplar in data:
        exemplar_data = {
            "intent": exemplar["intent"],
            "phrase": exemplar["phrase"],
            "embedding": array.array("f", exemplar["embedding"]) if exemplar.get("embedding") else None,
        }
        exemplars_to_upsert.append(exemplar_data)

    await _upsert(conn, "intent_exemplar", exemplars_to_upsert, ["intent", "phrase"])


async def load_database_fixtures() -> None:
    """Import/Synchronize Database Fixtures using raw SQL."""

    settings = get_settings()
    fixtures_path = Path(settings.db.FIXTURE_PATH)

    async with config.oracle_async.get_connection() as conn:
        # Load companies
        fixture_data = await open_fixture_async(fixtures_path, "company")
        await _upsert_companies(conn, fixture_data)
        await logger.ainfo("loaded companies")

        # Load shops
        fixture_data = await open_fixture_async(fixtures_path, "shop")
        await _upsert_shops(conn, fixture_data)
        await logger.ainfo("loaded shops")

        # Load products
        fixture_data = await open_fixture_async(fixtures_path, "product")
        await _upsert_products(conn, fixture_data)
        await logger.ainfo("loaded products")

        # Load exemplars
        fixture_data = await open_fixture_async(fixtures_path, "intent_exemplar")
        await _upsert_intent_exemplars(conn, fixture_data)
        await logger.ainfo("loaded intent exemplars")


async def _load_vectors() -> None:
    """Load vector embeddings for products using Oracle 23AI native vector operations."""
    from app import config
    from app.services.vertex_ai import VertexAIService

    vertex_ai = VertexAIService()

    async with config.oracle_async.get_connection() as conn:
        cursor = conn.cursor()
        try:
            # Get all products without embeddings
            await cursor.execute(
                """
                SELECT id, name, description
                FROM product
                WHERE embedding IS NULL
                """
            )

            products = [{"id": row[0], "name": row[1], "description": row[2]} async for row in cursor]
            for product in products:
                text_content = f"{product['name']}: {product['description']}"
                embedding = await vertex_ai.create_embedding(text_content)

                # Use Oracle 23AI native vector operations
                await cursor.execute(
                    """
                    UPDATE product
                    SET embedding = :embedding,
                        embedding_generated_on = SYSTIMESTAMP
                    WHERE id = :id
                    """,
                    {"id": product["id"], "embedding": embedding},
                )

                logger.info(
                    "Generated embedding for product",
                    product_id=product["id"],
                    product_name=product["name"],
                )
            await conn.commit()
            logger.info("Vector embeddings loaded successfully")
        finally:
            cursor.close()


async def export_table_data(  # noqa: C901
    conn: oracledb.AsyncConnection,
    table_name: str,
    export_path: Path,
    compress: bool = True,
) -> int:
    """Export a single table to JSON file with optional compression.

    Args:
        conn: Database connection
        table_name: Name of table to export
        export_path: Directory to export to
        compress: Whether to gzip the output

    Returns:
        Number of records exported
    """

    cursor = conn.cursor()
    try:
        # Validate table name to prevent SQL injection
        valid_tables = [
            "COMPANY",
            "SHOP",
            "PRODUCT",
            "INVENTORY",
            "INTENT_EXEMPLAR",
            "APP_CONFIG",
        ]
        if table_name.upper() not in valid_tables:
            msg = f"Invalid table name: {table_name}"
            raise ValueError(msg)

        # Validate table name to prevent SQL injection
        valid_tables = [
            "COMPANY",
            "SHOP",
            "PRODUCT",
            "INVENTORY",
            "INTENT_EXEMPLAR",
            "APP_CONFIG",
        ]
        if table_name.upper() not in valid_tables:
            msg = f"Invalid table name: {table_name}"
            raise ValueError(msg)

        # Validate table name to prevent SQL injection
        valid_tables = [
            "COMPANY",
            "SHOP",
            "PRODUCT",
            "INVENTORY",
            "INTENT_EXEMPLAR",
            "APP_CONFIG",
        ]
        if table_name.upper() not in valid_tables:
            msg = f"Invalid table name: {table_name}"
            raise ValueError(msg)

        # Get all data from the table
        # TODO: Consider using streaming/pagination for very large tables  # noqa: FIX002
        await cursor.execute(f"SELECT * FROM {table_name}")  # noqa: S608

        # Get column names
        columns = [col[0].lower() for col in cursor.description]

        # Fetch all rows and convert to dictionaries
        # TODO: Stream rows to file instead of loading all into memory for large tables  # noqa: FIX002
        rows = []
        async for row in cursor:
            row_dict = {}
            for i, value in enumerate(row):
                col_name = columns[i]

                # Handle special Oracle types including Oracle 23AI VECTOR
                if isinstance(value, array.array):
                    # Convert Oracle VECTOR to list for JSON serialization
                    row_dict[col_name] = list(value)
                elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                    # Handle other Oracle vector types that might be returned
                    try:
                        row_dict[col_name] = list(value)
                    except (TypeError, ValueError):
                        row_dict[col_name] = str(value)  # type: ignore[assignment]
                elif isinstance(value, datetime):
                    # Convert datetime to ISO format
                    row_dict[col_name] = value.isoformat()  # type: ignore[assignment]
                elif value is None:
                    # Skip None values for cleaner JSON
                    continue
                else:
                    row_dict[col_name] = value

            rows.append(row_dict)

        # Serialize with msgspec
        # TODO: Consider streaming JSON encoder for very large datasets  # noqa: FIX002
        json_data = msgspec.json.encode(rows)

        # Write to file
        export_path.mkdir(parents=True, exist_ok=True)
        file_name = f"{table_name}.json"
        if compress:
            file_name += ".gz"

        file_path = export_path / file_name

        if compress:
            # Write compressed
            with gzip.open(file_path, "wb") as f:
                f.write(json_data)
        else:
            # Write uncompressed
            file_path.write_bytes(json_data)

        logger.info("Exported %d records from %s to %s", len(rows), table_name, file_path)
        return len(rows)

    finally:
        cursor.close()


async def dump_database_data(
    export_path: Path | str = "exported_data",
    tables: str | list[str] = "*",
    compress: bool = True,
) -> dict[str, int]:
    """Export database tables to JSON files.

    Args:
        export_path: Directory to export files to
        tables: Table name(s) to export, or "*" for all tables
        compress: Whether to gzip the output files

    Returns:
        Dictionary mapping table names to record counts
    """

    export_path = Path(export_path)

    async with config.oracle_async.get_connection() as conn:
        cursor = conn.cursor()
        try:
            # Get list of tables to export
            if tables == "*":
                # Get all user tables
                # TODO: Consider caching table list or making configurable  # noqa: FIX002
                # For demo purposes, only export essential tables
                # TODO: Remove this filter for production use to export all tables  # noqa: FIX002
                await cursor.execute("""
                    SELECT table_name
                    FROM user_tables
                    WHERE table_name IN ('COMPANY', 'INTENT_EXEMPLAR', 'PRODUCT', 'SHOP')
                    ORDER BY table_name
                """)
                table_list: list[str] = [row[0] for row in await cursor.fetchall()]
            elif isinstance(tables, str):
                table_list = [tables.upper()]
            else:
                table_list = [t.upper() for t in tables]

            # Export each table
            # TODO: Consider parallel exports for multiple tables  # noqa: FIX002
            results = {}
            for table_name in table_list:
                try:
                    count = await export_table_data(conn, table_name, export_path, compress)
                    results[table_name] = count
                except ValueError:
                    logger.exception("Invalid table name: %s", table_name)
                    results[table_name] = -1
                except Exception:
                    logger.exception("Failed to export table: %s", table_name)
                    results[table_name] = -1

            logger.info("Export complete. Exported %d tables to %s", len(results), export_path)
            return results

        finally:
            cursor.close()
