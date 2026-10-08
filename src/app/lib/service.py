# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Service base and filter pagination facade."""

from sqlspec.adapters.oracledb import OracleAsyncDriver
from sqlspec.core.filters import FilterTypes, OffsetPagination
from sqlspec.extensions.litestar.providers import create_filter_dependencies
from sqlspec.service import SQLSpecAsyncService


class OracleAsyncService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Base class for async services using Oracle."""

    def __init__(self, driver: OracleAsyncDriver) -> None:
        super().__init__(driver)


__all__ = ("FilterTypes", "OffsetPagination", "OracleAsyncService", "create_filter_dependencies")
