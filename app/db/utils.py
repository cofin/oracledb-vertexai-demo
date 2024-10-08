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


async def load_database_fixtures() -> None:
    """Import/Synchronize Database Fixtures."""

    from advanced_alchemy.utils.fixtures import open_fixture_async
    from structlog import get_logger

    from app.config import alchemy
    from app.domain.coffee.services import CompanyService, InventoryService, ProductService, ShopService
    from app.lib.settings import get_settings

    settings = get_settings()
    logger = get_logger()
    fixtures_path = Path(settings.db.FIXTURE_PATH)
    async with CompanyService.new(config=alchemy) as service:
        fixture_data = await open_fixture_async(fixtures_path, "company")
        await service.upsert_many(match_fields=["name"], data=fixture_data, auto_commit=True)
        await logger.ainfo("loaded companies")
    async with ShopService.new(config=alchemy) as service:
        fixture_data = await open_fixture_async(fixtures_path, "shop")
        await service.upsert_many(match_fields=["name"], data=fixture_data, auto_commit=True)
        await logger.ainfo("loaded shops")
    async with ProductService.new(config=alchemy) as service:
        fixture_data = await open_fixture_async(fixtures_path, "product")
        await service.upsert_many(match_fields=["name"], data=fixture_data, auto_commit=True)
        await logger.ainfo("loaded products")
    async with InventoryService.new(config=alchemy) as service:
        fixture_data = await open_fixture_async(fixtures_path, "inventory")
        await service.upsert_many(match_fields=["shop_id", "product_id"], data=fixture_data, auto_commit=True)
        await logger.ainfo("loaded inventory")
