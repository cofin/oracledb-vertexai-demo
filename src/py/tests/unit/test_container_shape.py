"""Container shape tests for the 3-provider Dishka collapse (Ch 2.3)."""

from __future__ import annotations

import inspect

from dishka import Provider, Scope


def test_ioc_exposes_three_user_providers() -> None:
    """`PROVIDERS` tuple lists exactly three user-defined provider classes."""
    from app.ioc import PROVIDERS

    assert len(PROVIDERS) == 3, f"expected 3 user providers, found {len(PROVIDERS)}: {PROVIDERS}"
    for cls in PROVIDERS:
        assert isinstance(cls, type) and issubclass(cls, Provider), f"{cls!r} is not a Provider subclass"


def test_ioc_provider_classes_have_expected_names() -> None:
    """Naming matches accelerator pattern: persistence, integrations, domain services."""
    from app.ioc import PROVIDERS

    names = {cls.__name__ for cls in PROVIDERS}
    assert names == {"LitestarPersistenceProvider", "IntegrationsProvider", "DomainServiceProvider"}, names


def test_make_litestar_container_resolves_expected_types() -> None:
    """`make_litestar_container` builds a container with persistence + integration + domain types."""
    from sqlspec.adapters.oracledb import OracleAsyncConfig, OracleAsyncDriver
    from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore

    from app.domain.products.services.services import ProductService
    from app.ioc import make_litestar_container

    container = make_litestar_container()
    registered_types: set[type] = set()
    registry = container.registry
    while registry is not None:
        registered_types.update(key.type_hint for key in registry.factories)
        registry = getattr(registry, "child_registry", None)

    for cls in (OracleAsyncConfig, OracleAsyncDriver, OracleAsyncADKStore, ProductService):
        assert cls in registered_types, f"{cls.__name__} factory missing from container registry chain"


def test_persistence_provider_scopes() -> None:
    """LitestarPersistenceProvider exposes APP-scoped config + REQUEST-scoped driver."""
    from app.ioc import LitestarPersistenceProvider

    instance = LitestarPersistenceProvider()
    factories = {f.provides.type_hint: f for f in instance.factories}

    from sqlspec.adapters.oracledb import OracleAsyncConfig, OracleAsyncDriver

    assert OracleAsyncConfig in factories, "config factory missing"
    assert factories[OracleAsyncConfig].scope == Scope.APP

    assert OracleAsyncDriver in factories, "driver factory missing"
    assert factories[OracleAsyncDriver].scope == Scope.REQUEST


def test_integrations_provider_scopes() -> None:
    """IntegrationsProvider holds APP-scoped singletons for external integrations."""
    from app.ioc import IntegrationsProvider

    instance = IntegrationsProvider()
    factories = {f.provides.type_hint: f for f in instance.factories}

    from google.genai import Client
    from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore
    from sqlspec.extensions.adk import SQLSpecSessionService

    from app.domain.chat.services.adk import ADKRunner

    for cls in (Client, OracleAsyncADKStore, SQLSpecSessionService, ADKRunner):
        assert cls in factories, f"{cls.__name__} factory missing from IntegrationsProvider"
        assert factories[cls].scope == Scope.APP, f"{cls.__name__} must be APP-scoped"


def test_domain_service_provider_request_scoped() -> None:
    """DomainServiceProvider holds REQUEST-scoped per-request services."""
    from app.ioc import DomainServiceProvider

    instance = DomainServiceProvider()
    factories = {f.provides.type_hint: f for f in instance.factories}

    from app.domain.chat.services.adk import AgentToolsService, IntentService
    from app.domain.products.services.services import (
        OracleVectorSearchService,
        ProductService,
        StoreService,
        VertexAIService,
    )
    from app.domain.system.services.services import CacheService, ExemplarService, MetricsService

    for cls in (
        ProductService,
        StoreService,
        VertexAIService,
        OracleVectorSearchService,
        CacheService,
        MetricsService,
        ExemplarService,
        IntentService,
        AgentToolsService,
    ):
        assert cls in factories, f"{cls.__name__} factory missing from DomainServiceProvider"
        assert factories[cls].scope == Scope.REQUEST, f"{cls.__name__} must be REQUEST-scoped"


def test_old_per_domain_provider_classes_are_gone() -> None:
    """Per-domain Provider subclasses must not be re-exported anywhere."""
    import app.domain.chat.services as chat_services
    import app.domain.products.services as products_services
    import app.domain.system.services as system_services

    for module, name in (
        (chat_services, "ChatServiceProvider"),
        (products_services, "ProductsServiceProvider"),
        (system_services, "SystemServiceProvider"),
    ):
        attr = getattr(module, name, None)
        assert attr is None, (
            f"{module.__name__}.{name} still exists — Ch 2.3 must collapse it into ioc.py providers."
        )


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
