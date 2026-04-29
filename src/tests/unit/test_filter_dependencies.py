# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Filter-dependency wiring tests.

Every list endpoint adopts ``create_filter_dependencies`` and every list
service exposes ``list_with_count(*filters) -> OffsetPagination[T]``.
The tests rely on declarative shape (class attrs, signatures) — no live
database connection required.
"""

from __future__ import annotations

import inspect
from typing import get_args, get_origin

import pytest


def _filter_keys(controller_cls: type) -> set[str]:
    """Return the keys ``create_filter_dependencies`` registered on the controller."""
    deps = getattr(controller_cls, "dependencies", None)
    assert deps is not None, f"{controller_cls.__name__}.dependencies missing"
    return set(deps.keys())


@pytest.mark.parametrize(
    ("controller_path", "expected_keys"),
    [
        ("app.domain.products.controllers.ProductController", {"filters", "limit_offset_filter", "search_filter"}),
        ("app.domain.products.controllers.StoreController", {"filters", "limit_offset_filter", "search_filter"}),
        ("app.domain.system.controllers.ExemplarController", {"filters", "limit_offset_filter", "search_filter"}),
    ],
)
def test_controller_dependencies_include_filter_keys(controller_path: str, expected_keys: set[str]) -> None:
    """``create_filter_dependencies`` must register the canonical filter providers on each list controller."""
    module_path, _, attr = controller_path.rpartition(".")
    module = __import__(module_path, fromlist=[attr])
    controller_cls = getattr(module, attr)

    keys = _filter_keys(controller_cls)
    missing = expected_keys - keys
    assert not missing, f"{attr}.dependencies missing filter keys: {missing}; got {keys}"


@pytest.mark.parametrize(
    ("service_path", "schema_path"),
    [
        ("app.domain.products.services.ProductService", "app.domain.products.schemas.Product"),
        ("app.domain.products.services.StoreService", "app.domain.products.schemas.Store"),
        ("app.domain.system.services.ExemplarService", "app.domain.system.schemas.IntentExemplar"),
    ],
)
def test_service_exposes_list_with_count(service_path: str, schema_path: str) -> None:
    """Each list service must expose ``async list_with_count(*filters) -> OffsetPagination[Schema]``."""
    from sqlspec.core.filters import OffsetPagination

    svc_module_path, _, svc_attr = service_path.rpartition(".")
    schema_module_path, _, schema_attr = schema_path.rpartition(".")
    svc_module = __import__(svc_module_path, fromlist=[svc_attr])
    schema_module = __import__(schema_module_path, fromlist=[schema_attr])

    svc_cls = getattr(svc_module, svc_attr)
    schema_cls = getattr(schema_module, schema_attr)

    method = getattr(svc_cls, "list_with_count", None)
    assert method is not None, f"{svc_attr}.list_with_count is missing"
    assert inspect.iscoroutinefunction(method), f"{svc_attr}.list_with_count must be async"

    sig = inspect.signature(method)
    return_hint = sig.return_annotation
    if isinstance(return_hint, str):
        from typing import get_type_hints

        return_hint = get_type_hints(method).get("return")

    origin = get_origin(return_hint)
    assert origin is OffsetPagination, (
        f"{svc_attr}.list_with_count must return OffsetPagination[...], got {return_hint!r}"
    )
    args = get_args(return_hint)
    assert args and args[0] is schema_cls, (
        f"{svc_attr}.list_with_count must return OffsetPagination[{schema_attr}], got OffsetPagination[{args}]"
    )


def test_exemplar_controller_path_is_api_exemplars() -> None:
    """The explore page consumes ``/api/exemplars``; the path must stay stable."""
    from app.domain.system.controllers import ExemplarController

    assert ExemplarController.path == "/api/exemplars"


def test_product_controller_path_is_api_products() -> None:
    from app.domain.products.controllers import ProductController

    assert ProductController.path == "/api/products"


def test_store_controller_path_is_api_stores() -> None:
    from app.domain.products.controllers import StoreController

    assert StoreController.path == "/api/stores"
