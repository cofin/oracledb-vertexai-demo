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
                    UPDATE SET updated_at = SYSTIMESTAMP
                WHEN NOT MATCHED THEN
                    INSERT (id, name)
                    VALUES (:id, :name2)
                """,
                {"id": company["id"], "name": company["name"], "name2": company["name"]},
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
                        address = :address,
                        updated_at = SYSTIMESTAMP
                WHEN NOT MATCHED THEN
                    INSERT (id, name, address)
                    VALUES (:id, :name2, :address2)
                """,
                {
                    "id": shop["id"],
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
    cursor = conn.cursor()
    try:
        for product in data:
            # Convert embedding list to array if present
            embedding = product.get("embedding")
            embedding_date = product.get("embedding_generated_on")

            await cursor.execute(
                """
                MERGE INTO product p
                USING (SELECT :name AS name FROM dual) src
                ON (p.name = src.name)
                WHEN MATCHED THEN
                    UPDATE SET
                        company_id = :company_id,
                        current_price = :current_price,
                        "SIZE" = :size,
                        description = :description,
                        embedding = :embedding,
                        embedding_generated_on = :embedding_generated_on,
                        updated_at = SYSTIMESTAMP
                WHEN NOT MATCHED THEN
                    INSERT (id, company_id, name, current_price, "SIZE",
                            description, embedding, embedding_generated_on)
                    VALUES (:id, :company_id2, :name2, :current_price2, :size2,
                            :description2, :embedding2, :embedding_generated_on2)
                """,
                {
                    "id": product["id"],
                    "company_id": product["company_id"],
                    "company_id2": product["company_id"],
                    "name": product["name"],
                    "name2": product["name"],
                    "current_price": product["current_price"],
                    "current_price2": product["current_price"],
                    "size": product["size"],
                    "size2": product["size"],
                    "description": product["description"],
                    "description2": product["description"],
                    "embedding": embedding,
                    "embedding2": embedding,
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
        for inventory in data:
            await cursor.execute(
                """
                MERGE INTO inventory i
                USING (SELECT :shop_id AS shop_id, :product_id AS product_id FROM dual) src
                ON (i.shop_id = src.shop_id AND i.product_id = src.product_id)
                WHEN MATCHED THEN
                    UPDATE SET updated_at = SYSTIMESTAMP
                WHEN NOT MATCHED THEN
                    INSERT (shop_id, product_id)
                    VALUES (:shop_id2, :product_id2)
                """,
                {
                    "shop_id": inventory["shop_id"],
                    "shop_id2": inventory["shop_id"],
                    "product_id": inventory["product_id"],
                    "product_id2": inventory["product_id"],
                },
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
                        embedding_generated_on = SYSTIMESTAMP,
                        updated_at = SYSTIMESTAMP
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
