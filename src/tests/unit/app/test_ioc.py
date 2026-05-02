# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Architectural tests for the Dishka container shape."""

from __future__ import annotations

import inspect


def test_make_litestar_container_resolves_expected_types() -> None:
    """`make_container(LitestarProvider())` builds a container with persistence + integration + domain types."""
    from sqlspec.adapters.oracledb import OracleAsyncConfig, OracleAsyncDriver
    from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore

    from app.domain.products.services.services import ProductService
    from app.ioc import make_container
    from app.lib.di import LitestarProvider

    container = make_container(LitestarProvider())
    registered_types: set[type] = set()
    registry = container.registry
    while registry is not None:
        registered_types.update(key.type_hint for key in registry.factories)
        registry = getattr(registry, "child_registry", None)

    for cls in (OracleAsyncConfig, OracleAsyncDriver, OracleAsyncADKStore, ProductService):
        assert cls in registered_types, f"{cls.__name__} factory missing from container registry chain"


def test_ioc_module_does_not_use_future_annotations() -> None:
    """Dishka providers break under PEP 563 — the spec calls this out explicitly."""
    import ast

    import app.ioc as ioc_module

    tree = ast.parse(inspect.getsource(ioc_module))
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            names = ", ".join(alias.name for alias in node.names)
            msg = (
                f"src/py/app/ioc.py imports __future__ feature(s) ({names}) — "
                "Dishka @provide methods need eager annotation evaluation. Remove this import."
            )
            raise AssertionError(msg)
