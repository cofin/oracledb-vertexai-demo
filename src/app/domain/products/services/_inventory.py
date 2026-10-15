# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Store product inventory availability service."""

from __future__ import annotations

from app.domain.products.services._stores import StoreService

__all__ = ("InventoryService",)


class InventoryService(StoreService):
    """Service facade for store-level product availability queries."""
