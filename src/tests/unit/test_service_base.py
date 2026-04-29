# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest
from sqlspec.service import SQLSpecAsyncService as SQLSpecBase


def test_lib_service_reexports_sqlspec_async_service() -> None:
    from app.lib.service import SQLSpecAsyncService

    assert SQLSpecAsyncService is SQLSpecBase


@pytest.mark.parametrize(
    "module_path,class_name",
    [
        ("app.domain.products.services.services", "ProductService"),
        ("app.domain.products.services.services", "StoreService"),
        ("app.domain.system.services.services", "CacheService"),
        ("app.domain.system.services.services", "MetricsService"),
        ("app.domain.chat.services.adk", "AgentToolsService"),
    ],
)
def test_domain_services_subclass_sqlspec_async_service(module_path: str, class_name: str) -> None:
    module = __import__(module_path, fromlist=[class_name])
    cls = getattr(module, class_name)

    assert issubclass(cls, SQLSpecBase), f"{class_name} must subclass sqlspec.service.SQLSpecAsyncService"


def test_lib_service_reexports_filters_and_pagination() -> None:
    from app.lib import service

    for name in (
        "FilterTypes",
        "LimitOffsetFilter",
        "OrderByFilter",
        "SearchFilter",
        "OffsetPagination",
        "PaginationFilter",
        "apply_filter",
    ):
        assert hasattr(service, name), f"app.lib.service must re-export {name}"


def test_lib_service_reexports_create_filter_dependencies() -> None:
    from sqlspec.extensions.litestar.providers import (
        create_filter_dependencies as upstream,
    )

    from app.lib.service import create_filter_dependencies

    assert create_filter_dependencies is upstream


def test_lib_service_no_longer_defines_local_sqlspec_service_class() -> None:
    from app.lib import service

    local = getattr(service, "SQLSpecService", None)
    if local is None:
        return
    assert local is SQLSpecBase, (
        "If SQLSpecService remains, it must be an alias of sqlspec's SQLSpecAsyncService — "
        "no local Generic wrapper allowed."
    )
