# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Service base and filter pagination facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlspec.adapters.oracledb import OracleAsyncDriver
from sqlspec.core.filters import FilterTypes, OffsetPagination
from sqlspec.extensions.litestar.providers import create_filter_dependencies
from sqlspec.service import SQLSpecAsyncService

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ("FilterTypes", "OffsetPagination", "OracleAsyncService", "create_filter_dependencies")


class OracleAsyncService(SQLSpecAsyncService[OracleAsyncDriver]):
    """Base class for async services using Oracle."""

    def __init__(self, driver: OracleAsyncDriver) -> None:
        super().__init__(driver)

    async def execute_many(self, statement: Any, parameters: Sequence[Any], *, auto_commit: bool = False) -> Any:
        """Execute a statement across a sequence of parameter sets.

        Args:
            statement: SQL string or statement object to execute.
            parameters: Sequence of bind parameter mappings or tuples.
            auto_commit: Commit the transaction after executing the batch when True.

        Returns:
            Driver execution result.
        """
        result = await self.driver.execute_many(statement, parameters)
        if auto_commit:
            await self.driver.commit()
        return result
