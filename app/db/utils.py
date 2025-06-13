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


async def _upsert_companies(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert company records using raw SQL."""
    cursor = conn.cursor()
    try:
        for company in data:
            await cursor.execute(
                """
                MERGE INTO company c
                USING (SELECT :name AS name FROM dual) src
                ON (c.name = src.name)
                WHEN MATCHED THEN
                    UPDATE SET id = c.id  -- Dummy update to trigger updated_at
                WHEN NOT MATCHED THEN
                    INSERT (name)
                    VALUES (:name2)
                """,
                {"name": company["name"], "name2": company["name"]},
            )
        await conn.commit()
    finally:
        cursor.close()


async def _upsert_shops(conn: oracledb.AsyncConnection, data: list[dict[str, Any]]) -> None:
    """Upsert shop records using raw SQL."""
    cursor = conn.cursor()
    try:
        for shop in data:
            await cursor.execute(
                """
                MERGE INTO shop s
                USING (SELECT :name AS name FROM dual) src
                ON (s.name = src.name)
                WHEN MATCHED THEN
                    UPDATE SET
                        address = :address
                WHEN NOT MATCHED THEN
                    INSERT (name, address)
                    VALUES (:name2, :address2)
                """,
                {
                    "name": shop["name"],
                    "name2": shop["name"],
                    "address": shop["address"],
                    "address2": shop["address"],
                },
            )
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
                        product_size = :product_size,
                        description = :description,
                        embedding = :embedding,
                        embedding_generated_on = :embedding_generated_on
                WHEN NOT MATCHED THEN
                    INSERT (company_id, name, current_price, product_size, description,
                            embedding, embedding_generated_on)
                    VALUES (:company_id2, :name2, :current_price2, :product_size2, :description2,
                            :embedding2, :embedding_generated_on2)
                """,
                {
                    "company_id": actual_company_id,
                    "company_id2": actual_company_id,
                    "name": product["name"],
                    "name2": product["name"],
                    "current_price": product["current_price"],
                    "current_price2": product["current_price"],
                    "product_size": product["product_size"],
                    "product_size2": product["product_size"],
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

        # Load inventory
        fixture_data = await open_fixture_async(fixtures_path, "inventory")
        await _upsert_inventory(conn, fixture_data)
        await logger.ainfo("loaded inventory")


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
