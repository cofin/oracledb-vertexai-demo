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

from advanced_alchemy.repository import SQLAlchemyAsyncRepository, SQLAlchemyAsyncSlugRepository

from app.db.models import Company, Inventory, Product, Shop


class CompanyRepository(SQLAlchemyAsyncRepository[Company]):
    model_type = Company


class ProductRepository(SQLAlchemyAsyncRepository[Product]):
    model_type = Product


class ShopRepository(SQLAlchemyAsyncSlugRepository[Shop]):
    model_type = Shop


class InventoryRepository(SQLAlchemyAsyncRepository[Inventory]):
    model_type = Inventory
