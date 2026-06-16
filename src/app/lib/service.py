# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Service base + filter / pagination facade.

Re-exports the canonical sqlspec service primitives so domain services have a
single import surface. No local subclassing — the inheritance chain stops at
sqlspec's :class:`SQLSpecAsyncService`.
"""

from sqlspec.adapters.oracledb import OracleAsyncDriver
from sqlspec.core.filters import (
    AnyCollectionFilter,
    BeforeAfterFilter,
    FilterTypes,
    FilterTypeT,
    InAnyFilter,
    InCollectionFilter,
    LimitOffsetFilter,
    NotAnyCollectionFilter,
    NotInCollectionFilter,
    NotInSearchFilter,
    OffsetPagination,
    OnBeforeAfterFilter,
    OrderByFilter,
    PaginationFilter,
    SearchFilter,
    StatementFilter,
    apply_filter,
)
from sqlspec.extensions.litestar.providers import create_filter_dependencies
from sqlspec.service import SQLSpecAsyncService, SQLSpecSyncService


class OracleAsyncService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Base class for async services using Oracle."""

    def __init__(self, driver: OracleAsyncDriver) -> None:
        super().__init__(driver)


__all__ = (
    "AnyCollectionFilter",
    "BeforeAfterFilter",
    "FilterTypeT",
    "FilterTypes",
    "InAnyFilter",
    "InCollectionFilter",
    "LimitOffsetFilter",
    "NotAnyCollectionFilter",
    "NotInCollectionFilter",
    "NotInSearchFilter",
    "OffsetPagination",
    "OnBeforeAfterFilter",
    "OracleAsyncService",
    "OrderByFilter",
    "PaginationFilter",
    "SQLSpecAsyncService",
    "SQLSpecSyncService",
    "SearchFilter",
    "StatementFilter",
    "apply_filter",
    "create_filter_dependencies",
)
