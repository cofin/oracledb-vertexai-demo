# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Products domain controllers."""

from litestar import Controller

from app.domain.products.controllers._apex import ApexController
from app.domain.products.controllers._products import ProductController, StoreController
from app.domain.products.controllers._vector import VectorController

controllers: list[type[Controller]] = [ProductController, StoreController, VectorController, ApexController]

__all__ = ("ApexController", "ProductController", "StoreController", "VectorController", "controllers")
