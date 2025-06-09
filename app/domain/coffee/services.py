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

from textwrap import dedent
from typing import TYPE_CHECKING, Any

import structlog
from advanced_alchemy.filters import CollectionFilter, LimitOffset
from advanced_alchemy.repository import SQLAlchemyAsyncRepository, SQLAlchemyAsyncSlugRepository
from advanced_alchemy.service import (
    SQLAlchemyAsyncRepositoryService,
)
from sqlalchemy import select

from app.db.models import Company, Inventory, Product, Shop

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = structlog.get_logger()


# EVERYTHING BELOW HERE ARE REGULAR SQLALCHEMY MODELS.
# The logic below is purely for easy CRUD interaction with models
# See: https://github.com/litestar-org/advanced-alchemy


# Company Repository and Service


class CompanyRepository(SQLAlchemyAsyncRepository[Company]):
    model_type = Company


class CompanyService(SQLAlchemyAsyncRepositoryService[Company]):
    """Handles database operations for user roles."""

    repository_type = CompanyRepository


# Product Repository and Service


class ProductRepository(SQLAlchemyAsyncRepository[Product]):
    model_type = Product


class ProductService(SQLAlchemyAsyncRepositoryService[Product]):
    """Handles database operations for user roles."""

    repository_type = ProductRepository


# Shop Repository and Service


class ShopRepository(SQLAlchemyAsyncSlugRepository[Shop]):
    model_type = Shop


class ShopService(SQLAlchemyAsyncRepositoryService[Shop]):
    """Handles database operations for user roles."""

    repository_type = ShopRepository


# Inventory Repository and Service


class InventoryRepository(SQLAlchemyAsyncRepository[Inventory]):
    model_type = Inventory


class InventoryService(SQLAlchemyAsyncRepositoryService[Inventory]):
    """Handles database operations for user roles."""

    repository_type = InventoryRepository
