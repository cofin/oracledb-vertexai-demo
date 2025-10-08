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

"""Base service module following SQLSpec patterns."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, TypeVar, cast

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
from sqlspec.driver import AsyncDriverAdapterBase
from sqlspec.typing import ModelDTOT, StatementParameters

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

    from sqlspec import QueryBuilder, Statement, StatementConfig

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
    "OrderByFilter",
    "PaginationFilter",
    "SQLSpecService",
    "SearchFilter",
    "StatementFilter",
    "apply_filter",
)

T = TypeVar("T")
AsyncDriverT = TypeVar("AsyncDriverT", bound=AsyncDriverAdapterBase)


class SQLSpecService:
    """Base service class for SQLSpec operations."""

    def __init__(self, driver: AsyncDriverAdapterBase) -> None:
        """Initialize the service."""
        self.driver = driver

    async def paginate(
        self,
        statement: Statement | QueryBuilder,
        /,
        *parameters: StatementParameters | StatementFilter,
        schema_type: type[ModelDTOT],
        statement_config: StatementConfig | None = None,
        **kwargs: Any,
    ) -> OffsetPagination[ModelDTOT]:
        """Paginate the data."""
        results, total = await self.driver.select_with_total(
            statement,
            *parameters,
            schema_type=schema_type,
            statement_config=statement_config,
            **kwargs,
        )
        limit_offset = self.find_filter(LimitOffsetFilter, parameters)
        offset = limit_offset.offset if limit_offset else 0
        limit = limit_offset.limit if limit_offset else 10
        return OffsetPagination[ModelDTOT](items=results, limit=limit, offset=offset, total=total)

    async def get_or_404(
        self,
        statement: Statement | QueryBuilder,
        /,
        *parameters: StatementParameters,
        schema_type: type[ModelDTOT],
        error_message: str | None = None,
        statement_config: StatementConfig | None = None,
        **kwargs: Any,
    ) -> ModelDTOT:
        """Get a single record or raise 404 error if not found.

        Args:
            statement: The SQL statement to execute
            *parameters: Statement parameters
            schema_type: The schema type for the result
            error_message: Custom error message (optional)
            statement_config: Optional statement configuration
            **kwargs: Additional keyword arguments

        Returns:
            The found record

        Raises:
            ValueError: If no record is found
        """
        result = await self.driver.select_one_or_none(
            statement,
            *parameters,
            schema_type=schema_type,
            statement_config=statement_config,
            **kwargs,
        )
        if result is None:
            raise ValueError(error_message or "Record not found")
        return result

    async def exists(
        self,
        statement: Statement | QueryBuilder,
        /,
        *parameters: StatementParameters,
        statement_config: StatementConfig | None = None,
        **kwargs: Any,
    ) -> bool:
        """Check if a record exists.

        Args:
            statement: The SQL statement to execute
            *parameters: Statement parameters
            statement_config: Optional statement configuration
            **kwargs: Additional keyword arguments

        Returns:
            True if record exists, False otherwise
        """
        result = await self.driver.select_one_or_none(
            statement,
            *parameters,
            statement_config=statement_config,
            **kwargs,
        )
        return result is not None

    @staticmethod
    def find_filter(
        filter_type: type[FilterTypeT],
        filters: Sequence[StatementFilter | StatementParameters] | Sequence[StatementFilter],
    ) -> FilterTypeT | None:
        """Get the filter specified by filter type from the filters.

        Args:
            filter_type: The type of filter to find.
            filters: filter types to apply to the query

        Returns:
            The match filter instance or None
        """
        return next(
            (cast("FilterTypeT | None", filter_) for filter_ in filters if isinstance(filter_, filter_type)),
            None,
        )

    async def begin(self) -> None:
        """Begin a database transaction."""
        await self.driver.begin()

    async def commit(self) -> None:
        """Commit the current database transaction."""
        await self.driver.commit()

    async def rollback(self) -> None:
        """Rollback the current database transaction."""
        await self.driver.rollback()

    @asynccontextmanager
    async def begin_transaction(self) -> AsyncIterator[None]:
        """Context manager for database transactions."""
        await self.begin()
        try:
            yield
        except Exception:
            await self.rollback()
            raise
        else:
            await self.commit()
