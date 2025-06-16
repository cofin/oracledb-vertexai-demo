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

from pathlib import Path
from typing import TYPE_CHECKING, Any

from structlog import get_logger

from app.lib.fixtures import open_fixture_async

if TYPE_CHECKING:
    import oracledb

logger = get_logger()


async def _merge_one(cursor: oracledb.AsyncCursor, sql: str, params: dict[str, Any]) -> None:
    """Execute a single MERGE statement."""
    await cursor.execute(sql, params)


async def _upsert_companies(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert company records using raw SQL."""
    cursor = conn.cursor()
    sql = """
        MERGE INTO company c
        USING (SELECT :name AS name FROM dual) src
        ON (c.name = src.name)
        WHEN MATCHED THEN
            UPDATE SET id = c.id  -- Dummy update to trigger updated_at
        WHEN NOT MATCHED THEN
            INSERT (name)
            VALUES (:name2)
        """
    try:
        for company in data:
            params = {"name": company["name"], "name2": company["name"]}
            await _merge_one(cursor, sql, params)
        await conn.commit()
    finally:
        cursor.close()


async def _upsert_shops(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert shop records using raw SQL."""
    cursor = conn.cursor()
    sql = """
        MERGE INTO shop s
        USING (SELECT :name AS name FROM dual) src
        ON (s.name = src.name)
        WHEN MATCHED THEN
            UPDATE SET
                address = :address
        WHEN NOT MATCHED THEN
            INSERT (name, address)
            VALUES (:name2, :address2)
        """
    try:
        for shop in data:
            params = {
                "name": shop["name"],
                "name2": shop["name"],
                "address": shop["address"],
                "address2": shop["address"],
            }
            await _merge_one(cursor, sql, params)
        await conn.commit()
    finally:
        cursor.close()


async def _upsert_products(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert product records using raw SQL."""
    import array

    cursor = conn.cursor()
    try:
        # Get mapping of company IDs
        await cursor.execute("SELECT id FROM company ORDER BY id")
        company_ids = [row[0] async for row in cursor]

        # Map fixture company IDs (1,2,3...) to actual IDs
        company_id_map = {i + 1: company_ids[i] for i in range(len(company_ids))}

        for product in data:
            # Convert embedding list to Oracle array if present
            embedding = product.get("embedding")
            embedding_date = product.get("embedding_generated_on")

            oracle_embedding = array.array("f", embedding) if embedding else None

            # Map fixture company_id to actual ID
            actual_company_id = company_id_map.get(product["company_id"], product["company_id"])

            await cursor.execute(
                """
                MERGE INTO product p
                USING (SELECT :name AS name FROM dual) src
                ON (p.name = src.name)
                WHEN MATCHED THEN
                    UPDATE SET
                        company_id = :company_id,
                        current_price = :current_price,
                        description = :description,
                        embedding = :embedding,
                        embedding_generated_on = :embedding_generated_on
                WHEN NOT MATCHED THEN
                    INSERT (company_id, name, current_price, description,
                            embedding, embedding_generated_on)
                    VALUES (:company_id2, :name2, :current_price2, :description2,
                            :embedding2, :embedding_generated_on2)
                """,
                {
                    "company_id": actual_company_id,
                    "company_id2": actual_company_id,
                    "name": product["name"],
                    "name2": product["name"],
                    "current_price": product["current_price"],
                    "current_price2": product["current_price"],
                    "description": product["description"],
                    "description2": product["description"],
                    "embedding": oracle_embedding,
                    "embedding2": oracle_embedding,
                    "embedding_generated_on": embedding_date,
                    "embedding_generated_on2": embedding_date,
                },
            )
        await conn.commit()
    finally:
        cursor.close()


async def _upsert_inventory(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert inventory records using raw SQL."""
    cursor = conn.cursor()
    try:
        # Create a mapping of old IDs to actual IDs
        # First, get all products and shops with their IDs
        await cursor.execute("SELECT id, name FROM product ORDER BY id")
        products = {row[0]: row[1] async for row in cursor}

        await cursor.execute("SELECT id, name FROM shop ORDER BY id")
        shops = {row[0]: row[1] async for row in cursor}

        # For the fixtures, we'll use a simple mapping based on order
        # The fixtures use IDs starting from 1 for shops and specific IDs for products
        shop_id_map = {i + 1: list(shops.keys())[i] for i in range(len(shops))}

        # For products, we have 216 products with fixture IDs 1-216
        # Map them 1:1 to the actual IDENTITY column values
        product_list = list(products.keys())
        product_id_map = {}
        if product_list:
            # Map fixture product IDs 1-216 to actual sequential IDs
            for i, fixture_id in enumerate(range(1, 217)):
                if i < len(product_list):
                    product_id_map[fixture_id] = product_list[i]

        for inventory in data:
            fixture_shop_id = inventory["shop_id"]
            fixture_product_id = inventory["product_id"]

            # Map fixture IDs to actual IDs
            actual_shop_id = shop_id_map.get(fixture_shop_id)
            actual_product_id = product_id_map.get(fixture_product_id)

            if actual_shop_id and actual_product_id:
                await cursor.execute(
                    """
                    MERGE INTO inventory i
                    USING (SELECT :shop_id AS shop_id, :product_id AS product_id FROM dual) src
                    ON (i.shop_id = src.shop_id AND i.product_id = src.product_id)
                    WHEN MATCHED THEN
                        UPDATE SET id = i.id  -- Dummy update to trigger updated_at
                    WHEN NOT MATCHED THEN
                        INSERT (shop_id, product_id)
                        VALUES (:shop_id2, :product_id2)
                    """,
                    {
                        "shop_id": actual_shop_id,
                        "shop_id2": actual_shop_id,
                        "product_id": actual_product_id,
                        "product_id2": actual_product_id,
                    },
                )
            else:
                logger.warning(
                    "Skipping inventory - could not map shop %s or product %s", fixture_shop_id, fixture_product_id
                )

        await conn.commit()
    finally:
        cursor.close()


async def _upsert_intent_exemplars(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert intent exemplar records using raw SQL."""
    import array

    cursor = conn.cursor()
    sql = """
        MERGE INTO intent_exemplar ie
        USING (SELECT :intent AS intent, :phrase AS phrase FROM dual) src
        ON (ie.intent = src.intent AND ie.phrase = src.phrase)
        WHEN MATCHED THEN
            UPDATE SET
                embedding = :embedding
        WHEN NOT MATCHED THEN
            INSERT (intent, phrase, embedding)
            VALUES (:intent2, :phrase2, :embedding2)
        """
    try:
        for exemplar in data:
            # Convert embedding list to Oracle array if present
            embedding = exemplar.get("embedding")
            oracle_embedding = array.array("f", embedding) if embedding else None
            params = {
                "intent": exemplar["intent"],
                "intent2": exemplar["intent"],
                "phrase": exemplar["phrase"],
                "phrase2": exemplar["phrase"],
                "embedding": oracle_embedding,
                "embedding2": oracle_embedding,
            }
            await _merge_one(cursor, sql, params)
        await conn.commit()
    finally:
        cursor.close()


async def load_database_fixtures() -> None:
    """Import/Synchronize Database Fixtures using raw SQL."""
    from app import config
    from app.lib.settings import get_settings

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
    """Load vector embeddings for products using raw SQL."""
    import array

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

                # Convert to Oracle VECTOR format
                oracle_vector = array.array("f", embedding)
                await cursor.execute(
                    """
                    UPDATE product
                    SET embedding = :embedding,
                        embedding_generated_on = SYSTIMESTAMP
                    WHERE id = :id
                    """,
                    {"id": product["id"], "embedding": oracle_vector},
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


async def export_table_data(
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
    import array
    import gzip
    from datetime import datetime

    import msgspec

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

        # Get all data from the table
        # TODO: Consider using streaming/pagination for very large tables
        await cursor.execute(f"SELECT * FROM {table_name}")  # noqa: S608

        # Get column names
        columns = [col[0].lower() for col in cursor.description]

        # Fetch all rows and convert to dictionaries
        # TODO: Stream rows to file instead of loading all into memory for large tables
        rows = []
        async for row in cursor:
            row_dict = {}
            for i, value in enumerate(row):
                col_name = columns[i]

                # Handle special Oracle types
                if isinstance(value, array.array):
                    # Convert Oracle VECTOR to list
                    row_dict[col_name] = list(value)
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
        # TODO: Consider streaming JSON encoder for very large datasets
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
    from app import config

    export_path = Path(export_path)

    async with config.oracle_async.get_connection() as conn:
        cursor = conn.cursor()
        try:
            # Get list of tables to export
            if tables == "*":
                # Get all user tables
                # TODO: Consider caching table list or making configurable
                # For demo purposes, only export essential tables
                # TODO: Remove this filter for production use to export all tables
                await cursor.execute("""
                    SELECT table_name
                    FROM user_tables
                    WHERE table_name IN ('COMPANY', 'INTENT_EXEMPLAR', 'PRODUCT', 'SHOP')
                    ORDER BY table_name
                """)
                table_list = [row[0] for row in await cursor.fetchall()]
            elif isinstance(tables, str):
                table_list = [tables.upper()]
            else:
                table_list = [t.upper() for t in tables]

            # Export each table
            # TODO: Consider parallel exports for multiple tables
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
