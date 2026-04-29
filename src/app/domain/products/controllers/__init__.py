# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Products domain controllers."""

from litestar import Controller

from app.domain.products.controllers._products import ProductController, StoreController
from app.domain.products.controllers._vector import VectorController

controllers: list[type[Controller]] = [ProductController, StoreController, VectorController]

__all__ = ("ProductController", "StoreController", "VectorController", "controllers")
